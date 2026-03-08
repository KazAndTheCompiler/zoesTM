from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from ..db import tx, conn


@dataclass
class FocusState:
    status: str = 'idle'
    mode: str = 'focus'
    minutes: int = 25
    ends_at: datetime | None = None
    remaining_seconds: int | None = None


state = FocusState()


def _iso_to_dt(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))


def _dt_to_iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.isoformat()


def _load_state():
    """Load focus session state from database into module state."""
    global state
    try:
        with conn() as c:
            row = c.execute("SELECT status, mode, minutes, ends_at, remaining_seconds FROM focus_sessions WHERE id = 1").fetchone()
        if row:
            ends_at_dt = _iso_to_dt(row['ends_at']) if row['ends_at'] else None
            state = FocusState(
                status=row['status'],
                mode=row['mode'],
                minutes=row['minutes'],
                ends_at=ends_at_dt,
                remaining_seconds=row['remaining_seconds']
            )
    except Exception:
        # Safe fallback when table is not migrated yet in isolated/test imports.
        state = FocusState()


def _save_state():
    """Persist current module state to database."""
    with tx() as c:
        c.execute(
            """
            INSERT INTO focus_sessions (id, status, mode, minutes, ends_at, remaining_seconds, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                mode = excluded.mode,
                minutes = excluded.minutes,
                ends_at = excluded.ends_at,
                remaining_seconds = excluded.remaining_seconds,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                state.status,
                state.mode,
                state.minutes,
                _dt_to_iso(state.ends_at),
                state.remaining_seconds,
            )
        )


# Load persisted state on module import
_load_state()


def _remaining_seconds():
    if state.status == 'paused' and state.remaining_seconds is not None:
        return max(0, int(state.remaining_seconds))
    if not state.ends_at:
        return 0
    return max(0, int((state.ends_at - datetime.now(UTC)).total_seconds()))


def start(minutes: int = 25):
    state.status = 'running'
    state.mode = 'focus'
    state.minutes = minutes
    state.remaining_seconds = None
    state.ends_at = datetime.now(UTC) + timedelta(minutes=minutes)
    _save_state()
    return {'event': 'focus_start', 'minutes': minutes, 'remaining_seconds': _remaining_seconds(), 'tts_hook': 'Focus session started'}


def pause():
    state.remaining_seconds = _remaining_seconds()
    state.ends_at = None
    state.status = 'paused'
    _save_state()
    return {'event': 'focus_pause', 'remaining_seconds': _remaining_seconds(), 'tts_hook': 'Pomodoro paused'}


def resume():
    state.status = 'running'
    remaining = state.remaining_seconds if state.remaining_seconds is not None else state.minutes * 60
    state.ends_at = datetime.now(UTC) + timedelta(seconds=max(0, int(remaining)))
    state.remaining_seconds = None
    _save_state()
    return {'event': 'focus_resume', 'remaining_seconds': _remaining_seconds(), 'tts_hook': 'Back to focus'}


def complete():
    state.status = 'idle'
    state.ends_at = None
    state.remaining_seconds = None
    _save_state()
    return {'event': 'session_done', 'tts_hook': 'Session complete. Great work!'}


def status():
    return {
        'status': state.status,
        'mode': state.mode,
        'minutes': state.minutes,
        'remaining_seconds': _remaining_seconds(),
        'tts_hooks': {
            'on_start': 'Focus session started',
            'on_pause': 'Pomodoro paused',
            'on_resume': 'Back to focus',
            'on_complete': 'Session complete. Great work!',
        },
    }
