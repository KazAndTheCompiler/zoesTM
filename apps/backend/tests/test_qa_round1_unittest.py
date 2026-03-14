import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, UTC
from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db
from apps.backend.app.repositories import alarms_repo, habits_repo, tasks_repo
from apps.backend.app.routers import boards, calendar, focus, review
from apps.backend.app.services.habits import weekly_overview
from apps.backend.app.services.quick_add import parse_quick_add


class QARound1Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "qa_round1.db"
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)

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


class TestTasksCrudEdges(QARound1Base):
    def test_create_list_complete_and_missing(self):
        created = self.client.post("/tasks/", json={"title": "qa task", "priority": 2}).json()
        self.assertEqual(created["title"], "qa task")

        listing = self.client.get("/tasks/").json()
        self.assertTrue(any(t["id"] == created["id"] for t in listing))

        completed = self.client.patch(f"/tasks/{created['id']}/complete").json()
        self.assertEqual(completed["done"], 1)

        missing = self.client.patch("/tasks/not-a-real-id/complete")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "task_not_found")

    def test_materialize_recurring_idempotent(self):
        parent = tasks_repo.create_task({
            "title": "Daily standup",
            "priority": 2,
            "due_at": "2026-03-01T09:00:00+00:00",
            "recurrence_rule": "FREQ=DAILY",
        })
        first = self.client.post("/tasks/materialize-recurring?window_hours=72").json()
        second = self.client.post("/tasks/materialize-recurring?window_hours=72").json()

        self.assertGreaterEqual(first["templates"], 1)
        self.assertEqual(second["created"], 0)

        children = [t for t in tasks_repo.list_tasks() if t.get("recurrence_parent_id") == parent["id"]]
        self.assertEqual(len(children), 1)


class TestQuickAddEdges(unittest.TestCase):
    def test_ambiguous_time_sets_flag_and_candidates(self):
        out = parse_quick_add("tmrw fri eve in 2h #ops")
        self.assertTrue(out["ambiguity"])
        self.assertGreaterEqual(len(out["candidates"]), 2)

    def test_missing_title_falls_back_to_text(self):
        out = parse_quick_add("   #ops !high tomorrow   ")
        self.assertTrue(out["title"])
        self.assertEqual(out["priority"], 1)

    def test_malformed_tokens_do_not_crash(self):
        out = parse_quick_add("@@@ !!! ### in xxh")
        self.assertIn("title", out)
        self.assertIn("confidence", out)


