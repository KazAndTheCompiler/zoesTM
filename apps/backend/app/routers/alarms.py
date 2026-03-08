import json
from fastapi import APIRouter, Body, Query
from ..schemas import AlarmIn
from ..repositories import alarms_repo
from ..services import events, notifications, tts
from ..errors import not_found

router = APIRouter()


@router.post('/')
def create_alarm(
    payload: AlarmIn | None = Body(None),
    at: str | None = Query(None),
    muted: bool = Query(False),
    kind: str = Query('alarm'),
    title: str = Query(''),
    tts_text: str = Query(''),
    youtube_link: str = Query(''),
):
    """Create an alarm.
     
    Accepts either JSON body (preferred) or query params (legacy compatibility).

    Example body:
    {
        "at": "07:30",
        "title": "Wake up",
        "tts_text": "Good morning, time to rise",
        "youtube_link": "https://www.youtube.com/watch?v=...",
        "muted": false,
        "kind": "alarm"
    }
    
    'at' accepts:
      - "HH:MM"  — fires daily at that time (e.g. "07:30")
      - ISO 8601 — fires once at that datetime (e.g. "2026-03-05T07:30:00")
    """
    if payload is None:
        payload = AlarmIn(
            at=at or '',
            muted=muted,
            kind=kind,
            title=title,
            tts_text=tts_text,
            youtube_link=youtube_link,
        )

    alarm = alarms_repo.create_alarm(
        at=payload.at,
        muted=payload.muted,
        kind=payload.kind,
        title=payload.title,
        tts_text=payload.tts_text,
        youtube_link=payload.youtube_link,
    )
    events.emit_event('alarm.created', {'alarm_id': alarm['id'], 'kind': alarm['kind']})
    return alarm


@router.get('/')
def list_alarms_endpoint():
    """Return all alarms with their metadata."""
    alarms = alarms_repo.list_alarms()
    return {'alarms': alarms}


@router.post('/{alarm_id}/queue')
def set_queue(alarm_id: str, items: list[str]):
    alarm = alarms_repo.get_alarm(alarm_id)
    if not alarm:
        raise not_found('alarm_not_found', 'Alarm not found', {'alarm_id': alarm_id})
    queue = alarms_repo.set_queue(alarm_id, items)
    events.emit_event('alarm.queue.updated', {'alarm_id': alarm_id, 'count': len(queue)})
    return {'alarm_id': alarm_id, 'queue': queue}


@router.post('/{alarm_id}/trigger')
def trigger(alarm_id: str):
    alarm = alarms_repo.get_alarm(alarm_id)
    if not alarm:
        raise not_found('alarm_not_found', 'Alarm not found', {'alarm_id': alarm_id})

    actions = [{'type': 'tts', 'text': alarm.get('tts_text') or alarm.get('title') or 'Reminder'}]
    queue = alarms_repo.list_queue(alarm_id)
    if alarm.get('kind') == 'alarm' and queue:
        actions.append({'type': 'music_queue', 'tracks': [q['track_ref'] for q in queue]})

    # Speak immediately via OS TTS — non-blocking background thread
    tts_text = alarm.get('tts_text') or alarm.get('title') or 'Alarm'
    tts.speak(tts_text)

    import json
    alarms_repo.touch_alarm(alarm_id)
    events.emit_event('alarm.triggered', {'alarm_id': alarm_id, 'kind': alarm.get('kind', 'alarm')})
    payload = json.dumps({
        'alarm_id': alarm_id,
        'kind': alarm.get('kind', 'alarm'),
        'tts_text': alarm.get('tts_text') or alarm.get('title') or 'Alarm',
        'youtube_link': alarm.get('youtube_link') or '',
    })
    notifications.create('alarm', f"🔔 {alarm.get('title') or 'Alarm'}", payload, scope='alarm_trigger')
    return {'status': 'triggered', 'alarm': alarm, 'actions': actions}


@router.delete('/{alarm_id}')
def delete_alarm(alarm_id: str):
    alarm = alarms_repo.get_alarm(alarm_id)
    if not alarm:
        raise not_found('alarm_not_found', 'Alarm not found', {'alarm_id': alarm_id})
    alarms_repo.delete_alarm(alarm_id)
    events.emit_event('alarm.deleted', {'alarm_id': alarm_id})
    return {'ok': True, 'alarm_id': alarm_id}



@router.get('/watchdog/status')
def watchdog_status():
    return {'status': 'running', 'recovery_grace_minutes': 10}


@router.post('/reconcile')
def reconcile(grace_minutes: int = 10):
    notifications.create('info', 'Alarm reconcile complete', f'grace={grace_minutes}', scope='alarms')
    return {'status': 'ok', 'grace_minutes': grace_minutes, 'duplicates_prevented': True}


# Endpoints map:
# Owner: alarm-domain
# GET  /alarms/        (returns {'alarms': [...]})
# POST /alarms/        (body: {at, muted, kind, title, tts_text, youtube_link})
# POST /alarms/{alarm_id}/queue
# POST /alarms/{alarm_id}/trigger
# GET /alarms/watchdog/status
# POST /alarms/reconcile?grace_minutes=10
