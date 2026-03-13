import re
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from ..errors import conflict, not_found, bad_request
from ..repositories import habits_repo, journal_repo
from ..schemas import JournalIn, JournalPatch
from ..services import events
from ..services.authz import require_scopes

router = APIRouter()
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')


def _require_date(value: str) -> str:
    if not DATE_RE.match(value or ''):
        raise bad_request('validation_error', 'Invalid ISO date', {'field': 'date', 'value': value})
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as exc:
        raise bad_request('validation_error', 'Invalid ISO date', {'field': 'date', 'value': value}) from exc
    return value


def _strip_markdown(text: str) -> str:
    text = re.sub(r'`([^`]*)`', r'\1', text or '')
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^[#>*\-]+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'[*_~]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _habit_summary(for_date: str) -> dict:
    names = []
    done = 0
    total = 0
    for log in habits_repo.get_logs(limit=2000):
        logged_at = str(log.get('logged_at') or '')
        if not logged_at.startswith(for_date):
            continue
        total += 1
        name = log.get('habit_name')
        if name:
            names.append(name)
        if bool(log.get('done')):
            done += 1
    names = sorted(dict.fromkeys(names))
    return {'done': done, 'total': total, 'names': names}


def _calendar_events(for_date: str) -> list:
    url = 'http://localhost:8001/calendar/range'
    params = {
        'start': f'{for_date}T00:00:00Z',
        'end': f'{for_date}T23:59:59Z',
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            return payload.get('entries', []) if isinstance(payload, dict) else []
    except Exception:
        return []


def _export_payload(for_date: str) -> dict:
    return {
        'date': for_date,
        'journal': journal_repo.get_entry_by_date(for_date),
        'habits': _habit_summary(for_date),
        'events': _calendar_events(for_date),
    }


def _as_text(payload: dict) -> str:
    journal = payload.get('journal') or {}
    habits = payload['habits']
    events_list = payload['events']
    events_text = '\n'.join(f"- {e.get('title', 'Untitled')} @ {e.get('at', '')}" for e in events_list) or '- none'
    journal_text = _strip_markdown(journal.get('markdown_body', '')) or '(no journal entry)'
    return '\n'.join([
        payload['date'],
        f"Habits: {habits['done']}/{habits['total']} done",
        'Events:',
        events_text,
        'Journal:',
        journal_text,
    ])


def _as_markdown(payload: dict) -> str:
    journal = payload.get('journal') or {}
    habits = payload['habits']
    events_list = payload['events']
    lines = [
        f"# Daily Digest — {payload['date']}",
        '',
        '## Habits',
        f"{habits['done']}/{habits['total']} done",
    ]
    if habits['names']:
        lines.extend(['', *[f"- {name}" for name in habits['names']]])
    lines.extend(['', '## Events'])
    if events_list:
        lines.extend([f"- {e.get('title', 'Untitled')} @ {e.get('at', '')}" for e in events_list])
    else:
        lines.append('- none')
    lines.extend(['', '## Journal', journal.get('markdown_body', '') if journal else ''])
    return '\n'.join(lines).strip() + '\n'


@router.post('/', status_code=201, dependencies=[Depends(require_scopes({'write:journal'}))])
def create_journal_entry(payload: JournalIn):
    data = payload.model_dump(exclude_none=True)
    if data.get('date') is not None:
        data['date'] = _require_date(data['date'])
    try:
        entry = journal_repo.create_entry(data)
    except ValueError as exc:
        if str(exc) == 'duplicate_date':
            raise conflict('journal_conflict', 'Journal entry already exists for that date', {'date': data.get('date')})
        raise
    events.emit_event('journal.created', {'entry_id': entry['id'], 'date': entry['date']})
    return entry


@router.get('/', dependencies=[Depends(require_scopes({'read:journal'}))])
def list_journal_entries(
    limit: int | None = Query(None, ge=1),
    offset: int | None = Query(None, ge=0),
):
    return journal_repo.list_entries(limit=limit, offset=offset)


@router.get('/export/{date}', dependencies=[Depends(require_scopes({'read:journal'}))])
def export_journal(date: str, format: str = Query('json', pattern='^(json|text|markdown)$')):
    date = _require_date(date)
    payload = _export_payload(date)
    if format == 'text':
        return PlainTextResponse(_as_text(payload))
    if format == 'markdown':
        return PlainTextResponse(_as_markdown(payload), media_type='text/markdown; charset=utf-8')
    return payload


@router.get('/by-id/{entry_id}', dependencies=[Depends(require_scopes({'read:journal'}))])
def get_journal_entry_by_id(entry_id: str):
    entry = journal_repo.get_entry(entry_id)
    if not entry:
        raise not_found('journal_not_found', 'Journal entry not found', {'entry_id': entry_id})
    return entry


@router.get('/by-date/{date}', dependencies=[Depends(require_scopes({'read:journal'}))])
def get_journal_entry_by_date(date: str):
    date = _require_date(date)
    entry = journal_repo.get_entry_by_date(date)
    if not entry:
        raise not_found('journal_not_found', 'Journal entry not found', {'date': date})
    return entry


@router.get('/{value}', dependencies=[Depends(require_scopes({'read:journal'}))])
def get_journal_entry_compat(value: str):
    if DATE_RE.match(value or ''):
        return get_journal_entry_by_date(value)
    if UUID_RE.match(value or ''):
        return get_journal_entry_by_id(value)
    raise not_found('journal_not_found', 'Journal entry not found', {'value': value})


@router.patch('/{entry_id}', dependencies=[Depends(require_scopes({'write:journal'}))])
def update_journal_entry(entry_id: str, payload: JournalPatch):
    body = payload.model_dump(exclude_unset=True)
    entry = journal_repo.update_entry(entry_id, body)
    if not entry:
        raise not_found('journal_not_found', 'Journal entry not found', {'entry_id': entry_id})
    events.emit_event('journal.updated', {'entry_id': entry['id'], 'date': entry['date']})
    return entry


@router.delete('/{entry_id}', dependencies=[Depends(require_scopes({'write:journal'}))])
def delete_journal_entry(entry_id: str):
    existing = journal_repo.get_entry(entry_id)
    if not existing:
        raise not_found('journal_not_found', 'Journal entry not found', {'entry_id': entry_id})
    ok = journal_repo.delete_entry(entry_id)
    if not ok:
        raise not_found('journal_not_found', 'Journal entry not found', {'entry_id': entry_id})
    events.emit_event('journal.deleted', {'entry_id': entry_id, 'date': existing['date']})
    return {'ok': True}


# Endpoints map:
# Owner: journal-domain
# POST /journal/
# GET /journal/
# GET /journal/export/{date}
# GET /journal/by-id/{id}
# GET /journal/by-date/{date}
# GET /journal/{id-or-date}
# PATCH /journal/{id}
# DELETE /journal/{id}
