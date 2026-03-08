import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_default = Path(__file__).resolve().parents[1] / "data" / "zoestm.db"
_env_db = os.getenv("DB_PATH", "").strip()
DB_PATH = Path(_env_db) if _env_db else _default
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

@contextmanager
def conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=True, timeout=10.0)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = ON;')
    try:
        yield c
    finally:
        c.close()


@contextmanager
def tx():
    with conn() as c:
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def close_connection():
    """Compatibility no-op; connections are context-managed per call."""
    return None
