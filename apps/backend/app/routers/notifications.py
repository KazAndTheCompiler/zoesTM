from fastapi import APIRouter
from ..services import notifications as center

router = APIRouter()


@router.get('/')
def list_notifications(scope: str | None = None):
    return {'items': center.list_items(scope)}


@router.post('/{notification_id}/read')
def mark_read(notification_id: str):
    return center.mark_read(notification_id)


@router.post('/{notification_id}/archive')
def archive(notification_id: str):
    return center.archive(notification_id)


@router.post('/clear')
def clear_scope(scope: str):
    return center.clear_scope(scope)


@router.get('/unread-count')
def unread_count():
    return center.unread_count()


# Endpoints map:
# Owner: notification-domain
# GET /notifications/?scope=global
# POST /notifications/{notification_id}/read
# POST /notifications/{notification_id}/archive
# POST /notifications/clear?scope=global
# GET /notifications/unread-count
