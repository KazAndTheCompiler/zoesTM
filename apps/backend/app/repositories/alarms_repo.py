import uuid
from ..db import tx, conn



def create_alarm(at: str, muted: bool = False, kind: str = 'alarm', title: str = '', tts_text: str = '', youtube_link: str = ''):
    aid = str(uuid.uuid4())
    with tx() as c:
        c.execute("INSERT INTO alarms(id,alarm_time,muted,enabled) VALUES(?,?,?,1)", (aid, at, int(muted)))
        c.execute(
            "INSERT OR REPLACE INTO alarm_meta(alarm_id,kind,title,tts_text,youtube_link) VALUES(?,?,?,?,?)",
            (aid, kind, title, tts_text, youtube_link),
        )
    return get_alarm(aid)


def get_alarm(alarm_id: str):
    with conn() as c:
        row = c.execute(
            """
            SELECT a.id, a.alarm_time, a.muted, a.enabled, a.last_fired_at,
                   COALESCE(m.kind, 'alarm') as kind,
                   COALESCE(m.title, '') as title,
                   COALESCE(m.tts_text, '') as tts_text,
                   COALESCE(m.youtube_link, '') as youtube_link
            FROM alarms a
            LEFT JOIN alarm_meta m ON m.alarm_id = a.id
            WHERE a.id=?
            """,
            (alarm_id,),
        ).fetchone()
    return dict(row) if row else None


def list_alarms():
    with conn() as c:
        rows = c.execute(
            """
            SELECT a.id, a.alarm_time, a.muted, a.enabled, a.created_at, a.updated_at, a.last_fired_at,
                   COALESCE(m.kind, 'alarm') as kind,
                   COALESCE(m.title, '') as title,
                   COALESCE(m.tts_text, '') as tts_text,
                   COALESCE(m.youtube_link, '') as youtube_link
            FROM alarms a
            LEFT JOIN alarm_meta m ON m.alarm_id = a.id
            ORDER BY a.alarm_time ASC, a.created_at ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def set_queue(alarm_id: str, items: list[str]):
    items = items[:20]
    with tx() as c:
        c.execute("DELETE FROM alarm_queue WHERE alarm_id=?", (alarm_id,))
        for pos, item in enumerate(items):
            c.execute(
                "INSERT INTO alarm_queue(id,alarm_id,track_ref,position,predownload_status) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), alarm_id, item, pos, "pending"),
            )
    return list_queue(alarm_id)


def list_queue(alarm_id: str):
    with conn() as c:
        rows = c.execute(
            "SELECT track_ref,position,predownload_status FROM alarm_queue WHERE alarm_id=? ORDER BY position ASC",
            (alarm_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_alarm(alarm_id: str):
    with tx() as c:
        c.execute("DELETE FROM alarm_queue WHERE alarm_id=?", (alarm_id,))
        c.execute("DELETE FROM alarm_meta WHERE alarm_id=?", (alarm_id,))
        c.execute("DELETE FROM alarms WHERE id=?", (alarm_id,))


def set_last_fired(alarm_id: str):
    with tx() as c:
        c.execute("UPDATE alarms SET last_fired_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?", (alarm_id,))


def touch_alarm(alarm_id: str):
    with tx() as c:
        c.execute("UPDATE alarms SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (alarm_id,))
