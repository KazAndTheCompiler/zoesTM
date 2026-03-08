import hmac
import hashlib
import json
import uuid
from datetime import datetime, UTC

import httpx

from ..config import settings
from ..db import tx, conn


def register(target_url: str, secret: str):
    wid = str(uuid.uuid4())
    with tx() as c:
        c.execute(
            "INSERT INTO webhooks(id,target_url,secret,enabled) VALUES(?,?,?,1)",
            (wid, target_url, secret),
        )
    return get(wid)


def get(webhook_id: str):
    with conn() as c:
        row = c.execute("SELECT id,target_url,enabled,created_at FROM webhooks WHERE id=?", (webhook_id,)).fetchone()
    return dict(row) if row else None


def list_all():
    with conn() as c:
        rows = c.execute("SELECT id,target_url,enabled,created_at FROM webhooks ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def disable(webhook_id: str):
    with tx() as c:
        c.execute("UPDATE webhooks SET enabled=0, updated_at=CURRENT_TIMESTAMP WHERE id=?", (webhook_id,))
    return get(webhook_id)


def _signature(secret: str, timestamp: str, payload_json: str):
    body = f"{timestamp}.{payload_json}".encode('utf-8')
    return hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def verify(secret: str, timestamp: str, payload_json: str, signature: str):
    expected = _signature(secret, timestamp, payload_json)
    return hmac.compare_digest(expected, signature)


def deliver_test(webhook_id: str, payload: dict):
    with conn() as c:
        row = c.execute("SELECT id,target_url,secret,enabled FROM webhooks WHERE id=?", (webhook_id,)).fetchone()
    if not row:
        return {'status': 'missing'}
    if int(row['enabled']) != 1:
        return {'status': 'disabled'}
    ts = datetime.now(UTC).isoformat()
    payload_json = json.dumps(payload, sort_keys=True)
    sig = _signature(row['secret'], ts, payload_json)

    delivery_mode = 'stub'
    delivery_error = None
    status_code = None

    if settings.ENABLE_WEBHOOK_HTTP_DELIVERY:
        delivery_mode = 'http'
        headers = {
            'Content-Type': 'application/json',
            'X-ZoesTM-Timestamp': ts,
            'X-ZoesTM-Signature': sig,
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(row['target_url'], content=payload_json, headers=headers)
            status_code = resp.status_code
            if not (200 <= resp.status_code < 300):
                delivery_error = f'http_{resp.status_code}'
        except Exception as exc:  # pragma: no cover
            delivery_error = str(exc)

    rid = str(uuid.uuid4())
    with tx() as c:
        c.execute(
            "INSERT INTO webhook_receipts(id,webhook_id,outbox_event_id,signature) VALUES(?,?,?,?)",
            (rid, webhook_id, None, sig),
        )
    return {
        'status': 'delivered',
        'signature': sig,
        'timestamp': ts,
        'delivery_mode': delivery_mode,
        'delivery_error': delivery_error,
        'status_code': status_code,
    }
