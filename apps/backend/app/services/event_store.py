"""
Persistent event store replacing the in-memory deque.
Provides both a streaming interface for recent events and a cursor-based read-ahead.
"""
import json
import uuid
from datetime import datetime, timedelta, UTC
from ..db import tx, conn


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def emit_event(event_type: str, payload: dict, idempotency_key: str | None = None):
    """Emit an event and persist it to outbox_events table."""
    event = {
        'id': str(uuid.uuid4()),
        'event_type': event_type,
        'payload': payload,
        'idempotency_key': idempotency_key or f"{event_type}:{uuid.uuid4()}",
        'created_at': _now_iso(),
    }
    with tx() as c:
        c.execute(
            """
            INSERT OR IGNORE INTO outbox_events(id, event_type, payload_json, idempotency_key, status, attempts, next_attempt_at)
            VALUES(?, ?, ?, ?, 'pending', 0, CURRENT_TIMESTAMP)
            """,
            (event['id'], event_type, json.dumps(payload), event['idempotency_key']),
        )
    return event


def get_event_stream(cursor: str | None = None, limit: int = 50, reverse: bool = False):
    """
    Read events with cursor-based pagination.

    Args:
        cursor: event_id to read after (exclusive) or 'before:EVENT_ID' for reverse
        limit: max number of events to return
        reverse: if True, use cursor as 'before:' prefix and return older events

    Returns:
        {'events': [...], 'next_cursor': str or None}
    """
    # Normalize cursor
    is_before = False
    if cursor and cursor.startswith('before:'):
        is_before = True
        cursor = cursor[7:]

    with conn() as c:
        if reverse:
            # Get N events BEFORE cursor
            if cursor:
                rows = c.execute(
                    """
                    SELECT id, event_type, payload_json, created_at, idempotency_key
                    FROM outbox_events
                    WHERE id < ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (cursor, max(1, min(limit, 200))),
                ).fetchall()
            else:
                rows = c.execute(
                    """
                    SELECT id, event_type, payload_json, created_at, idempotency_key
                    FROM outbox_events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (max(1, min(limit, 200)),),
                ).fetchall()
        else:
            # Get N events AFTER cursor
            if cursor:
                rows = c.execute(
                    """
                    SELECT id, event_type, payload_json, created_at, idempotency_key
                    FROM outbox_events
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (cursor, max(1, min(limit, 200))),
                ).fetchall()
            else:
                rows = c.execute(
                    """
                    SELECT id, event_type, payload_json, created_at, idempotency_key
                    FROM outbox_events
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (max(1, min(limit, 200)),),
                ).fetchall()

    events = []
    for r in rows:
        events.append({
            'id': r[0],
            'event_type': r[1],
            'payload': json.loads(r[2]),
            'created_at': r[3],
            'idempotency_key': r[4],
        })

    # Determine next cursor
    if events:
        if reverse:
            next_cursor = f'before:{events[0]["id"]}' if len(events) >= limit else None
        else:
            next_cursor = events[-1]['id'] if len(events) >= limit else None
    else:
        next_cursor = None

    return {'events': events, 'next_cursor': next_cursor}


def get_event_by_id(event_id: str):
    """Fetch a single event by ID."""
    with conn() as c:
        row = c.execute(
            "SELECT id, event_type, payload_json, created_at, idempotency_key FROM outbox_events WHERE id=?",
            (event_id,),
        ).fetchone()
    if not row:
        return None
    return {
        'id': row[0],
        'event_type': row[1],
        'payload': json.loads(row[2]),
        'created_at': row[3],
        'idempotency_key': row[4],
    }


def list_pending(limit: int = 50):
    """List pending events that can be delivered now."""
    with conn() as c:
        rows = c.execute(
            """
            SELECT id, event_type, payload_json, idempotency_key, attempts, status, next_attempt_at
            FROM outbox_events
            WHERE status IN ('pending', 'retry_wait') AND next_attempt_at <= CURRENT_TIMESTAMP
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_delivered(event_id: str, delivery_id: str):
    """Mark an event as successfully delivered and record the delivery."""
    with tx() as c:
        c.execute(
            """
            UPDATE outbox_events
            SET status='sent', updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (event_id,),
        )
        # Record webhook receipt (delivery_id links to webhook_id in webhook_receipts)
        c.execute(
            """
            INSERT INTO webhook_receipts(id, outbox_event_id, delivery_id, delivered_at)
            VALUES(?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (delivery_id, event_id, delivery_id),
        )


def mark_retry(event_id: str, attempts: int, error: str):
    """Mark an event for retry with backoff delay."""
    backoff = min(300, 2 ** min(8, attempts))
    next_at = datetime.now(UTC) + timedelta(seconds=backoff)
    with tx() as c:
        c.execute(
            """
            UPDATE outbox_events
            SET status='retry_wait', attempts=?, last_error=?, next_attempt_at=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (attempts, error[:400], next_at.isoformat(), event_id),
        )


def get_unverified_webhooks(limit: int = 100):
    """List webhook targets waiting for verification."""
    with conn() as c:
        rows = c.execute(
            """
            SELECT id, target_url, secret, created_at
            FROM webhooks
            WHERE enabled=1
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def set_webhook_verified(webhook_id: str):
    """Mark a webhook as verified (signed but not necessarily delivered)."""
    with tx() as c:
        c.execute(
            "UPDATE webhooks SET verified_at=CURRENT_TIMESTAMP WHERE id=?",
            (webhook_id,),
        )


def get_webhook_receipts(webhook_id: str, limit: int = 50):
    """Get delivery receipts for a webhook."""
    with conn() as c:
        rows = c.execute(
            """
            SELECT id, outbox_event_id, delivery_id, delivered_at, signature
            FROM webhook_receipts
            WHERE webhook_id=?
            ORDER BY delivered_at DESC
            LIMIT ?
            """,
            (webhook_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_event(event_id: str):
    """Delete an event (for debugging/cleanup)."""
    with tx() as c:
        c.execute("DELETE FROM outbox_events WHERE id=?", (event_id,))
        c.execute("DELETE FROM webhook_receipts WHERE outbox_event_id=?", (event_id,))
    return {'deleted': True}


def cleanup_old_events(before_date: datetime | None = None):
    """
    Clean up old events and receipts.

    Args:
        before_date: delete all events before this datetime (default: 30 days ago)
    """
    cutoff = before_date or (datetime.now(UTC) - timedelta(days=30))
    with tx() as c:
        # Keep deleted/sent events for 30 days, then archive or delete
        c.execute(
            "DELETE FROM webhook_receipts WHERE delivered_at < ?",
            (cutoff.isoformat(),),
        )
        # We'll leave outbox_events mostly untouched for audit but could archive
    return {'deleted_receipts': True}
