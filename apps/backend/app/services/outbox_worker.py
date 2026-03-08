import json
from . import events, webhooks
from ..db import conn, tx


def dispatch_once(limit: int = 20):
    pending = events.list_outbox_pending(limit)
    delivered = 0
    failed = 0
    hooks = webhooks.list_all()
    enabled_hooks = [h for h in hooks if int(h['enabled']) == 1]
    for ev in pending:
        try:
            payload = json.loads(ev['payload_json'])
            for h in enabled_hooks:
                webhooks.deliver_test(h['id'], {'event': ev['event_type'], 'payload': payload, 'idempotency_key': ev['idempotency_key']})
            events.mark_outbox_success(ev['id'])
            delivered += 1
        except Exception as exc:  # pragma: no cover
            attempts = int(ev['attempts']) + 1
            events.mark_outbox_retry(ev['id'], attempts, str(exc))
            failed += 1
    return {'processed': len(pending), 'delivered': delivered, 'failed': failed}


def snapshot_metrics():
    with conn() as c:
        p = c.execute("SELECT COUNT(*) as n FROM outbox_events WHERE status='pending'").fetchone()['n']
        r = c.execute("SELECT COUNT(*) as n FROM outbox_events WHERE status='retry_wait'").fetchone()['n']
        s = c.execute("SELECT COUNT(*) as n FROM outbox_events WHERE status='sent'").fetchone()['n']
    return {'outbox_pending': p, 'outbox_retry_wait': r, 'outbox_sent': s}
