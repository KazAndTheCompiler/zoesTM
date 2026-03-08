import uuid
from datetime import datetime, timedelta, UTC
from ..db import tx, conn


def _tags_to_db(tags):
    if not tags:
        return ''
    if isinstance(tags, str):
        return tags
    return '|'.join([str(t).strip() for t in tags if str(t).strip()])


def _row_to_task(row):
    d = dict(row)
    tags_raw = d.get('tags') or ''
    d['tags'] = [x for x in str(tags_raw).split('|') if x]
    return d


def create_task(payload: dict):
    tid = str(uuid.uuid4())
    recurrence_rule = payload.get('recurrence_rule')
    recurrence_parent_id = payload.get('recurrence_parent_id')
    with tx() as c:
        c.execute(
            "INSERT INTO tasks(id,title,due_at,priority,done,recurrence_rule,recurrence_parent_id,tags) VALUES(?,?,?,?,0,?,?,?)",
            (
                tid,
                payload.get('title'),
                payload.get('due_at'),
                int(payload.get('priority', 2)),
                recurrence_rule,
                recurrence_parent_id,
                _tags_to_db(payload.get('tags', [])),
            ),
        )
    return get_task(tid)


def list_tasks(done: bool | None = None, limit: int | None = None, offset: int | None = None):
    """List tasks with optional filtering and pagination.

    Args:
        done: Filter by completion status (True for done, False for open). None returns all.
        limit: Maximum number of tasks to return.
        offset: Number of tasks to skip (for pagination).

    Returns:
        List of task dictionaries ordered by created_at DESC.
    """
    query = "SELECT id,title,due_at,priority,done,recurrence_rule,recurrence_parent_id,tags FROM tasks"
    params = []

    if done is not None:
        query += " WHERE done = ?"
        params.append(1 if done else 0)

    query += " ORDER BY created_at DESC, rowid DESC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    if offset is not None and limit is not None:
        query += " OFFSET ?"
        params.append(offset)

    with conn() as c:
        rows = c.execute(query, params).fetchall()
    return [_row_to_task(r) for r in rows]


def get_task(task_id: str):
    with conn() as c:
        row = c.execute("SELECT id,title,due_at,priority,done,recurrence_rule,recurrence_parent_id,tags FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def update_task(task_id: str, payload: dict):
    existing = get_task(task_id)
    if not existing:
        return None
    title = payload.get('title', existing.get('title'))
    due_at = payload.get('due_at', existing.get('due_at'))
    priority = int(payload.get('priority', existing.get('priority', 2)))
    tags = _tags_to_db(payload.get('tags', existing.get('tags', [])))
    with tx() as c:
        c.execute(
            "UPDATE tasks SET title=?, due_at=?, priority=?, tags=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title, due_at, priority, tags, task_id),
        )
    return get_task(task_id)


def delete_task(task_id: str):
    with tx() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return c.rowcount > 0


def complete_task(task_id: str):
    with tx() as c:
        c.execute("UPDATE tasks SET done=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (task_id,))
    return get_task(task_id)


def list_recurrence_templates():
    with conn() as c:
        rows = c.execute("SELECT * FROM tasks WHERE recurrence_rule IS NOT NULL").fetchall()
    return [dict(r) for r in rows]


def _next_due_from_template(template_due: str | None, recurrence_rule: str | None, now: datetime) -> str:
    if not template_due:
        return now.isoformat()
    try:
        base = datetime.fromisoformat(template_due.replace('Z', '+00:00'))
    except Exception:
        return now.isoformat()

    rule = (recurrence_rule or '').lower()
    step = timedelta(days=1)
    if 'week' in rule:
        step = timedelta(days=7)
    elif 'month' in rule:
        step = timedelta(days=30)

    nxt = base
    while nxt <= now:
        nxt = nxt + step
    return nxt.isoformat().replace('+00:00', 'Z')


def materialize_recurring(window_hours: int = 36):
    created = 0
    now = datetime.now(UTC)
    templates = list_recurrence_templates()
    for t in templates:
        title = t['title']
        due = _next_due_from_template(t.get('due_at'), t.get('recurrence_rule'), now)
        parent = t['id']
        with conn() as c:
            existing = c.execute(
                "SELECT COUNT(*) as n FROM tasks WHERE recurrence_parent_id=? AND due_at BETWEEN ? AND ?",
                (parent, (now - timedelta(hours=window_hours)).isoformat(), (now + timedelta(hours=window_hours)).isoformat()),
            ).fetchone()['n']
        if existing:
            continue
        create_task({
            'title': title,
            'priority': t.get('priority', 2),
            'due_at': due,
            'recurrence_parent_id': parent,
            'tags': t.get('tags', ''),
        })
        created += 1
    return {'templates': len(templates), 'created': created}