class TestCalendarBoardsFocusReview(QARound1Base):
    def test_calendar_feed_filters_entries_without_at(self):
        in_window = (datetime.now(UTC) + timedelta(hours=6)).isoformat().replace('+00:00', 'Z')
        tasks_repo.create_task({"title": "with due", "due_at": in_window, "priority": 2})
        tasks_repo.create_task({"title": "without due", "priority": 2})
        out = calendar.feed(
            from_=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            to=(datetime.now(UTC) + timedelta(days=1)).isoformat().replace('+00:00', 'Z'),
        )
        titles = [e["title"] for e in out["entries"]]
        self.assertIn("with due", titles)
        self.assertNotIn("without due", titles)

    def test_calendar_invalid_window_returns_empty_entries(self):
        out = calendar.feed(from_="invalid", to="2026-03-01T00:00:00Z")
        self.assertEqual(out["entries"], [])
        self.assertEqual(out["owner"], "zoestm")

    def test_focus_invalid_transitions_are_rejected(self):
        from apps.backend.app.errors import ApiError

        focus.start(minutes=1)
        focus.complete()
        with self.assertRaises(ApiError) as paused:
            focus.pause()
        self.assertEqual(paused.exception.status_code, 409)

        with self.assertRaises(ApiError) as resumed:
            focus.resume()
        self.assertEqual(resumed.exception.status_code, 409)

    def test_alarm_queue_cap_order_and_replace(self):
        alarm = alarms_repo.create_alarm(at="07:00")
        items = [f"track-{i}" for i in range(30)]
        q1 = alarms_repo.set_queue(alarm["id"], items)
        self.assertEqual(len(q1), 20)
        self.assertEqual(q1[0]["track_ref"], "track-0")
        self.assertEqual(q1[-1]["track_ref"], "track-19")

        q2 = alarms_repo.set_queue(alarm["id"], ["replaced-1", "replaced-2"])
        self.assertEqual([x["track_ref"] for x in q2], ["replaced-1", "replaced-2"])

    def test_habits_weekly_mixed_dataset(self):
        habits_repo.log_checkin("hydrate", True)
        habits_repo.log_checkin("hydrate", False)
        habits_repo.log_checkin("stretch", True)
        summary = weekly_overview(habits_repo.get_logs(limit=3))
        self.assertEqual(summary["misses"], 1)
        self.assertEqual(summary["streak"], 2)

    def test_matrix_rule_precedence_and_manual_override(self):
        self.assertEqual(boards.matrix(priority=1, due_soon=True)["quadrant"], "do")
        self.assertEqual(boards.matrix(priority=1, due_soon=False)["quadrant"], "schedule")
        self.assertEqual(boards.matrix(priority=3, due_soon=True)["quadrant"], "delegate")

    def test_review_scheduler_transitions(self):
        deck = self.client.post('/review/decks?name=Scheduler Test').json()
        deck_id = deck['id']
        card = self.client.post(f'/review/decks/{deck_id}/cards', params={'front': 'Q', 'back': 'A'}).json()
        card_id = card['id']

        sess_start = self.client.post('/review/session/start?limit=1').json()
        self.assertEqual(sess_start['count'], 1)
        self.assertEqual(sess_start['cards'][0]['id'], card_id)

        for rating in ['again', 'hard', 'good', 'easy']:
            resp = self.client.post(f'/review/answer?rating={rating}&card_id={card_id}')
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertIn('session', body)
            self.assertIn('state', body['session'])
            self.assertIn('card', body)
            self.assertEqual(body['card']['id'], card_id)


class TestCommandsAndRepo(QARound1Base):
    def test_command_confirm_and_unknown_flow(self):
        bad = self.client.post("/commands/execute", json={"text": "gibberish"})
        self.assertEqual(bad.status_code, 400)

        blocked = self.client.post("/commands/execute", json={"text": "delete task 1"})
        self.assertEqual(blocked.status_code, 409)

        ok = self.client.post("/commands/execute?confirmation_token=CONFIRM", json={"text": "delete task 1"})
        self.assertEqual(ok.status_code, 200)

    def test_repository_rollback_on_error(self):
        from apps.backend.app.db import tx, conn

        start_count = len(tasks_repo.list_tasks())
        with self.assertRaises(sqlite3.OperationalError):
            with tx() as c:
                c.execute("INSERT INTO tasks(id,title,due_at,priority,done) VALUES('rollback-id','tmp',NULL,2,0)")
                c.execute("INSERT INTO non_existent_table(x) VALUES(1)")

        with conn() as c:
            row = c.execute("SELECT COUNT(*) as n FROM tasks WHERE id='rollback-id'").fetchone()
        self.assertEqual(row["n"], 0)
        self.assertGreaterEqual(len(tasks_repo.list_tasks()), start_count)


class TestMigrationsFreshDb(unittest.TestCase):
    def test_all_migrations_apply_on_fresh_sqlite(self):
        mig_dir = Path(__file__).resolve().parents[1] / "migrations"
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "fresh.db"
            with sqlite3.connect(db_path) as c:
                for mig in sorted(mig_dir.glob("*.sql")):
                    c.executescript(mig.read_text(encoding="utf-8"))
                table_count = c.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchone()[0]
        self.assertGreater(table_count, 5)


if __name__ == "__main__":
    unittest.main()
