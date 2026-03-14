#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=. ./.venv/bin/python - <<'PY'
import uuid
from datetime import datetime, timedelta, UTC
from pathlib import Path
from fastapi.testclient import TestClient
from apps.backend.app.main import app

ui = Path('apps/frontend/src/App.tsx').read_text(encoding='utf-8')
required = [
    "overview-grid",
    "'overview'",
    "'tasks'",
    "'focus'",
    "'alarm-player'",
    "'habits'",
    "'eisenhower-kanban'",
    "'review-anki'",
    "'commands'",
    "box-tasks",
    "box-zoescal",
    "box-zoesjournal",
    "box-focus",
    "box-alarm-player",
    "box-habits",
    "box-eisenhower-kanban",
    "box-review-anki",
    "box-commands",
    "Global Command Bar (BPC)",
]
missing = [x for x in required if x not in ui]
if missing:
    raise SystemExit('frontend behavior controls missing: ' + ', '.join(missing))

c = TestClient(app)

openapi = c.get('/meta/openapi').json()
assert openapi.get('spec', {}).get('info', {}).get('title'), 'openapi title missing'

start = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
end = (datetime.now(UTC) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
cal = c.get(f'/calendar/feed?from_={start}&to={end}').json()
assert cal.get('owner') == 'zoestm'
assert isinstance(cal.get('entries'), list)

alarm = c.post('/alarms/', json={
    'at': '2026-03-01T07:00:00+00:00',
    'kind': 'reminder',
    'title': 'Smoke',
    'tts_text': 'Smoke',
}).json()
assert 'id' in alarm

deck_name = f"Smoke Test Deck {uuid.uuid4().hex[:8]}"
deck_resp = c.post('/review/decks', params={'name': deck_name})
if deck_resp.status_code != 200:
    print(f"Deck creation failed: {deck_resp.status_code} {deck_resp.text}")
    deck = deck_resp.json()
    if 'duplicate_deck_name' in deck.get('error', {}).get('code', ''):
        existing = c.get('/review/decks').json()
        for d in existing.get('items', []):
            if d['name'] == deck_name:
                deck = d
                break
        else:
            raise Exception(f"Failed to get deck ID for {deck_name}")
else:
    deck = deck_resp.json()
deck_id = deck['id']
c.post(f'/review/decks/{deck_id}/cards', params={'front': 'Q', 'back': 'A'}).json()
start = c.post('/review/session/start?limit=1').json()
assert start['count'] >= 1

review = c.get('/review/session').json()
assert 'state' in review
assert 'interval' in review
assert 'card' in review
assert 'queue_size' in review

cmd = c.post('/commands/preview', json={'text': 'add task smoke'}).json()
assert 'parsed' in cmd and 'would_execute' in cmd

print('frontend behavior smoke: OK')
PY
