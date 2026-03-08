import uuid
from ..db import tx, conn


def create(level: str, title: str, body: str = '', scope: str = 'global'):
    nid = str(uuid.uuid4())
    with tx() as c:
        c.execute(
            "INSERT INTO notifications(id,level,title,body,scope,is_read,archived) VALUES(?,?,?,?,?,0,0)",
            (nid, level, title, body, scope),
        )
    return get(nid)


def get(notification_id: str):
    with conn() as c:
        row = c.execute("SELECT * FROM notifications WHERE id=?", (notification_id,)).fetchone()
    return dict(row) if row else None


def list_items(scope: str | None = None):
    q = "SELECT * FROM notifications WHERE archived=0"
    args = []
    if scope:
        q += " AND scope=?"
        args.append(scope)
    q += " ORDER BY created_at DESC"
    with conn() as c:
        rows = c.execute(q, tuple(args)).fetchall()
    return [dict(r) for r in rows]


def mark_read(notification_id: str):
    with tx() as c:
        c.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notification_id,))
    return get(notification_id)


def archive(notification_id: str):
    with tx() as c:
        c.execute("UPDATE notifications SET archived=1 WHERE id=?", (notification_id,))
    return get(notification_id)


def clear_scope(scope: str):
    with tx() as c:
        c.execute("UPDATE notifications SET archived=1 WHERE scope=?", (scope,))
    return {'scope': scope, 'status': 'cleared'}


def unread_count():
    with conn() as c:
        row = c.execute("SELECT COUNT(*) as n FROM notifications WHERE is_read=0 AND archived=0").fetchone()
    return {'unread': row['n']}
