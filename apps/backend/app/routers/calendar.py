"""
ZoesTM Calendar Bridge

Per ADR 0001: ZoesTM does not own calendar presentation.
This router exposes task/habit/alarm data in calendar-entry shape
so ZoesCal can pull from ZoesTM via the shared contract.
"""

from datetime import datetime, UTC
from fastapi import APIRouter
from ..repositories import tasks_repo, habits_repo, alarms_repo

router = APIRouter()


def _parse_iso_utc(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def _alarm_to_entry(alarm: dict, now: datetime) -> dict | None:
    at = alarm.get("alarm_time", "")
    if not at:
        return None
    try:
        if len(at) <= 5:
            hh, mm = at.split(":")
            dt = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            at_iso = dt.isoformat().replace("+00:00", "Z")
        else:
            dt = datetime.fromisoformat(at.replace("Z", "+00:00"))
            at_iso = at
    except Exception:
        return None
    return {
        "source": "zoestm",
        "source_type": "alarm",
        "source_id": alarm["id"],
        "source_version": "v1",
        "dedupe_key": f"alarm:{alarm['id']}",
        "conflict_score": 0.0,
        "title": f"🔔 {alarm.get('title') or 'Alarm'}",
        "at": at_iso,
        "read_only": True,
        "editability_class": "readonly_mirror",
    }


def _in_window(at, start, end):
    dt = _parse_iso_utc(at) if at else None
    return bool(dt and start <= dt <= end)


@router.get("/feed")
def feed(from_: str, to: str):
    """Shared contract feed for ZoesCal to consume."""
    start = _parse_iso_utc(from_)
    end = _parse_iso_utc(to)
    if not start or not end:
        return {"from": from_, "to": to, "entries": [], "owner": "zoestm"}

    entries = []
    for t in tasks_repo.list_tasks()[:200]:
        at = t.get("due_at")
        if _in_window(at, start, end):
            entries.append(
                {
                    "source": "zoestm",
                    "source_type": "task",
                    "source_id": t["id"],
                    "source_version": "v1",
                    "dedupe_key": f"task:{t['id']}",
                    "conflict_score": 0.1,
                    "title": t["title"],
                    "at": at,
                    "read_only": True,
                    "editability_class": "readonly_mirror",
                }
            )

    for h in habits_repo.get_logs(limit=200):
        at = h.get("logged_at")
        if _in_window(at, start, end):
            entries.append(
                {
                    "source": "zoestm",
                    "source_type": "habit",
                    "source_id": h.get("id", h.get("logged_at", "")),
                    "source_version": "v1",
                    "dedupe_key": f"habit:{h.get('logged_at')}",
                    "conflict_score": 0.0,
                    "title": h.get("habit_name", "habit"),
                    "at": at,
                    "read_only": True,
                    "editability_class": "readonly_mirror",
                }
            )

    now = datetime.now(UTC)
    for a in alarms_repo.list_alarms():
        if not a.get("enabled"):
            continue
        entry = _alarm_to_entry(a, now)
        if entry and _in_window(entry.get("at"), start, end):
            entries.append(entry)

    return {"from": from_, "to": to, "entries": entries, "owner": "zoestm"}


# Endpoints map:
# Owner: zoestm-calendar-bridge
# GET /calendar/feed
