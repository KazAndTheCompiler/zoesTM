from datetime import datetime, timedelta, UTC
from fastapi import APIRouter
from ..repositories import tasks_repo, habits_repo, alarms_repo

router = APIRouter()


def _parse_iso_utc(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
    except Exception:
        return None


def _alarm_to_entry(alarm: dict, now: datetime) -> dict | None:
    at = alarm.get('alarm_time', '')
    if not at:
        return None
    try:
        if len(at) <= 5:
            hh, mm = at.split(':')
            dt = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            at_iso = dt.isoformat().replace('+00:00', 'Z')
        else:
            dt = datetime.fromisoformat(at.replace('Z', '+00:00'))
            at_iso = at
    except Exception:
        return None
    return {
        'source': 'alarm',
        'source_id': alarm['id'],
        'source_version': 'v1',
        'dedupe_key': f"alarm:{alarm['id']}",
        'conflict_score': 0.0,
        'title': f"🔔 {alarm.get('title') or 'Alarm'}",
        'at': at_iso,
    }


def _in_window(at: str | None, start: datetime, end: datetime) -> bool:
    dt = _parse_iso_utc(at) if at else None
    return bool(dt and start <= dt <= end)


@router.get('/range')
def range_view(start: str, end: str):
    tl = timeline(start, end)
    return {'start': start, 'end': end, 'entries': tl.get('entries', []), 'conflicts': []}


@router.get('/timeline')
def timeline(from_: str, to: str):
    start = _parse_iso_utc(from_)
    end = _parse_iso_utc(to)
    if not start or not end:
        return {'from': from_, 'to': to, 'entries': []}

    entries = []
    for t in tasks_repo.list_tasks()[:200]:
        at = t.get('due_at')
        if _in_window(at, start, end):
            entries.append({'source': 'task', 'source_id': t['id'], 'source_version': 'v1',
                            'dedupe_key': f"task:{t['id']}", 'conflict_score': 0.1,
                            'title': t['title'], 'at': at})
    for h in habits_repo.get_logs(limit=200):
        at = h.get('logged_at')
        if _in_window(at, start, end):
            entries.append({'source': 'habit', 'source_id': h.get('id', h.get('logged_at', '')),
                            'source_version': 'v1', 'dedupe_key': f"habit:{h.get('logged_at')}",
                            'conflict_score': 0.0, 'title': h.get('habit_name', 'habit'), 'at': at})
    return {'from': from_, 'to': to, 'entries': entries}


@router.get('/view')
def view(mode: str = 'day'):
    mode = mode if mode in ('day', 'week', 'month') else 'day'
    now = datetime.now(UTC)
    span = {'day': 1, 'week': 7, 'month': 30}[mode]
    start = now
    end = now + timedelta(days=span)
    entries = []

    for t in tasks_repo.list_tasks()[:200]:
        at = t.get('due_at')
        if at:
            entries.append({'source': 'task', 'source_id': t['id'], 'source_version': 'v1',
                            'dedupe_key': f"task:{t['id']}", 'conflict_score': 0.1,
                            'title': t['title'], 'at': at})

    for h in habits_repo.get_logs(limit=200):
        at = h.get('logged_at')
        if at:
            entries.append({'source': 'habit', 'source_id': h.get('id', h.get('logged_at', '')),
                            'source_version': 'v1', 'dedupe_key': f"habit:{h.get('logged_at')}",
                            'conflict_score': 0.0, 'title': h.get('habit_name', 'habit'), 'at': at})

    for a in alarms_repo.list_alarms():
        if not a.get('enabled'):
            continue
        entry = _alarm_to_entry(a, now)
        if entry:
            entries.append(entry)

    return {
        'mode': mode,
        'window': {'start': start.isoformat().replace('+00:00', 'Z'), 'end': end.isoformat().replace('+00:00', 'Z')},
        'entries': entries,
    }


# Endpoints map:
# Owner: calendar-domain
# GET /calendar/range
# GET /calendar/timeline
# GET /calendar/view
