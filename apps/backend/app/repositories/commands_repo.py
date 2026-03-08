import uuid
from ..db import tx, conn


def add_log(command_text: str, intent: str, status: str = "ok", error: str | None = None):
    with tx() as c:
        c.execute(
            "INSERT INTO command_logs(id,command_text,intent,status,error) VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), command_text, intent, status, error),
        )


def history(limit: int = 100):
    with conn() as c:
        rows = c.execute(
            "SELECT command_text as text,intent,status,error,created_at FROM command_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
