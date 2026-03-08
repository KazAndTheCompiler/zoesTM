import uuid
from ..db import tx, conn


def list_habits():
    with conn() as c:
        rows = c.execute("SELECT id, name, created_at FROM habits ORDER BY created_at ASC").fetchall()
    return [dict(r) for r in rows]


def add_habit(name: str):
    name = name.strip()
    hid = str(uuid.uuid4())
    with tx() as c:
        c.execute("INSERT OR IGNORE INTO habits(id, name) VALUES(?,?)", (hid, name))
    with conn() as c:
        row = c.execute("SELECT id, name, created_at FROM habits WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def delete_habit(name: str):
    with tx() as c:
        c.execute("DELETE FROM habit_logs WHERE habit_name=?", (name,))
        c.execute("DELETE FROM habits WHERE name=?", (name,))
    return {'ok': True, 'name': name}


def log_checkin(name: str, done: bool = True):
    with tx() as c:
        # Auto-create habit if it doesn't exist yet
        c.execute("INSERT OR IGNORE INTO habits(id, name) VALUES(?,?)", (str(uuid.uuid4()), name))
        c.execute(
            "INSERT INTO habit_logs(id,habit_name,done) VALUES(?,?,?)",
            (str(uuid.uuid4()), name, int(done)),
        )
    return {"ok": True}


def get_logs(limit: int = 500):
    with conn() as c:
        rows = c.execute("SELECT habit_name, done, logged_at FROM habit_logs ORDER BY logged_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
