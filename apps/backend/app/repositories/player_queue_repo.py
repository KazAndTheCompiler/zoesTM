import uuid
from ..db import tx, conn


def _ensure_table():
    with tx() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS player_queue (
              id TEXT PRIMARY KEY,
              position INTEGER NOT NULL,
              track_ref TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def replace(items: list[str], max_items: int = 20):
    _ensure_table()
    kept = items[:max_items]
    with tx() as c:
        c.execute("DELETE FROM player_queue")
        for i, t in enumerate(kept):
            c.execute(
                "INSERT INTO player_queue(id, position, track_ref) VALUES(?,?,?)",
                (str(uuid.uuid4()), i, t),
            )
    return list_items()


def list_items():
    _ensure_table()
    with conn() as c:
        rows = c.execute("SELECT track_ref FROM player_queue ORDER BY position ASC").fetchall()
    return [r['track_ref'] for r in rows]


def pop_next():
    _ensure_table()
    with tx() as c:
        row = c.execute("SELECT id, track_ref FROM player_queue ORDER BY position ASC LIMIT 1").fetchone()
        if not row:
            return None
        c.execute("DELETE FROM player_queue WHERE id=?", (row['id'],))
        # re-pack positions
        rows = c.execute("SELECT id FROM player_queue ORDER BY position ASC").fetchall()
        for i, r in enumerate(rows):
            c.execute("UPDATE player_queue SET position=? WHERE id=?", (i, r['id']))
        return row['track_ref']
