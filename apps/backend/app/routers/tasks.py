from fastapi import APIRouter, Query
from ..schemas import TaskIn, TaskPatch, QuickAddIn
from ..services.quick_add import parse_quick_add
from ..repositories import tasks_repo
from ..services import events
from ..errors import not_found

router = APIRouter()


@router.post('/')
def create_task(payload: TaskIn):
    task = tasks_repo.create_task(payload.model_dump())
    events.emit_event('task.created', {'task_id': task['id'], 'title': task['title']})
    return task


@router.get('/')
def list_tasks(
    done: bool | None = Query(None, description="Filter by completion status: true for done, false for open"),
    limit: int | None = Query(None, ge=1, description="Maximum number of tasks to return"),
    offset: int | None = Query(None, ge=0, description="Number of tasks to skip")
):
    return tasks_repo.list_tasks(done=done, limit=limit, offset=offset)


@router.patch('/{task_id}')
def update_task(task_id: str, payload: TaskPatch):
    out = tasks_repo.update_task(task_id, payload.model_dump(exclude_none=True))
    if out is None:
        raise not_found('task_not_found', 'Task not found', {'task_id': task_id})
    events.emit_event('task.updated', {'task_id': task_id})
    return out


@router.delete('/{task_id}')
def delete_task(task_id: str):
    ok = tasks_repo.delete_task(task_id)
    if not ok:
        raise not_found('task_not_found', 'Task not found', {'task_id': task_id})
    events.emit_event('task.deleted', {'task_id': task_id})
    return {'ok': True, 'task_id': task_id}


@router.patch('/{task_id}/complete')
def complete(task_id: str):
    out = tasks_repo.complete_task(task_id)
    if out is None:
        raise not_found('task_not_found', 'Task not found', {'task_id': task_id})
    events.emit_event('task.completed', {'task_id': task_id})
    return out


@router.post('/quick-add')
def quick_add(payload: QuickAddIn):
    parsed = parse_quick_add(payload.text)
    if payload.commit and not parsed.get('ambiguity') and parsed.get('title'):
        task = tasks_repo.create_task(
            {
                'title': parsed['title'],
                'due_at': parsed.get('due_at'),
                'priority': parsed.get('priority', 2),
                'tags': parsed.get('tags', []),
            }
        )
        events.emit_event('task.created.quick_add', {'task_id': task['id'], 'title': task['title']})
        return {'parsed': parsed, 'created': task}
    return {'parsed': parsed, 'created': None}


@router.post('/materialize-recurring')
def materialize_recurring(window_hours: int = 36):
    out = tasks_repo.materialize_recurring(window_hours)
    events.emit_event('task.recurrence.materialized', out)
    return out


# Endpoints map:
# Owner: task-domain
# POST /tasks/
# GET /tasks/
# PATCH /tasks/{task_id}
# DELETE /tasks/{task_id}
# PATCH /tasks/{task_id}/complete
# POST /tasks/quick-add  (body: {text, commit})
# POST /tasks/materialize-recurring?window_hours=36
