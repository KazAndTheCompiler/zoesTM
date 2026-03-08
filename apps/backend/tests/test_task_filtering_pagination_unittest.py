import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db


class TaskFilteringPaginationBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "task_filtering.db"

        mig_dir = Path(__file__).resolve().parents[1] / "migrations"
        with sqlite3.connect(cls._db_path) as c:
            for mig in sorted(mig_dir.glob("*.sql")):
                c.executescript(mig.read_text(encoding="utf-8"))

        db.DB_PATH = cls._db_path
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH = cls._orig_db_path
        cls._tmpdir.cleanup()

    def setUp(self):
        """Clear available tables before each test without assuming optional tables exist."""
        with sqlite3.connect(self._db_path) as c:
            existing = {
                r[0]
                for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            # Keep deletion order safe for FKs where relevant
            preferred = [
                'tasks', 'alarms', 'alarm_meta', 'alarm_queue',
                'habit_logs', 'habits',
                'cards', 'decks',
                'command_logs',
                'player_queue',
            ]
            for t in preferred:
                if t in existing:
                    c.execute(f"DELETE FROM {t}")
            c.commit()


class TestTaskListFiltering(TaskFilteringPaginationBase):
    def test_list_tasks_default_returns_all_ordered_by_created_desc(self):
        # Create tasks with different priorities/due dates
        self.client.post("/tasks/", json={"title": "Task A", "priority": 1})
        self.client.post("/tasks/", json={"title": "Task B", "priority": 2})
        self.client.post("/tasks/", json={"title": "Task C", "priority": 3})

        resp = self.client.get("/tasks/")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 3)
        # Verify order is created_at DESC (most recent first)
        titles = [t["title"] for t in tasks]
        self.assertEqual(titles, ["Task C", "Task B", "Task A"])

    def test_filter_by_done_true(self):
        # Create tasks with different done states
        t1 = self.client.post("/tasks/", json={"title": "Done task", "priority": 2}).json()
        t2 = self.client.post("/tasks/", json={"title": "Open task 1", "priority": 2}).json()
        t3 = self.client.post("/tasks/", json={"title": "Open task 2", "priority": 2}).json()

        # Complete t2
        self.client.patch(f"/tasks/{t2['id']}/complete")

        resp = self.client.get("/tasks/?done=true")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Open task 1")
        self.assertTrue(all(t["done"] for t in tasks))

    def test_filter_by_done_false(self):
        t1 = self.client.post("/tasks/", json={"title": "Done task", "priority": 2}).json()
        t2 = self.client.post("/tasks/", json={"title": "Open task 1", "priority": 2}).json()
        t3 = self.client.post("/tasks/", json={"title": "Open task 2", "priority": 2}).json()

        # Complete t1 and t2
        self.client.patch(f"/tasks/{t1['id']}/complete")
        self.client.patch(f"/tasks/{t2['id']}/complete")

        resp = self.client.get("/tasks/?done=false")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Open task 2")
        self.assertTrue(all(not t["done"] for t in tasks))

    def test_pagination_limit(self):
        # Create several tasks
        for i in range(5):
            self.client.post("/tasks/", json={"title": f"Task {i}", "priority": 2})

        resp = self.client.get("/tasks/?limit=3")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 3)
        # Should be most recent 3 tasks
        titles = [t["title"] for t in tasks]
        self.assertEqual(titles, ["Task 4", "Task 3", "Task 2"])

    def test_pagination_limit_and_offset(self):
        for i in range(5):
            self.client.post("/tasks/", json={"title": f"Task {i}", "priority": 2})

        resp = self.client.get("/tasks/?limit=2&offset=2")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 2)
        titles = [t["title"] for t in tasks]
        self.assertEqual(titles, ["Task 2", "Task 1"])

    def test_filter_and_pagination_combined(self):
        # Create mix of done and open tasks
        for i in range(3):
            t = self.client.post("/tasks/", json={"title": f"Open {i}", "priority": 2}).json()
            if i < 2:
                self.client.patch(f"/tasks/{t['id']}/complete")

        # Get open tasks with limit
        resp = self.client.get("/tasks/?done=false&limit=1")
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Open 2")  # most recent open

    def test_invalid_limit_offset_handled_by_fastapi(self):
        # Negative values should be rejected by FastAPI's ge validator
        resp = self.client.get("/tasks/?limit=-1")
        self.assertEqual(resp.status_code, 422)  # validation error

        resp = self.client.get("/tasks/?offset=-1")
        self.assertEqual(resp.status_code, 422)

    def test_done_filter_returns_empty_when_no_matches(self):
        # Create only done tasks
        t1 = self.client.post("/tasks/", json={"title": "Done 1", "priority": 2}).json()
        t2 = self.client.post("/tasks/", json={"title": "Done 2", "priority": 2}).json()
        self.client.patch(f"/tasks/{t1['id']}/complete")
        self.client.patch(f"/tasks/{t2['id']}/complete")

        resp = self.client.get("/tasks/?done=false")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_pagination_offset_beyond_length_returns_empty(self):
        for i in range(3):
            self.client.post("/tasks/", json={"title": f"Task {i}", "priority": 2})

        resp = self.client.get("/tasks/?limit=2&offset=10")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


if __name__ == '__main__':
    unittest.main()
