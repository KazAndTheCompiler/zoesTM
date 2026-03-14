import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['ZOESTM_DEV_AUTH'] = '0'
os.environ['ZOESTM_ENFORCE_AUTH'] = '0'
os.environ['ZOESTM_TRUST_LOCAL_CLIENTS'] = '1'

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db


class JournalApiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / 'journal.db'

        mig_dir = Path(__file__).resolve().parents[1] / 'migrations'
        with sqlite3.connect(cls._db_path) as c:
            for mig in sorted(mig_dir.glob('*.sql')):
                c.executescript(mig.read_text(encoding='utf-8'))

        db.DB_PATH = cls._db_path
        cls.client = TestClient(app, headers={'origin': 'http://localhost:5175'})

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH = cls._orig_db_path
        cls._tmpdir.cleanup()

    def setUp(self):
        with sqlite3.connect(self._db_path) as c:
            for table in ['journal_entries', 'habit_logs', 'habits', 'outbox_events', 'webhook_receipts', 'webhooks', 'tasks', 'command_logs']:
                try:
                    c.execute(f'DELETE FROM {table}')
                except sqlite3.OperationalError:
                    pass
            c.commit()


class TestJournalApi(JournalApiBase):
    def test_create_get_update_delete_and_events(self):
        create = self.client.post('/journal/', json={'markdown_body': '# Hello world', 'date': '2026-03-13'})
        self.assertEqual(create.status_code, 201)
        created = create.json()
        self.assertEqual(created['markdown_body'], '# Hello world')

        get_by_id = self.client.get(f"/journal/{created['id']}")
        self.assertEqual(get_by_id.status_code, 200)
        self.assertEqual(get_by_id.json()['id'], created['id'])

        get_by_date = self.client.get('/journal/2026-03-13')
        self.assertEqual(get_by_date.status_code, 200)
        self.assertEqual(get_by_date.json()['date'], '2026-03-13')

        patch_resp = self.client.patch(f"/journal/{created['id']}", json={'markdown_body': '## Updated heading', 'emoji': '🔥'})
        self.assertEqual(patch_resp.status_code, 200)
        patched = patch_resp.json()
        self.assertEqual(patched['emoji'], '🔥')
        self.assertEqual(patched['markdown_body'], '## Updated heading')

        recent = self.client.get('/integrations/events/recent')
        self.assertEqual(recent.status_code, 200)
        event_types = [item['event_type'] for item in recent.json()['items']]
        self.assertIn('journal.created', event_types)
        self.assertIn('journal.updated', event_types)

        delete_resp = self.client.delete(f"/journal/{created['id']}")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertEqual(delete_resp.json()['ok'], True)

        after = self.client.get(f"/journal/{created['id']}")
        self.assertEqual(after.status_code, 404)
        self.assertEqual(after.json()['error']['code'], 'journal_not_found')

    def test_duplicate_date_returns_409(self):
        one = self.client.post('/journal/', json={'markdown_body': 'first', 'date': '2020-01-01'})
        self.assertEqual(one.status_code, 201)
        two = self.client.post('/journal/', json={'markdown_body': 'second', 'date': '2020-01-01'})
        self.assertEqual(two.status_code, 409)

    def test_export_json_text_markdown_and_search(self):
        self.client.post('/habits/add?name=reading')
        self.client.post('/habits/checkin?name=reading&done=true')
        self.client.post('/journal/', json={'markdown_body': '## Updated heading', 'emoji': '📝', 'date': '2026-03-14'})

        with patch('apps.backend.app.routers.journal._calendar_events', return_value=[{'title': 'Standup', 'at': '2026-03-14T09:00:00Z'}]):
            export_json = self.client.get('/journal/export/2026-03-14')
            self.assertEqual(export_json.status_code, 200)
            payload = export_json.json()
            self.assertEqual(payload['date'], '2026-03-14')
            self.assertIsInstance(payload['events'], list)
            self.assertIn('done', payload['habits'])

            export_text = self.client.get('/journal/export/2026-03-14?format=text')
            self.assertEqual(export_text.status_code, 200)
            self.assertIn('Habits:', export_text.text)

            export_md = self.client.get('/journal/export/2026-03-14?format=markdown')
            self.assertEqual(export_md.status_code, 200)
            self.assertTrue(export_md.text.startswith('#'))

        search = self.client.get('/search?q=Updated+heading')
        self.assertEqual(search.status_code, 200)
        data = search.json()
        self.assertIn('items', data)
        self.assertIn('results', data)

    def test_meta_root_exists(self):
        resp = self.client.get('/meta')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['version'])

    def test_local_first_party_origin_can_use_journal_without_scope_header(self):
        resp = self.client.get('/journal/?limit=60', headers={'origin': 'http://localhost:5175'})
        self.assertEqual(resp.status_code, 200)

        preflight = self.client.options(
            '/journal/',
            headers={
                'origin': 'http://localhost:5175',
                'access-control-request-method': 'POST',
                'access-control-request-headers': 'content-type,x-token-scopes',
            },
        )
        self.assertIn(preflight.status_code, (200, 204))
        self.assertEqual(preflight.headers.get('access-control-allow-origin'), 'http://localhost:5175')

    def test_untrusted_origin_without_scopes_is_forbidden(self):
        resp = self.client.get('/journal/?limit=60', headers={'origin': 'https://evil.example'})
        self.assertEqual(resp.status_code, 403)


if __name__ == '__main__':
    unittest.main()
