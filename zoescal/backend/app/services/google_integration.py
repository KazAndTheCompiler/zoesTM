import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
from urllib.parse import quote
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from ..repositories import events_repo


logger = logging.getLogger("zoescal.google")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_CALENDAR_LIST_URL = (
    "https://www.googleapis.com/calendar/v3/users/me/calendarList"
)
GOOGLE_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks.readonly",
]

DEFAULT_TOKEN_PATH = Path(__file__).resolve().parents[2] / "data" / "google_token.json"
DEFAULT_STATE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "google_oauth_state.json"
)


def _token_path() -> Path:
    raw = os.getenv("GOOGLE_TOKEN_PATH", "").strip()
    path = Path(raw) if raw else DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    path = DEFAULT_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def _redirect_uri() -> str:
    return os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8001/auth/google/callback"
    ).strip()


def is_configured() -> bool:
    return bool(_client_id() and _client_secret() and _redirect_uri())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        logger.exception("failed_to_read_json", extra={"path": str(path)})
        return None


def _delete_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.exception("failed_to_delete_file", extra={"path": str(path)})


def _pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def create_login_url() -> str:
    if not is_configured():
        raise RuntimeError("Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    verifier = _pkce_verifier()
    _write_json(
        _state_path(),
        {
            "state": state,
            "code_verifier": verifier,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return str(httpx.URL(GOOGLE_AUTH_URL, params=params))


def load_tokens() -> dict[str, Any] | None:
    return _read_json(_token_path())


def save_tokens(payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    expires_in = int(payload.get("expires_in", 3600))
    token_data = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token")
        or (load_tokens() or {}).get("refresh_token"),
        "scope": payload.get("scope", " ".join(GOOGLE_SCOPES)),
        "token_type": payload.get("token_type", "Bearer"),
        "expiry": (now + timedelta(seconds=expires_in)).isoformat(),
        "updated_at": now.isoformat(),
    }
    _write_json(_token_path(), token_data)
    return token_data


async def exchange_code(code: str, state: str) -> dict[str, Any]:
    state_data = _read_json(_state_path()) or {}
    if state_data.get("state") != state or not state_data.get("code_verifier"):
        raise RuntimeError("Invalid OAuth state")

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": state_data["code_verifier"],
            },
        )
    response.raise_for_status()
    _delete_file(_state_path())
    return save_tokens(response.json())


def connection_status() -> dict[str, Any]:
    tokens = load_tokens()
    if not tokens:
        return {"configured": is_configured(), "connected": False}
    expiry = _parse_dt(tokens.get("expiry"))
    return {
        "configured": is_configured(),
        "connected": True,
        "expiry": tokens.get("expiry"),
        "expired": bool(expiry and expiry <= datetime.now(UTC)),
        "scopes": tokens.get("scope", "").split(),
    }


async def revoke_and_delete() -> None:
    tokens = load_tokens()
    if tokens and tokens.get("access_token"):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                await client.post(
                    GOOGLE_REVOKE_URL, params={"token": tokens["access_token"]}
                )
        except Exception:
            logger.exception("google_revoke_failed")
    _delete_file(_token_path())
    _delete_file(_state_path())


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


async def get_valid_access_token() -> str | None:
    tokens = load_tokens()
    if not tokens:
        return None
    expiry = _parse_dt(tokens.get("expiry"))
    if expiry and expiry > datetime.now(UTC) + timedelta(minutes=2):
        return tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return None
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
    response.raise_for_status()
    refreshed = response.json()
    refreshed["refresh_token"] = refresh_token
    return save_tokens(refreshed)["access_token"]


def _event_start_end(item: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    start = item.get("start", {})
    end = item.get("end", {})
    if start.get("date"):
        start_at = f"{start['date']}T00:00:00Z"
        end_at = (
            f"{end.get('date', start['date'])}T00:00:00Z" if end.get("date") else None
        )
        return start_at, end_at, True
    return start.get("dateTime"), end.get("dateTime"), False


async def sync_google_events() -> dict[str, int]:
    if not is_configured():
        logger.info("google_sync_skipped_not_configured")
        return {"calendars": 0, "events": 0}

    token = await get_valid_access_token()
    if not token:
        logger.info("google_sync_skipped_not_connected")
        return {"calendars": 0, "events": 0}

    headers = {"Authorization": f"Bearer {token}"}
    imported = 0
    calendars = 0
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            cal_resp = await client.get(GOOGLE_CALENDAR_LIST_URL)
            cal_resp.raise_for_status()
            calendar_items = cal_resp.json().get("items", [])
        except Exception:
            logger.exception("google_calendar_list_failed")
            return {"calendars": 0, "events": 0}

        for calendar in calendar_items:
            calendar_id = calendar.get("id")
            if not calendar_id:
                continue
            calendars += 1
            try:
                events_resp = await client.get(
                    GOOGLE_EVENTS_URL.format(calendar_id=quote(calendar_id, safe="")),
                    params={
                        "singleEvents": "true",
                        "showDeleted": "false",
                        "maxResults": 2500,
                        "orderBy": "startTime",
                        "timeMin": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    },
                )
                events_resp.raise_for_status()
            except Exception:
                logger.exception(
                    "google_calendar_events_failed", extra={"calendar_id": calendar_id}
                )
                continue

            for item in events_resp.json().get("items", []):
                if item.get("status") == "cancelled":
                    continue
                start_at, end_at, all_day = _event_start_end(item)
                if not start_at:
                    continue
                try:
                    events_repo.upsert_external_event(
                        {
                            "title": item.get("summary", "Untitled event"),
                            "description": item.get("description", ""),
                            "start_at": start_at,
                            "end_at": end_at,
                            "all_day": all_day,
                            "source_type": "google",
                            "source_instance_id": calendar_id,
                            "source_external_id": item.get("id"),
                            "source_origin_app": "google",
                            "editability_class": "readonly_mirror",
                            "read_only": True,
                            "sync_status": "synced",
                        }
                    )
                    imported += 1
                except Exception:
                    logger.exception(
                        "google_event_upsert_failed",
                        extra={"calendar_id": calendar_id, "event_id": item.get("id")},
                    )
                    continue
    return {"calendars": calendars, "events": imported}


async def google_sync_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            result = await sync_google_events()
            logger.info("google_sync_complete", extra=result)
        except Exception:
            logger.exception("google_sync_loop_failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=900)
        except asyncio.TimeoutError:
            continue
