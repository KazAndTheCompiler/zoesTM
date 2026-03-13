import sqlite3
import uuid
from datetime import UTC, datetime

from ..db import conn, tx


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _row_to_entry(row):
    return dict(row) if row else None


def create_entry(payload: dict):
    entry_id = str(uuid.uuid4())
    date = payload.get('date') or _today_iso()
    markdown_body = payload.get('markdown_body', '')
    emoji = payload.get('emoji')
    try:
        with tx() as c:
            c.execute(
                "INSERT INTO journal_entries(id, date, markdown_body, emoji) VALUES(?,?,?,?)",
                (entry_id, date, markdown_body, emoji),
            )
    except sqlite3.IntegrityError as exc:
        if 'journal_entries.date' in str(exc) or 'idx_journal_date' in str(exc) or 'UNIQUE constraint failed: journal_entries.date' in str(exc):
            raise ValueError('duplicate_date') from exc
        raise
    return get_entry(entry_id)


def list_entries(limit: int | None = None, offset: int | None = None):
    query = "SELECT id, date, markdown_body, emoji, created_at, updated_at FROM journal_entries ORDER BY date DESC, created_at DESC, rowid DESC"
    params = []
    if limit is not None:
        query += ' LIMIT ?'
        params.append(limit)
    if offset is not None and limit is not None:
        query += ' OFFSET ?'
        params.append(offset)
    with conn() as c:
        rows = c.execute(query, params).fetchall()
    return [_row_to_entry(r) for r in rows]


def get_entry(entry_id: str):
    with conn() as c:
        row = c.execute(
            "SELECT id, date, markdown_body, emoji, created_at, updated_at FROM journal_entries WHERE id=?",
            (entry_id,),
        ).fetchone()
    return _row_to_entry(row)


def get_entry_by_date(date: str):
    with conn() as c:
        row = c.execute(
            "SELECT id, date, markdown_body, emoji, created_at, updated_at FROM journal_entries WHERE date=?",
            (date,),
        ).fetchone()
    return _row_to_entry(row)


def update_entry(entry_id: str, payload: dict):
    existing = get_entry(entry_id)
    if not existing:
        return None
    markdown_body = payload.get('markdown_body', existing.get('markdown_body'))
    emoji = payload['emoji'] if 'emoji' in payload else existing.get('emoji')
    with tx() as c:
        c.execute(
            "UPDATE journal_entries SET markdown_body=?, emoji=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (markdown_body, emoji, entry_id),
        )
    return get_entry(entry_id)


def delete_entry(entry_id: str):
    with tx() as c:
        cur = c.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
        return cur.rowcount > 0
