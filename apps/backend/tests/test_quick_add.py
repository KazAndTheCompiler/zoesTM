import unittest
from datetime import datetime, UTC, timedelta

from apps.backend.app.services.quick_add import parse_quick_add


class TestQuickAddService(unittest.TestCase):
    def test_parser_returns_expected_shape(self):
        out = parse_quick_add("Pay rent tomorrow 9pm #finance !high")
        self.assertTrue(out["title"])
        self.assertEqual(out["priority"], 1)
        self.assertIn("finance", out["tags"])
        self.assertIsNotNone(out["due_at"])
        self.assertGreaterEqual(out["confidence"], 0.5)
        self.assertLessEqual(out["confidence"], 1)

    def test_parser_handles_plain_input(self):
        out = parse_quick_add("Write report")
        self.assertEqual(out["title"], "Write report")
        self.assertEqual(out["priority"], 2)
        self.assertEqual(out["tags"], [])
        self.assertIsNone(out["due_at"])

    def test_explicit_time_with_tomorrow(self):
        out = parse_quick_add("Call mom tomorrow 9pm")
        self.assertIsNotNone(out["due_at"])
        due = datetime.fromisoformat(out["due_at"].replace('Z', '+00:00'))
        # Should be tomorrow at 21:00
        self.assertEqual(due.hour, 21)
        self.assertEqual(due.minute, 0)

    def test_explicit_time_with_colon(self):
        out = parse_quick_add("Meeting tomorrow 14:30")
        self.assertIsNotNone(out["due_at"])
        due = datetime.fromisoformat(out["due_at"].replace('Z', '+00:00'))
        self.assertEqual(due.hour, 14)
        self.assertEqual(due.minute, 30)

    def test_in_minutes_parsing(self):
        out = parse_quick_add("Standup in 30min")
        self.assertIsNotNone(out["due_at"])
        due = datetime.fromisoformat(out["due_at"].replace('Z', '+00:00'))
        now = datetime.now(UTC)
        delta = due - now
        self.assertGreater(delta.total_seconds(), 0)
        # Should be approximately 30 minutes (allow small tolerance)
        self.assertLess(abs(delta.total_seconds() - 1800), 2)

    def test_in_30min_multiple_candidates_ambiguity(self):
        out = parse_quick_add("Task in 30min tomorrow")
        # This should produce ambiguity (two candidates)
        self.assertTrue(out["ambiguity"])
        self.assertEqual(len(out["candidates"]), 2)

    def test_default_time_without_explicit(self):
        out = parse_quick_add("Review PR tomorrow")
        self.assertIsNotNone(out["due_at"])
        due = datetime.fromisoformat(out["due_at"].replace('Z', '+00:00'))
        # Default tomorrow 9am
        self.assertEqual(due.hour, 9)
        self.assertEqual(due.minute, 0)


if __name__ == "__main__":
    unittest.main()
