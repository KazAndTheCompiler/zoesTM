import os
from pathlib import Path
import sqlite3
from datetime import datetime, UTC

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.getenv("DB_PATH", str(ROOT / 'apps' / 'backend' / 'data' / 'zoestm.db')))
MIG = ROOT / 'apps' / 'backend' / 'migrations'
DB.parent.mkdir(parents=True, exist_ok=True)


def ensure_table(c: sqlite3.Connection):
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          name TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )


def applied(c: sqlite3.Connection) -> set[str]:
    rows = c.execute("SELECT name FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def _iter_statements(sql: str):
    buf = ""
    for line in sql.splitlines():
        buf += line + "\n"
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            if stmt:
                yield stmt
            buf = ""
    if buf.strip():
        yield buf.strip()


def apply_one(c: sqlite3.Connection, path: Path):
    sql = path.read_text()
    c.execute("BEGIN")
    try:
        for stmt in _iter_statements(sql):
            c.execute(stmt)
        c.execute(
            "INSERT INTO schema_migrations(name, applied_at) VALUES(?, ?)",
            (path.name, datetime.now(UTC).isoformat()),
        )
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise


with sqlite3.connect(DB) as c:
    ensure_table(c)
    done = applied(c)
    all_files = sorted(MIG.glob('*.sql'))
    pending = [p for p in all_files if p.name not in done]
    for p in pending:
        apply_one(c, p)
    c.commit()

print('migrated', DB, 'applied', len(pending), 'pending->0')
