import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db
from apps.backend.app.config import settings


class QARound3Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / 'qa_round3.db'

        mig_dir = Path(__file__).resolve().parents[1] / 'migrations'
        with sqlite3.connect(cls._db_path) as c:
            for mig in sorted(mig_dir.glob('*.sql')):
                c.executescript(mig.read_text(encoding='utf-8'))

        db.DB_PATH = cls._db_path
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH = cls._orig_db_path
        cls._tmpdir.cleanup()


class TestErrorPayloadContract(QARound3Base):
    def test_canonical_error_payload_shape(self):
        checks = [
            self.client.patch('/tasks/missing-id/complete'),
            self.client.post('/alarms/missing-id/trigger'),
            self.client.post('/commands/execute', json={'text': '???'}),
        ]
        for response in checks:
            self.assertIn(response.status_code, (400, 404, 409))
            body = response.json()
            self.assertIn('error', body)
            self.assertIn('code', body['error'])
            self.assertIn('message', body['error'])


class TestAlarmListEndpoint(QARound3Base):
    def test_list_alarms_returns_meta_fields(self):
        created = self.client.post('/alarms/?at=07:30&kind=tts&title=Wake%20up&tts_text=Good%20morning')
        self.assertEqual(created.status_code, 200)

        listed = self.client.get('/alarms/')
        self.assertEqual(listed.status_code, 200)
        body = listed.json()
        self.assertIn('alarms', body)
        self.assertGreaterEqual(len(body['alarms']), 1)
        alarm = body['alarms'][0]
        self.assertIn('id', alarm)
        self.assertIn('alarm_time', alarm)
        self.assertIn('kind', alarm)
        self.assertIn('title', alarm)
        self.assertIn('tts_text', alarm)


class TestWebhookDeliveryMode(QARound3Base):
    def test_webhook_test_endpoint_uses_http_mode_when_enabled(self):
        headers = {'x-token-scopes': 'write:webhooks,read:events'}
        created = self.client.post('/integrations/webhooks?target_url=https://example.test/hook&secret=s3cr3t', headers=headers)
        self.assertEqual(created.status_code, 200)
        webhook_id = created.json()['id']

        mock_response = MagicMock(status_code=202)
        old_flag = settings.ENABLE_WEBHOOK_HTTP_DELIVERY
        settings.ENABLE_WEBHOOK_HTTP_DELIVERY = True
        try:
            with patch('apps.backend.app.services.webhooks.httpx.Client') as mock_client:
                mock_client.return_value.__enter__.return_value.post.return_value = mock_response
                tested = self.client.post(f'/integrations/webhooks/test/{webhook_id}', headers=headers)
        finally:
            settings.ENABLE_WEBHOOK_HTTP_DELIVERY = old_flag

        self.assertEqual(tested.status_code, 200)
        body = tested.json()
        self.assertEqual(body['delivery_mode'], 'http')
        self.assertEqual(body['status_code'], 202)
        self.assertIsNone(body['delivery_error'])


class TestAnkiRound1(QARound3Base):
    def test_deck_validation_and_duplicate_guard(self):
        bad = self.client.post('/review/decks?name=a')
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()['error']['code'], 'invalid_deck_name')

        good = self.client.post('/review/decks?name=Core Deck')
        self.assertEqual(good.status_code, 200)

        dup = self.client.post('/review/decks?name=core deck')
        self.assertEqual(dup.status_code, 400)
        self.assertEqual(dup.json()['error']['code'], 'duplicate_deck_name')

    def test_import_queue_rate_and_export_preview(self):
        deck = self.client.post('/review/decks?name=Spanish').json()
        deck_id = deck['id']

        csv_payload = 'front,back,tags,source\nHola,Hello,greeting|es,anki\nAdios,Bye,farewell|es,anki\n'
        imported = self.client.post('/review/import', params={'deck_id': deck_id, 'fmt': 'csv', 'content': csv_payload})
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()['created_cards'], 2)

        session = self.client.post('/review/session/start?limit=10')
        self.assertEqual(session.status_code, 200)
        cards = session.json()['cards']
        self.assertGreaterEqual(len(cards), 2)

        first_id = cards[0]['id']
        rated = self.client.post(f'/review/answer?rating=good&card_id={first_id}')
        self.assertEqual(rated.status_code, 200)
        # New response shape includes 'session' with state and interval
        self.assertEqual(rated.json().get('session', {}).get('state'), 'review')

        preview = self.client.get(f'/review/export-preview?deck_id={deck_id}&limit=10')
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()['deck_id'], deck_id)
        self.assertGreaterEqual(preview.json()['card_count'], 2)

    def test_session_scope_and_answer_for_selected_deck(self):
        deck = self.client.post('/review/decks?name=Deck Scoped').json()
        deck_id = deck['id']
        self.client.post(
            f'/review/decks/{deck_id}/cards',
            params={'front': 'Scoped Q', 'back': 'Scoped A', 'tags': 'scope|demo'},
        )

        other = self.client.post('/review/decks?name=Deck Other').json()
        self.client.post(
            f"/review/decks/{other['id']}/cards",
            params={'front': 'Other Q', 'back': 'Other A', 'tags': 'other'},
        )

        scoped = self.client.get(f'/review/session?deck_id={deck_id}&limit=10')
        self.assertEqual(scoped.status_code, 200)
        card = scoped.json()['card']
        self.assertEqual(card['front'], 'Scoped Q')

        rated = self.client.post(f"/review/answer?rating=good&card_id={card['id']}")
        self.assertEqual(rated.status_code, 200)
        self.assertEqual(rated.json().get('session', {}).get('last_rating'), 'good')


if __name__ == '__main__':
    unittest.main()
