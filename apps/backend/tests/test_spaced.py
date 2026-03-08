import unittest

from apps.backend.app.services.spaced import next_interval, compute_next_interval


class TestSpacedService(unittest.TestCase):
    def test_new_good_progression(self):
        state, interval = next_interval("new", "good", 1)
        self.assertEqual(state, "review")
        self.assertGreaterEqual(interval, 1)

    def test_existing_good_uses_ease_factor(self):
        # With default ease factor 2.5, interval 4 yields 10 days
        state, interval = next_interval("review", "good", 4)
        self.assertEqual(state, "review")
        self.assertEqual(interval, 10)

    def test_ease_factor_adjustment_hard(self):
        result = compute_next_interval("review", "hard", 10, 2.5, 5)
        self.assertEqual(result['new_state'], 'review')
        self.assertEqual(result['new_interval'], 12)  # 10*1.2=12
        self.assertEqual(result['new_ease_factor'], 2.35)  # 2.5 - 0.15

    def test_ease_factor_adjustment_easy(self):
        result = compute_next_interval("review", "easy", 10, 2.5, 5)
        self.assertEqual(result['new_state'], 'review')
        self.assertEqual(result['new_interval'], 32)  # 10*2.5*1.3 = 32.5 -> 32
        self.assertEqual(result['new_ease_factor'], 2.5)  # capped at 2.5

    def test_again_on_review_triggers_relearn(self):
        result = compute_next_interval("review", "again", 10, 2.5, 5)
        self.assertEqual(result['new_state'], 'relearn')
        self.assertEqual(result['new_interval'], 1)
        self.assertEqual(result['new_ease_factor'], 2.3)
        self.assertTrue(result['lapse_increment'])

    def test_again_on_learning(self):
        result = compute_next_interval("learning", "again", 1, 2.5, 0)
        self.assertEqual(result['new_state'], 'learning')
        self.assertEqual(result['new_interval'], 1)
        self.assertTrue(result['lapse_increment'])


if __name__ == "__main__":
    unittest.main()

