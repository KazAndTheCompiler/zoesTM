"""
Event store tests: cursor-based streaming, persistence, cleanup.
"""
import pytest
import uuid
from datetime import datetime, UTC, timedelta
from apps.backend.app.services import event_store
from apps.backend.app.db import tx


@pytest.fixture(autouse=True)
def clean_events():
    """Clean outbox_events before each test."""
    with tx() as c:
        c.execute("DELETE FROM outbox_events")
        c.execute("DELETE FROM webhook_receipts")
    yield
    # no cleanup after needed


def test_emit_and_get_stream():
    # Emit a few events
    for i in range(5):
        event_store.emit_event('test.batch', {'seq': i})

    # Get initial stream
    res = event_store.get_event_stream(limit=10)
    assert len(res['events']) == 5
    assert res['next_cursor'] is None  # no more

    ids = [e['id'] for e in res['events']]


def test_cursor_pagination():
    # Emit 3 events with seq to verify ordering
    event_store.emit_event('page1', {'seq': 1})
    event_store.emit_event('page2', {'seq': 2})
    event_store.emit_event('page3', {'seq': 3})

    # Get first page (limit 2)
    page1 = event_store.get_event_stream(limit=2)
    assert len(page1['events']) == 2
    assert page1['next_cursor'] is not None
    cursor = page1['next_cursor']

    # Get next page using cursor
    page2 = event_store.get_event_stream(cursor=cursor, limit=2)
    assert len(page2['events']) == 1
    assert page2['next_cursor'] is None  # last page

    # Verify order: seq should be increasing
    assert page2['events'][0]['payload']['seq'] == 3


def test_reverse_cursor():
    # Emit events with seq in increasing order (newer later)
    event_store.emit_event('old1', {'seq': 1})
    event_store.emit_event('old2', {'seq': 2})
    event_store.emit_event('old3', {'seq': 3})

    # Get latest page with reverse cursor 'before:last_id'
    first_page = event_store.get_event_stream(limit=2, reverse=True)
    assert len(first_page['events']) == 2
    # In reverse order, the first event should be newer (higher seq)
    assert first_page['events'][0]['payload']['seq'] >= first_page['events'][-1]['payload']['seq']
    before_cursor = f"before:{first_page['events'][0]['id']}"

    second_page = event_store.get_event_stream(cursor=before_cursor, limit=2, reverse=True)
    assert len(second_page['events']) == 1
    assert second_page['events'][0]['payload']['seq'] < first_page['events'][0]['payload']['seq']


def test_get_by_id():
    ev = event_store.emit_event('byid', {'q': 1})
    fetched = event_store.get_event_by_id(ev['id'])
    assert fetched['event_type'] == 'byid'
    assert fetched['payload']['q'] == 1


def test_cleanup_old_events():
    # Insert an old event directly into the DB
    old_id = str(uuid.uuid4())
    with tx() as c:
        c.execute(
            "INSERT INTO outbox_events(id, event_type, payload_json, idempotency_key, status, attempts, next_attempt_at, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (old_id, 'old', '{}', 'old:1', 'sent', 1, datetime.now(UTC).isoformat(),
             (datetime.now(UTC) - timedelta(days=60)).isoformat()),
        )
    # cleanup_old_events deletes receipts older than cutoff
    result = event_store.cleanup_old_events(before_date=datetime.now(UTC) - timedelta(days=30))
    assert result['deleted_receipts'] is True
