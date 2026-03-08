import json
import uuid
from collections import deque
from datetime import datetime, timedelta, UTC
from ..db import tx, conn

_RECENT = deque(maxlen=200)


def emit_event(event_type: str, payload: dict, idempotency_key: str | None = None):
    event = {
        'id': str(uuid.uuid4()),
        'event_type': event_type,
        'payload': payload,
        'idempotency_key': idempotency_key or f"{event_type}:{uuid.uuid4()}",
        'created_at': datetime.now(UTC).isoformat(),
    }
    _RECENT.appendleft(event)
    with tx() as c:
        c.execute(
            """
            INSERT OR IGNORE INTO outbox_events(id,event_type,payload_json,idempotency_key,status,attempts,next_attempt_at)
            VALUES(?,?,?,?, 'pending',0,CURRENT_TIMESTAMP)
            """,
            (event['id'], event_type, json.dumps(payload), event['idempotency_key']),
        )
    return event


def recent_events(limit: int = 50):
    return list(_RECENT)[: max(1, min(limit, 200))]


def list_outbox_pending(limit: int = 50):
    with conn() as c:
        rows = c.execute(
            """
            SELECT id,event_type,payload_json,idempotency_key,attempts,status,next_attempt_at
            FROM outbox_events
            WHERE status IN ('pending','retry_wait') AND next_attempt_at <= CURRENT_TIMESTAMP
            ORDER BY created_at ASC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_outbox_success(event_id: str):
    with tx() as c:
        c.execute("UPDATE outbox_events SET status='sent', updated_at=CURRENT_TIMESTAMP WHERE id=?", (event_id,))


def mark_outbox_retry(event_id: str, attempts: int, err: str):
    backoff = min(300, 2 ** min(8, attempts))
    next_at = datetime.now(UTC) + timedelta(seconds=backoff)
    with tx() as c:
        c.execute(
            """
            UPDATE outbox_events
            SET status='retry_wait', attempts=?, last_error=?, next_attempt_at=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (attempts, err[:400], next_at.isoformat(), event_id),
        )
