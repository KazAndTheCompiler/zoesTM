from fastapi import APIRouter, Depends
from ..services.authz import require_scopes
from ..services import events, webhooks, connectors
from ..services.outbox_worker import dispatch_once

router = APIRouter(dependencies=[Depends(require_scopes({'read:events'}))])


@router.get('/events/recent')
def recent_events(limit: int = 50):
    return {'items': events.recent_events(limit)}


@router.post('/webhooks', dependencies=[Depends(require_scopes({'write:webhooks'}))])
def register_webhook(target_url: str, secret: str):
    return webhooks.register(target_url, secret)


@router.get('/webhooks', dependencies=[Depends(require_scopes({'read:events'}))])
def list_webhooks():
    return {'items': webhooks.list_all()}


@router.post('/webhooks/{webhook_id}/disable', dependencies=[Depends(require_scopes({'write:webhooks'}))])
def disable_webhook(webhook_id: str):
    return webhooks.disable(webhook_id)


@router.post('/webhooks/test/{webhook_id}', dependencies=[Depends(require_scopes({'write:webhooks'}))])
def test_webhook(webhook_id: str):
    return webhooks.deliver_test(webhook_id, {'kind': 'test'})


@router.get('/connectors')
def list_connectors():
    return {'items': connectors.list_connectors()}


@router.post('/sync/{connector}/run', dependencies=[Depends(require_scopes({'admin:ops'}))])
def run_sync(connector: str):
    return connectors.run_sync(connector)


@router.post('/outbox/dispatch', dependencies=[Depends(require_scopes({'admin:ops'}))])
def dispatch_outbox(limit: int = 20):
    return dispatch_once(limit)


# Endpoints map:
# Owner: integrations-domain
# GET /integrations/events/recent?limit=50
# POST /integrations/webhooks?target_url=...&secret=...
# GET /integrations/webhooks
# POST /integrations/webhooks/{webhook_id}/disable
# POST /integrations/webhooks/test/{webhook_id}
# GET /integrations/connectors
# POST /integrations/sync/{connector}/run
# POST /integrations/outbox/dispatch?limit=20
