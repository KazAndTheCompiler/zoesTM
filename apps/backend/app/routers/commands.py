import json
from fastapi import APIRouter
from ..schemas import CommandIn
from ..services.command_center import parse_intent
from ..repositories import commands_repo
from ..services import events, notifications
from ..errors import bad_request, conflict

router = APIRouter()


@router.post('/parse')
def parse(payload: CommandIn):
    return parse_intent(payload.text)


@router.post('/preview')
def preview(payload: CommandIn):
    parsed = parse_intent(payload.text)
    return {'mode': 'dry-run', 'parsed': parsed, 'would_execute': parsed['intent'] != 'unknown'}


@router.post('/execute')
def execute(payload: CommandIn, confirmation_token: str | None = None):
    parsed = parse_intent(payload.text)
    intent = parsed['intent']
    if intent == 'unknown':
        commands_repo.add_log(payload.text, intent, status='error', error=json.dumps(parsed))
        notifications.create('warn', 'Command rejected', payload.text, scope='commands')
        raise bad_request('unknown_command', 'Unknown command')
    confirmed = payload.confirm or (confirmation_token == 'CONFIRM')
    if any(i.startswith('danger.') for i in parsed.get('intents', [])) and not confirmed:
        commands_repo.add_log(payload.text, intent, status='blocked', error='confirmation token required')
        raise conflict('confirmation_required', 'Confirmation required')
    commands_repo.add_log(payload.text, intent, status='ok', error=json.dumps(parsed))
    events.emit_event('command.executed', {'text': payload.text, 'intent': intent})
    return {'text': payload.text, 'intent': intent, 'status': 'ok', 'confidence': parsed['confidence']}


@router.get('/history')
def history(limit: int = 100):
    return commands_repo.history(limit)


# Endpoints map:
# Owner: command-domain
# POST /commands/parse
# POST /commands/preview
# POST /commands/execute?confirmation_token=CONFIRM
# GET /commands/history?limit=100
