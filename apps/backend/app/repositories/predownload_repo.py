import uuid
from ..db import tx, conn

# agreed state machine for skeleton
# queued -> downloading -> completed
# queued/downloading -> failed (on worker error)
# failed -> queued (retry)
_ACTIVE_STATES = {'queued', 'downloading', 'retry_wait'}
_TERMINAL_STATES = {'completed', 'failed'}
_PROGRESS_STATES = ['queued', 'downloading', 'completed']


def enqueue(track_ref: str):
    jid = str(uuid.uuid4())
    with tx() as c:
        count = c.execute(
            "SELECT COUNT(*) as n FROM predownload_jobs WHERE state IN ('queued','downloading','retry_wait')"
        ).fetchone()['n']
        if count >= 100:
            return {'status': 'queue_full'}
        c.execute(
            "INSERT INTO predownload_jobs(id,track_ref,state,attempts,max_attempts) VALUES(?,?, 'queued',0,5)",
            (jid, track_ref),
        )
    return get(jid)


def get(job_id: str):
    with conn() as c:
        row = c.execute("SELECT * FROM predownload_jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(limit: int = 100):
    with conn() as c:
        rows = c.execute("SELECT * FROM predownload_jobs ORDER BY created_at ASC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def retry_failed(job_id: str):
    with tx() as c:
        c.execute(
            "UPDATE predownload_jobs SET state='queued', updated_at=CURRENT_TIMESTAMP WHERE id=? AND state IN ('failed','retry_wait')",
            (job_id,),
        )
    return get(job_id)


def mark_failed(job_id: str):
    with tx() as c:
        c.execute("UPDATE predownload_jobs SET state='failed', updated_at=CURRENT_TIMESTAMP WHERE id=?", (job_id,))
    return get(job_id)


def advance_job(job_id: str):
    job = get(job_id)
    if not job:
        return None
    cur = job.get('state')
    if cur in _TERMINAL_STATES:
        return job
    if cur == 'retry_wait':
        nxt = 'queued'
    elif cur == 'queued':
        nxt = 'downloading'
    else:
        nxt = 'completed'
    with tx() as c:
        c.execute("UPDATE predownload_jobs SET state=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (nxt, job_id))
    return get(job_id)


def progression_states():
    return list(_PROGRESS_STATES)
