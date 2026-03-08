import os
import unittest
from pathlib import Path
import sqlite3

from apps.backend.app.services import events, webhooks
from apps.backend.app.services.outbox_worker import dispatch_once

# Respect DB_PATH for test isolation
DB = Path(os.getenv('DB_PATH', Path(__file__).resolve().parents[1] / 'data' / 'zoestm.db'))
MIG = Path(__file__).resolve().parents[1] / 'migrations'


class TestIntegrationOutbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Avoid replaying ALTER migrations on existing dev DB.
        core_sql = (MIG / '003_integration_core.sql').read_text()
        with sqlite3.connect(DB) as c:
            c.executescript(core_sql)

    def test_event_to_outbox_to_webhook(self):
        hook = webhooks.register('https://example.test/webhook', 's3cr3t')
        ev = events.emit_event('task.created', {'task_id': 't1'})
        self.assertEqual(ev['event_type'], 'task.created')
        out = dispatch_once(limit=10)
        self.assertGreaterEqual(out['delivered'], 1)


if __name__ == '__main__':
    unittest.main()
