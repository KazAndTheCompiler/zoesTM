import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, UTC
from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.app.main import app
from apps.backend.app import db


class QARound2Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db.DB_PATH
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "qa_round2.db"
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


class TestAlarmPlayerReliability(QARound2Base):
    def test_alarm_missing_returns_404_for_queue_and_trigger(self):
        q = self.client.post("/alarms/missing-id/queue", json=["yt:a"])
        self.assertEqual(q.status_code, 404)
        self.assertEqual(q.json()["error"]["code"], "alarm_not_found")

        t = self.client.post("/alarms/missing-id/trigger")
        self.assertEqual(t.status_code, 404)
        self.assertEqual(t.json()["error"]["code"], "alarm_not_found")

    def test_player_queue_is_deduped_sanitized_and_capped(self):
        payload = ["a", " a ", "", "b"] + [f"x{i}" for i in range(30)]
        out = self.client.post("/player/queue", json=payload)
        self.assertEqual(out.status_code, 200)
        items = out.json()["items"]
        self.assertEqual(items[0:2], ["a", "b"])
        self.assertEqual(len(items), 20)


class TestCalendarBridgeContract(QARound2Base):
    def test_feed_filters_entries_by_strict_window(self):
        self.client.post("/tasks/", json={"title": "inside-start", "due_at": "2026-03-02T10:00:00Z", "priority": 2})
        self.client.post("/tasks/", json={"title": "inside-end", "due_at": "2026-03-02T15:00:00Z", "priority": 2})
        self.client.post("/tasks/", json={"title": "outside-before", "due_at": "2026-03-01T23:00:00Z", "priority": 2})
        self.client.post("/tasks/", json={"title": "outside-after", "due_at": "2026-03-03T01:00:00Z", "priority": 2})
        self.client.post("/tasks/", json={"title": "no-due", "priority": 2})

        start = "2026-03-02T00:00:00Z"
        end = "2026-03-02T23:59:59Z"
        resp = self.client.get(f"/calendar/feed?from_={start}&to={end}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        titles = [e["title"] for e in data["entries"]]
        self.assertIn("inside-start", titles)
        self.assertIn("inside-end", titles)
        self.assertNotIn("outside-before", titles)
        self.assertNotIn("outside-after", titles)
        self.assertNotIn("no-due", titles)
        self.assertEqual(data["from"], start)
        self.assertEqual(data["to"], end)
        self.assertEqual(data["owner"], "zoestm")

    def test_feed_boundary_inclusion(self):
        self.client.post("/tasks/", json={"title": "boundary-start", "due_at": "2026-03-05T00:00:00Z", "priority": 2})
        self.client.post("/tasks/", json={"title": "boundary-end", "due_at": "2026-03-05T23:59:59Z", "priority": 2})

        start = "2026-03-05T00:00:00Z"
        end = "2026-03-05T23:59:59Z"
        resp = self.client.get(f"/calendar/feed?from_={start}&to={end}")
        self.assertEqual(resp.status_code, 200)
        titles = [e["title"] for e in resp.json()["entries"]]
        self.assertIn("boundary-start", titles)
        self.assertIn("boundary-end", titles)

    def test_feed_invalid_params_returns_empty_entries(self):
        resp = self.client.get("/calendar/feed?from_=invalid&to=2026-03-05T00:00:00Z")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["entries"], [])
        self.assertEqual(resp.json()["from"], "invalid")

    def test_feed_includes_alarm_mirror_entries(self):
        now = datetime.now(UTC)
        alarm_at = (now + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        self.client.post(
            "/alarms/",
            params={
                "at": alarm_at,
                "kind": "reminder",
                "title": "alarm-in-feed",
                "tts_text": "alarm-in-feed",
            },
        )
        start = now.isoformat().replace('+00:00', 'Z')
        end = (now + timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        resp = self.client.get(f"/calendar/feed?from_={start}&to={end}")
        self.assertEqual(resp.status_code, 200)
        titles = [e["title"] for e in resp.json()["entries"]]
        self.assertIn("🔔 alarm-in-feed", titles)


class TestIntegrationFlows(QARound2Base):
    def test_task_to_calendar_feed_to_reminder_flow(self):
        task = self.client.post(
            "/tasks/",
            json={"title": "pay rent", "priority": 1, "due_at": "2026-03-02T08:00:00+00:00"},
        )
        self.assertEqual(task.status_code, 200)

        cal = self.client.get("/calendar/feed?from_=2026-03-02T00:00:00Z&to=2026-03-02T23:59:59Z")
        self.assertEqual(cal.status_code, 200)
        titles = [e["title"] for e in cal.json()["entries"]]
        self.assertIn("pay rent", titles)

        reminder = self.client.post(
            "/alarms/?at=2026-03-02T07:50:00+00:00&kind=reminder&title=pay rent reminder&tts_text=pay rent"
        )
        self.assertEqual(reminder.status_code, 200)

        triggered = self.client.post(f"/alarms/{reminder.json()['id']}/trigger")
        self.assertEqual(triggered.status_code, 200)
        actions = triggered.json()["actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "tts")

    def test_review_rating_to_next_interval_flow(self):
        deck = self.client.post('/review/decks?name=Interval Test').json()
        deck_id = deck['id']
        card = self.client.post(f'/review/decks/{deck_id}/cards', params={'front': 'Q', 'back': 'A'}).json()
        card_id = card['id']

        sess = self.client.post('/review/session/start?limit=1').json()
        self.assertEqual(sess['count'], 1)
        self.assertEqual(sess['cards'][0]['id'], card_id)

        again = self.client.post(f'/review/answer?rating=again&card_id={card_id}')
        self.assertEqual(again.status_code, 200)
        self.assertIn('session', again.json())
        self.assertIn('card', again.json())

        good = self.client.post(f'/review/answer?rating=good&card_id={card_id}')
        self.assertEqual(good.status_code, 200)
        self.assertIn('session', good.json())
        self.assertIn('card', good.json())


if __name__ == "__main__":
    unittest.main()
