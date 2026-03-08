from fastapi import APIRouter
from ..db import conn

router = APIRouter()


@router.get('/health/detail')
def health_detail():
    db_ok = False
    outbox_ok = False
    try:
        with conn() as c:
            c.execute('SELECT 1').fetchone()
            db_ok = True
            c.execute('SELECT COUNT(*) as n FROM outbox_events').fetchone()
            outbox_ok = True
    except Exception:
        db_ok = False
        outbox_ok = False

    ok = db_ok and outbox_ok
    return {
        'ok': ok,
        'dependencies': {
            'db': 'ok' if db_ok else 'error',
            'event_bus': 'ok' if outbox_ok else 'error',
            'outbox_worker': 'ok' if outbox_ok else 'error',
        },
        'runbook': 'docs/integration-handoff.md',
    }


# Endpoints map:
# Owner: ops-domain
# GET /health/detail
