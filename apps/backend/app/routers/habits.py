from datetime import datetime, timedelta
from fastapi import APIRouter
from ..services.habits import weekly_overview
from ..repositories import habits_repo

router = APIRouter()


def _parse_day(ts: str | None):
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
    except Exception:
        return None


def _window_pct(logs, days: int) -> float:
    cutoff = datetime.now().date() - timedelta(days=days)
    subset = [x for x in logs if (_parse_day(x.get('logged_at')) and _parse_day(x.get('logged_at')) >= cutoff)]
    total = len(subset)
    done = sum(1 for x in subset if bool(x.get('done')))
    return round((done / total) * 100, 1) if total else 0.0


@router.get('/list')
def list_habits():
    return {'habits': habits_repo.list_habits()}


@router.post('/add')
def add_habit(name: str):
    habit = habits_repo.add_habit(name)
    return habit or {'error': 'could not add habit'}


@router.delete('/{name}')
def delete_habit(name: str):
    return habits_repo.delete_habit(name)


@router.post('/checkin')
def checkin(name: str, done: bool = True):
    return habits_repo.log_checkin(name, done)


@router.get('/weekly')
def weekly():
    return weekly_overview(habits_repo.get_logs())


@router.get('/insights')
def insights():
    logs = habits_repo.get_logs(limit=1000)
    pct_7 = _window_pct(logs, 7)
    pct_14 = _window_pct(logs, 14)
    pct_30 = _window_pct(logs, 30)
    return {
        'windows': {'7d': pct_7, '14d': pct_14, '30d': pct_30},
        'segments': [{'tag': 'default', 'completion_pct': pct_30}],
        'consistency': 'high' if pct_30 >= 80 else 'medium' if pct_30 >= 50 else 'low',
    }


# Endpoints map:
# Owner: habits-domain
# POST /habits/checkin?name=...&done=true
# GET /habits/weekly
# GET /habits/insights
