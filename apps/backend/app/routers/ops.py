import hashlib
import json
from fastapi import APIRouter, Depends
from ..schemas import OpsImportIn
from ..services.authz import require_scopes
from ..services.outbox_worker import dispatch_once
from ..repositories import tasks_repo, commands_repo, habits_repo
from ..errors import bad_request, conflict

router = APIRouter(dependencies=[Depends(require_scopes({'admin:ops'}))])


@router.post('/integrations/reconcile')
def reconcile(limit: int = 100):
    return {'status': 'ok', 'repair': dispatch_once(limit)}


@router.get('/export')
def export_data():
    payload = {
        'manifest': {'schema_version': 'v1', 'app_version': '1.0.0-rc1'},
        'tasks': tasks_repo.list_tasks(),
        'commands': commands_repo.history(limit=500),
        'habits': habits_repo.get_logs(limit=500),
    }
    blob = json.dumps(payload, sort_keys=True)
    checksum = hashlib.sha256(blob.encode('utf-8')).hexdigest()
    return {'checksum': checksum, 'payload': payload}


@router.post('/import')
def import_data(payload: OpsImportIn):
    calc = hashlib.sha256(payload.package.encode('utf-8')).hexdigest()
    if calc != payload.checksum:
        raise bad_request('checksum_mismatch', 'Checksum mismatch')
    parsed = json.loads(payload.package)
    if parsed.get('manifest', {}).get('schema_version') != 'v1':
        raise conflict('schema_version_mismatch', 'Schema version mismatch')

    tasks = parsed.get('tasks', [])
    commands = parsed.get('commands', [])
    habits = parsed.get('habits', [])

    if not payload.dry_run:
        for t in tasks:
            title = (t.get('title') or '').strip()
            if not title:
                continue
            tasks_repo.create_task({
                'title': title,
                'due_at': t.get('due_at'),
                'priority': int(t.get('priority', 2)),
                'recurrence_rule': t.get('recurrence_rule'),
                'recurrence_parent_id': t.get('recurrence_parent_id'),
            })
        for c in commands:
            txt = c.get('command_text') or c.get('text') or ''
            intent = c.get('parsed_intent') or c.get('intent') or 'imported'
            if txt:
                commands_repo.add_log(txt, intent, status=c.get('status', 'ok'), error=c.get('error_json') or c.get('error'))
        for h in habits:
            name = (h.get('habit_name') or '').strip()
            if name:
                habits_repo.log_checkin(name, bool(h.get('done', True)))

    summary = {
        'tasks': len(tasks),
        'commands': len(commands),
        'habits': len(habits),
        'dry_run': payload.dry_run,
        'applied': not payload.dry_run,
    }
    return {'status': 'ok', 'summary': summary, 'conflicts': []}


# Endpoints map:
# Owner: ops-domain
# POST /ops/integrations/reconcile?limit=100
# GET /ops/export
# POST /ops/import  (body: {package, checksum, dry_run})
