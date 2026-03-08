from fastapi import APIRouter
from ..services import pomodoro
from ..errors import conflict

router = APIRouter()


@router.post('/start')
def start(minutes: int = 25):
    return pomodoro.start(minutes)


@router.post('/pause')
def pause():
    if pomodoro.state.status != 'running':
        raise conflict('invalid_transition', 'Invalid pomodoro transition', {'from': pomodoro.state.status, 'to': 'paused'})
    return pomodoro.pause()


@router.post('/resume')
def resume():
    if pomodoro.state.status != 'paused':
        raise conflict('invalid_transition', 'Invalid pomodoro transition', {'from': pomodoro.state.status, 'to': 'running'})
    return pomodoro.resume()


@router.post('/complete')
def complete():
    if pomodoro.state.status not in ('running', 'paused'):
        raise conflict('invalid_transition', 'Invalid pomodoro transition', {'from': pomodoro.state.status, 'to': 'idle'})
    return pomodoro.complete()


@router.get('/status')
def status():
    return pomodoro.status()


# Endpoints map:
# Owner: focus-domain
# POST /focus/start?minutes=25
# POST /focus/pause
# POST /focus/resume
# POST /focus/complete
# GET /focus/status
