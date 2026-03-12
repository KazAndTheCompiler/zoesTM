import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..repositories import events_repo


logger = logging.getLogger("zoescal.zoestm_sync")


def _feed_url() -> str:
    return os.getenv("ZOESTM_FEED_URL", "http://127.0.0.1:8000/calendar/feed")


def _sync_window() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    lookback_days = int(os.getenv("ZOESTM_SYNC_LOOKBACK_DAYS", "1"))
    lookahead_days = int(os.getenv("ZOESTM_SYNC_LOOKAHEAD_DAYS", "30"))
    return now - timedelta(days=lookback_days), now + timedelta(days=lookahead_days)


def _entry_to_payload(entry: dict[str, Any]) -> dict[str, Any] | None:
    source_id = entry.get("source_id")
    start_at = entry.get("at")
    source_type = entry.get("source_type")
    if not source_id or not start_at or not source_type:
        return None
    return {
        "title": entry.get("title", "Untitled"),
        "description": entry.get("local_note", "") or "",
        "start_at": start_at,
        "end_at": entry.get("end_at"),
        "all_day": bool(entry.get("all_day", False)),
        "source_type": source_type,
        "source_instance_id": "zoestm",
        "source_external_id": str(source_id),
        "source_origin_app": "zoestm",
        "editability_class": "readonly_mirror",
        "read_only": True,
        "sync_status": "synced",
    }


async def sync_zoestm_feed() -> dict[str, int]:
    start, end = _sync_window()
    params = {
        "from_": start.isoformat().replace("+00:00", "Z"),
        "to": end.isoformat().replace("+00:00", "Z"),
    }
    imported = 0
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(_feed_url(), params=params)
        response.raise_for_status()
        payload = response.json()
    for entry in payload.get("entries", []):
        event_payload = _entry_to_payload(entry)
        if not event_payload:
            continue
        events_repo.upsert_external_event(event_payload)
        imported += 1
    return {"entries": imported}


async def sync_zoestm_feed_safe() -> dict[str, int]:
    try:
        result = await sync_zoestm_feed()
        logger.info("zoestm_sync_complete", extra=result)
        return result
    except Exception:
        logger.exception("zoestm_sync_failed")
        return {"entries": 0}


async def zoestm_sync_loop(stop_event: asyncio.Event) -> None:
    interval = int(os.getenv("ZOESTM_SYNC_INTERVAL_SECONDS", "900"))
    while not stop_event.is_set():
        await sync_zoestm_feed_safe()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
