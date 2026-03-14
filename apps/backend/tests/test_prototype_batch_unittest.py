import unittest
from datetime import datetime, timedelta, UTC

from apps.backend.app.routers import calendar, alarms, player
from apps.backend.app.schemas import AlarmIn
from apps.backend.app.repositories import tasks_repo


class TestPrototypeBatch(unittest.TestCase):
    def test_calendar_feed_filters_entries_by_window(self):
        inside = (datetime.now(UTC) + timedelta(hours=2)).isoformat().replace('+00:00', 'Z')
        outside = (datetime.now(UTC) + timedelta(days=10)).isoformat().replace('+00:00', 'Z')
        tasks_repo.create_task({"title": "feed-inside", "due_at": inside, "priority": 2})
        tasks_repo.create_task({"title": "feed-outside", "due_at": outside, "priority": 2})

        window_start = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        window_end = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        out = calendar.feed(from_=window_start, to=window_end)

        titles = [entry['title'] for entry in out['entries']]
        self.assertIn('feed-inside', titles)
        self.assertNotIn('feed-outside', titles)
        self.assertEqual(out['owner'], 'zoestm')

    def test_alarm_vs_reminder_trigger(self):
        alarm = alarms.create_alarm(AlarmIn(at='07:00', kind='alarm', title='wake', tts_text='wake now'))
        alarms.set_queue(alarm['id'], ['yt:abc'])
        tr_alarm = alarms.trigger(alarm['id'])
        self.assertEqual(len(tr_alarm['actions']), 2)

        rem = alarms.create_alarm(AlarmIn(at='09:00', kind='reminder', title='drink water', tts_text='hydrate'))
        tr_rem = alarms.trigger(rem['id'])
        self.assertEqual(len(tr_rem['actions']), 1)
        self.assertEqual(tr_rem['actions'][0]['type'], 'tts')

    def test_player_predownload_and_queue(self):
        q = player.replace_local_queue(['a', 'b', 'c'])
        self.assertEqual(q['count'], 3)
        job = player.enqueue('yt:test')
        tick = player.tick(job['id'])
        self.assertIn(tick['job']['state'], ('downloading', 'completed'))


if __name__ == '__main__':
    unittest.main()
