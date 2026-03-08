import unittest

from apps.backend.app.services.command_center import parse_intent
from apps.backend.app.services.quick_add import parse_quick_add


class TestPack05Pack06(unittest.TestCase):
    def test_command_chain_parse(self):
        out = parse_intent('focus 25 then break 5 then queue lofi')
        self.assertEqual(out['intent'], 'focus.start')
        self.assertGreaterEqual(len(out['intents']), 3)

    def test_quick_add_variants(self):
        out = parse_quick_add('tmrw 9am ship notes #ops !high')
        self.assertEqual(out['priority'], 1)
        self.assertIn('ops', out['tags'])
        self.assertIsNotNone(out['due_at'])


if __name__ == '__main__':
    unittest.main()
