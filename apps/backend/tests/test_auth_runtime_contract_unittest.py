import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db


class AuthRuntimeBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / 'auth-runtime.db'
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

    def setUp(self):
        with sqlite3.connect(self._db_path) as c:
            for table in ['journal_entries', 'audit_logs', 'outbox_events', 'webhook_receipts', 'webhooks']:
                try:
                    c.execute(f'DELETE FROM {table}')
                except sqlite3.OperationalError:
                    pass
            c.commit()


class TestAuthRuntimeContract(AuthRuntimeBase):
    def test_local_first_party_origin_can_use_journal_without_scope_header(self):
        with patch.dict(os.environ, {'ZOESTM_DEV_AUTH': '0', 'ZOESTM_ENFORCE_AUTH': '0', 'ZOESTM_TRUST_LOCAL_CLIENTS': '1'}, clear=False):
            resp = self.client.get('/journal/?limit=10', headers={'Origin': 'http://localhost:5175'})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), [])

    def test_unknown_origin_still_requires_scope_header(self):
        with patch.dict(os.environ, {'ZOESTM_DEV_AUTH': '0', 'ZOESTM_ENFORCE_AUTH': '0', 'ZOESTM_TRUST_LOCAL_CLIENTS': '1'}, clear=False):
            resp = self.client.get('/journal/?limit=10', headers={'Origin': 'https://evil.example'})
            self.assertEqual(resp.status_code, 403)

    def test_enforced_auth_mode_requires_explicit_scope_header(self):
        with patch.dict(os.environ, {'ZOESTM_DEV_AUTH': '0', 'ZOESTM_ENFORCE_AUTH': '1', 'ZOESTM_TRUST_LOCAL_CLIENTS': '1'}, clear=False):
            denied = self.client.get('/journal/?limit=10', headers={'Origin': 'http://localhost:5175'})
            self.assertEqual(denied.status_code, 401)
            allowed = self.client.get('/journal/?limit=10', headers={'Origin': 'http://localhost:5175', 'X-Token-Scopes': 'read:journal'})
            self.assertEqual(allowed.status_code, 200)

    def test_cors_preflight_accepts_local_journal_origin_and_scope_header(self):
        with patch.dict(os.environ, {'ZOESTM_DEV_AUTH': '0', 'ZOESTM_ENFORCE_AUTH': '0', 'ZOESTM_TRUST_LOCAL_CLIENTS': '1'}, clear=False):
            resp = self.client.options(
                '/journal/',
                headers={
                    'Origin': 'http://localhost:5175',
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'content-type,x-token-scopes',
                },
            )
            self.assertIn(resp.status_code, (200, 204))
            self.assertEqual(resp.headers.get('access-control-allow-origin'), 'http://localhost:5175')


if __name__ == '__main__':
    unittest.main()
