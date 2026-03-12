from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..errors import ApiError
from ..repositories import events_repo
from ..services.zoestm_sync import sync_zoestm_feed_safe

router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────────


class EventIn(BaseModel):
    title: str
    description: Optional[str] = ""
    start_at: str
    end_at: Optional[str] = None
    all_day: bool = False


class EventPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    all_day: Optional[bool] = None
    local_note: Optional[str] = None
    local_color: Optional[str] = None
    linked_task_id: Optional[str] = None


class ExternalEventIn(BaseModel):
    title: str
    description: Optional[str] = ""
    start_at: str
    end_at: Optional[str] = None
    all_day: bool = False
    source_type: str  # 'google' | 'caldav' etc
    source_instance_id: str  # account identifier
    source_external_id: str  # provider's event ID


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def _require_iso(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if _parse_iso(value) is None:
        raise ApiError(
            code="validation_error",
            message=f"Invalid ISO datetime for {field}",
            status_code=422,
            details={"field": field, "value": value},
        )
    return value


def _validate_event_payload(payload: dict, partial: bool = False) -> dict:
    data = dict(payload)
    if not partial or "start_at" in data:
        data["start_at"] = _require_iso(data.get("start_at"), "start_at")
    if "end_at" in data and data.get("end_at") is not None:
        data["end_at"] = _require_iso(data.get("end_at"), "end_at")
    return data


def _in_window(at: str | None, start: datetime, end: datetime) -> bool:
    dt = _parse_iso(at) if at else None
    return bool(dt and start <= dt <= end)


def _event_to_entry(e: dict) -> dict:
    """Convert a DB event to a calendar entry shape."""
    return {
        "id": e["id"],
        "source": e.get("source_type", "zoescal"),
        "source_id": e.get("source_external_id") or e["id"],
        "source_version": "v1",
        "dedupe_key": f"event:{e['id']}",
        "conflict_score": 0.0,
        "title": e["title"],
        "at": e.get("start_at"),
        "end_at": e.get("end_at"),
        "all_day": bool(e.get("all_day")),
        "read_only": bool(e.get("read_only")),
        "editability_class": e.get("editability_class", "local"),
        "local_note": e.get("local_note"),
        "linked_task_id": e.get("linked_task_id"),
        "sync_status": e.get("sync_status", "local_only"),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/timeline")
def timeline(from_: str, to: str):
    """Return all events in a time window."""
    start = _parse_iso(from_)
    end = _parse_iso(to)
    if not start or not end:
        return {"from": from_, "to": to, "entries": []}

    events = events_repo.list_events(start=from_, end=to)
    entries = [_event_to_entry(e) for e in events if not e.get("deleted")]
    return {"from": from_, "to": to, "entries": entries}


@router.get("/range")
def range_view(start: str, end: str):
    """Alias for timeline with conflict placeholder (ADR 0003)."""
    tl = timeline(start, end)
    return {
        "start": start,
        "end": end,
        "entries": tl["entries"],
        "conflicts": [],  # populated when conflict detection is implemented
    }


@router.get("/view")
async def view(mode: str = "day"):
    """Return events for a rolling day/week/month window from now."""
    mode = mode if mode in ("day", "week", "month") else "day"
    await sync_zoestm_feed_safe()
    now = datetime.now(UTC)
    span = {"day": 1, "week": 7, "month": 30}[mode]
    end = now + timedelta(days=span)

    events = events_repo.list_events(
        start=now.isoformat().replace("+00:00", "Z"),
        end=end.isoformat().replace("+00:00", "Z"),
    )
    entries = [_event_to_entry(e) for e in events if not e.get("deleted")]

    return {
        "mode": mode,
        "window": {
            "start": now.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
        "entries": entries,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────────


@router.post("/events", status_code=201)
def create_event(body: EventIn):
    event = events_repo.create_event(_validate_event_payload(body.model_dump()))
    return event


@router.get("/events/{event_id}")
def get_event(event_id: str):
    event = events_repo.get_event(event_id)
    if not event or event.get("deleted"):
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/events/{event_id}")
def patch_event(event_id: str, body: EventPatch):
    existing = events_repo.get_event(event_id)
    if not existing or existing.get("deleted"):
        raise HTTPException(status_code=404, detail="Event not found")
    updated = events_repo.update_event(
        event_id,
        _validate_event_payload(body.model_dump(exclude_none=True), partial=True),
    )
    return updated


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str):
    existing = events_repo.get_event(event_id)
    if not existing or existing.get("deleted"):
        raise HTTPException(status_code=404, detail="Event not found")
    events_repo.delete_event(event_id)


# ── External provider import (ADR 0005) ───────────────────────────────────────


@router.post("/events/external", status_code=201)
def import_external_event(body: ExternalEventIn):
    """
    Import an event from an external provider.
    Deduplicates by (source_type, source_instance_id, source_external_id).
    Provider-owned fields are read-only by default.
    """
    event = events_repo.upsert_external_event(
        _validate_event_payload(body.model_dump())
    )
    return event


# Endpoints map:
# Owner: zoescal-calendar-domain
# GET  /calendar/timeline
# GET  /calendar/range
# GET  /calendar/view
# POST /calendar/events
# GET  /calendar/events/{id}
# PATCH /calendar/events/{id}
# DELETE /calendar/events/{id}
# POST /calendar/events/external
