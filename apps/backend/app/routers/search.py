from fastapi import APIRouter
from ..repositories import tasks_repo, commands_repo, habits_repo, journal_repo

router = APIRouter()


@router.get('')
def unified_search(q: str = '', types: str = 'tasks,commands,habits,journal', limit: int = 20):
    limit = max(1, min(limit, 100))
    if not q.strip():
        return {'items': [], 'results': [], 'total': 0}
    enabled = {t.strip() for t in types.split(',') if t.strip()}
    items = []
    ql = q.lower()
    if 'tasks' in enabled:
        for t in tasks_repo.list_tasks():
            if ql in (t.get('title') or '').lower():
                items.append({'type': 'task', 'id': t['id'], 'title': t['title'], 'deeplink': f"/tasks/{t['id']}"})
    if 'commands' in enabled:
        for c in commands_repo.history(limit=50):
            if ql in (c.get('text') or '').lower():
                items.append({'type': 'command', 'id': c.get('created_at', ''), 'title': c['text'], 'deeplink': '/commands/history'})
    if 'habits' in enabled:
        for h in habits_repo.get_logs(limit=50):
            n = h.get('habit_name') or ''
            if ql in n.lower():
                items.append({'type': 'habit', 'id': h.get('id', ''), 'title': n, 'deeplink': '/habits/weekly'})
    if 'journal' in enabled:
        for j in journal_repo.list_entries(limit=50):
            body = (j.get('markdown_body') or '').lower()
            emoji = (j.get('emoji') or '').lower()
            if ql in body or (emoji and ql in emoji):
                title = j.get('date') or 'journal entry'
                items.append({'type': 'journal', 'id': j['id'], 'title': title, 'deeplink': f"/journal/{j['id']}"})
    items = sorted(items, key=lambda x: (0 if x['title'].lower().startswith(ql) else 1, x['title']))
    sliced = items[:limit]
    return {'items': sliced, 'results': sliced, 'total': len(items)}


# Endpoints map:
# Owner: search-domain
# GET /search?q=...&types=tasks,commands,habits,journal&limit=20
