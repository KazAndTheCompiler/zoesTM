from datetime import datetime, timedelta, UTC
from fastapi import APIRouter
from ..services.eisenhower import quadrant
from ..repositories import tasks_repo

router = APIRouter()


@router.get('/kanban')
def kanban():
    return {'columns': ['inbox', 'next', 'doing', 'waiting', 'done']}


@router.get('/matrix')
def matrix(priority: int = 2, due_soon: bool = False):
    return {'quadrant': quadrant(priority, due_soon)}


@router.get('/overview')
def overview():
    return {
        'kanban': kanban(),
        'matrix': matrix_data(),
    }


@router.get('/matrix-data')
def matrix_data():
    now = datetime.now(UTC)
    soon = now + timedelta(days=2)
    out = {'do': [], 'schedule': [], 'delegate': [], 'eliminate': []}
    for task in tasks_repo.list_tasks():
        due_raw = task.get('due_at')
        due_soon = False
        if due_raw:
            try:
                due = datetime.fromisoformat(due_raw.replace('Z', '+00:00'))
                due_soon = due <= soon
            except Exception:
                due_soon = False
        q = quadrant(task.get('priority', 2), due_soon)
        out[q].append(task)
    return {'quadrants': out}


# Endpoints map:
# Owner: board-domain
# GET /boards/kanban
# GET /boards/overview
# GET /boards/matrix?priority=1&due_soon=true
# GET /boards/matrix-data
