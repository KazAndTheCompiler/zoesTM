import unittest

from apps.backend.app.routers import calendar, alarms, player
from apps.backend.app.schemas import AlarmIn


class TestPrototypeBatch(unittest.TestCase):
    def test_calendar_modes(self):
        for mode in ('day', 'week', 'month'):
            out = calendar.view(mode=mode)
            self.assertEqual(out['mode'], mode)
            self.assertIn('entries', out)

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
