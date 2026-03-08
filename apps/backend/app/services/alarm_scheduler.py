"""
Alarm scheduler — runs in the background, checks every minute,
fires trigger() for any alarm whose time has come.

HH:MM alarms fire in LOCAL time (respects system timezone).
ISO 8601 alarms fire at the exact specified datetime.
Each alarm can only fire once per 90-second window to prevent double-fire.
"""
import json
import logging
from datetime import datetime, UTC, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from ..repositories import alarms_repo
from ..services import notifications
from ..services import tts

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _check_alarms():
    now_local = _local_now()
    now_utc = datetime.now(UTC)

    try:
        alarms = alarms_repo.list_alarms()
    except Exception as e:
        logger.error(f"[alarm_scheduler] DB read failed: {e}")
        return

    for alarm in alarms:
        if not alarm.get('enabled'):
            continue
        if alarm.get('muted'):
            continue

        alarm_time_str = alarm.get('alarm_time', '')
        if not alarm_time_str:
            continue

        try:
            if len(alarm_time_str) <= 5:
                hh, mm = alarm_time_str.split(':')
                alarm_dt = now_local.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                delta_seconds = (now_local - alarm_dt).total_seconds()
            else:
                alarm_dt = datetime.fromisoformat(alarm_time_str.replace('Z', '+00:00'))
                if alarm_dt.tzinfo is None:
                    alarm_dt = alarm_dt.replace(tzinfo=UTC)
                delta_seconds = (now_utc - alarm_dt).total_seconds()
        except Exception:
            continue

        if not (0 <= delta_seconds < 90):
            continue

        # Check last_fired_at — skip if fired within last 90 seconds
        last_fired = alarm.get('last_fired_at')
        if last_fired:
            try:
                last_fired_dt = datetime.fromisoformat(last_fired).replace(tzinfo=UTC)
                if (now_utc - last_fired_dt).total_seconds() < 90:
                    logger.debug(f"[alarm_scheduler] Skipping {alarm['id']} — fired recently")
                    continue
            except Exception:
                pass

        _fire_alarm(alarm)


def _fire_alarm(alarm: dict):
    alarm_id = alarm['id']
    title = alarm.get('title') or 'Alarm'
    tts_text = alarm.get('tts_text') or title
    youtube_link = alarm.get('youtube_link') or ''
    kind = alarm.get('kind', 'alarm')

    logger.info(f"[alarm_scheduler] Firing alarm {alarm_id} — {title!r}")

    try:
        alarms_repo.set_last_fired(alarm_id)
        tts.speak(tts_text)

        payload = json.dumps({
            'alarm_id': alarm_id,
            'kind': kind,
            'tts_text': tts_text,
            'youtube_link': youtube_link,
        })
        notifications.create(
            level='alarm',
            title=f'🔔 {title}',
            body=payload,
            scope='alarm_trigger',
        )
    except Exception as e:
        logger.error(f"[alarm_scheduler] Failed to fire alarm {alarm_id}: {e}")


def start():
    global _scheduler
    if _scheduler is not None:
        return
    local_tz = datetime.now().astimezone().tzname()
    logger.info(f"[alarm_scheduler] Starting — local timezone: {local_tz}")
    _scheduler = BackgroundScheduler(timezone='UTC')
    _scheduler.add_job(_check_alarms, 'interval', minutes=1, id='alarm_check', replace_existing=True)
    _scheduler.start()
    logger.info("[alarm_scheduler] Started — checking every 60s")


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[alarm_scheduler] Stopped")
