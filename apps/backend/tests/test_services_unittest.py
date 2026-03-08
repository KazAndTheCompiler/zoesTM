import unittest

from apps.backend.app.services.quick_add import parse_quick_add
from apps.backend.app.services.spaced import next_interval
from apps.backend.app.services.eisenhower import quadrant
from apps.backend.app.services.habits import weekly_overview
from apps.backend.app.services.player import rotate_queue
from apps.backend.app.services.command_center import parse_intent


class TestServices(unittest.TestCase):
    def test_quick_add_parses_priority_tag_due(self):
        out = parse_quick_add("Pay rent tomorrow 9pm #finance !high")
        self.assertEqual(out["priority"], 1)
        self.assertIn("finance", out["tags"])
        self.assertIsNotNone(out["due_at"])
        self.assertGreaterEqual(out["confidence"], 0.7)

    def test_spaced_interval_progression(self):
        state, iv = next_interval("new", "good", 1)
        self.assertEqual(state, "review")
        self.assertGreaterEqual(iv, 1)

    def test_eisenhower(self):
        self.assertEqual(quadrant(priority=1, due_soon=True), "do")
        self.assertEqual(quadrant(priority=1, due_soon=False), "schedule")

    def test_habits_weekly(self):
        summary = weekly_overview([
            {"habit_name": "Exercise", "done": True, "logged_at": "2026-03-06T10:00:00Z"},
            {"habit_name": "Exercise", "done": False, "logged_at": "2026-03-05T10:00:00Z"},
            {"habit_name": "Exercise", "done": True, "logged_at": "2026-03-04T10:00:00Z"},
        ])
        self.assertEqual(summary["completion_pct"], round((2/3)*100, 1))
        self.assertEqual(summary["misses"], 1)

    def test_queue_rotation_cap(self):
        items = [f"track-{i}" for i in range(30)]
        out = rotate_queue(items, 20)
        self.assertEqual(len(out), 20)
        self.assertEqual(out[0], "track-0")

    def test_command_intents(self):
        self.assertEqual(parse_intent("add task clean desk")["intent"], "task.create")
        self.assertEqual(parse_intent("start pomodoro 25")["intent"], "focus.start")
        self.assertEqual(parse_intent("set alarm 07:00")["intent"], "alarm.create")


if __name__ == "__main__":
    unittest.main()
