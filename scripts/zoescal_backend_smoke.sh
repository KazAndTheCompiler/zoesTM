#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=. ./.venv/bin/python - <<'PY'
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from zoescal.backend.app.main import app

with TestClient(app) as c:
    start = datetime.now(UTC)
    end = start + timedelta(hours=1)
    create = c.post('/calendar/events', json={
        'title': 'zoescal smoke event',
        'start_at': start.isoformat().replace('+00:00', 'Z'),
        'end_at': end.isoformat().replace('+00:00', 'Z'),
        'all_day': False,
    })
    assert create.status_code == 201, create.text
    event = create.json()

    timeline = c.get(f"/calendar/timeline?from_={start.isoformat().replace('+00:00', 'Z')}&to={(start + timedelta(days=1)).isoformat().replace('+00:00', 'Z')}")
    assert timeline.status_code == 200, timeline.text
    titles = [entry['title'] for entry in timeline.json().get('entries', [])]
    assert 'zoescal smoke event' in titles

    view = c.get('/calendar/view?mode=week')
    assert view.status_code == 200, view.text
    payload = view.json()
    assert payload.get('mode') == 'week'
    assert isinstance(payload.get('entries'), list)

    patch = c.patch(f"/calendar/events/{event['id']}", json={'local_note': 'smoke note'})
    assert patch.status_code == 200, patch.text
    assert patch.json().get('local_note') == 'smoke note'

print('zoescal backend smoke: OK')
PY
