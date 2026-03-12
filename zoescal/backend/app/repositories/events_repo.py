import uuid
from datetime import datetime, UTC
from ..db import tx, conn


def _new_id() -> str:
    """Generate a stable prefixed internal ID (ADR 0002)."""
    return f"evt_{uuid.uuid4().hex}"


def _row_to_event(row) -> dict:
    d = dict(row)
    return d


def create_event(payload: dict) -> dict:
    """Create a locally-owned calendar event."""
    eid = _new_id()
    now = datetime.now(UTC).isoformat()
    with tx() as c:
        c.execute(
            """INSERT INTO events(
                id, title, description, start_at, end_at, all_day,
                source_type, source_instance_id, source_external_id, source_origin_app,
                editability_class, read_only, sync_status, last_synced_at,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid,
                payload.get("title", ""),
                payload.get("description", ""),
                payload.get("start_at"),
                payload.get("end_at"),
                int(payload.get("all_day", False)),
                payload.get("source_type", "zoescal"),
                payload.get("source_instance_id", "local"),
                payload.get("source_external_id"),  # None for local events
                payload.get("source_origin_app", "zoescal"),
                payload.get("editability_class", "local"),
                int(payload.get("read_only", False)),
                payload.get("sync_status", "local_only"),
                payload.get("last_synced_at"),
                now,
                now,
            ),
        )
    return get_event(eid)


def get_event(event_id: str) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return _row_to_event(row) if row else None


def list_events(start: str | None = None, end: str | None = None) -> list[dict]:
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if start:
        query += " AND datetime(start_at) >= datetime(?)"
        params.append(start)
    if end:
        query += " AND datetime(start_at) <= datetime(?)"
        params.append(end)
    query += " ORDER BY datetime(start_at) ASC"
    with conn() as c:
        rows = c.execute(query, params).fetchall()
    return [_row_to_event(r) for r in rows]


def update_event(event_id: str, payload: dict) -> dict | None:
    """Update a locally-owned event. Provider-owned fields are protected."""
    existing = get_event(event_id)
    if not existing:
        return None
    # ADR 0005: block edits to provider-owned read-only events on provider fields
    if existing.get("read_only") and existing.get("source_type") not in (
        "zoescal",
        "zoestm",
    ):
        # Only allow overlay fields
        allowed = {"local_note", "local_color", "linked_task_id"}
        payload = {k: v for k, v in payload.items() if k in allowed}

    now = datetime.now(UTC).isoformat()
    fields = {
        "title": payload.get("title", existing["title"]),
        "description": payload.get("description", existing["description"]),
        "start_at": payload.get("start_at", existing["start_at"]),
        "end_at": payload.get("end_at", existing["end_at"]),
        "all_day": int(payload.get("all_day", existing["all_day"])),
        "local_note": payload.get("local_note", existing.get("local_note")),
        "local_color": payload.get("local_color", existing.get("local_color")),
        "linked_task_id": payload.get("linked_task_id", existing.get("linked_task_id")),
        "updated_at": now,
    }
    with tx() as c:
        c.execute(
            """UPDATE events SET
                title=?, description=?, start_at=?, end_at=?, all_day=?,
                local_note=?, local_color=?, linked_task_id=?, updated_at=?
            WHERE id=?""",
            (*fields.values(), event_id),
        )
    return get_event(event_id)


def delete_event(event_id: str) -> bool:
    """Soft-delete by marking tombstone (ADR 0002 - IDs never recycled)."""
    now = datetime.now(UTC).isoformat()
    with tx() as c:
        c.execute(
            "UPDATE events SET deleted=1, deleted_at=? WHERE id=?",
            (now, event_id),
        )
        return c.rowcount > 0


def upsert_external_event(payload: dict) -> dict:
    """
    Import or update an event from an external provider (ADR 0002, ADR 0005).
    Deduplicates by source_type + source_instance_id + source_external_id.
    """
    source_type = payload["source_type"]
    source_instance_id = payload["source_instance_id"]
    source_external_id = payload["source_external_id"]

    with conn() as c:
        existing = c.execute(
            """SELECT * FROM events
               WHERE source_type=? AND source_instance_id=? AND source_external_id=?
               AND deleted=0""",
            (source_type, source_instance_id, source_external_id),
        ).fetchone()

    if existing:
        # Update provider-owned fields only
        event_id = dict(existing)["id"]
        now = datetime.now(UTC).isoformat()
        with tx() as c:
            c.execute(
                """UPDATE events SET
                    title=?, description=?, start_at=?, end_at=?, all_day=?,
                    sync_status=?, editability_class=?, read_only=?,
                    last_synced_at=?, updated_at=?
                WHERE id=?""",
                (
                    payload.get("title", ""),
                    payload.get("description", ""),
                    payload.get("start_at"),
                    payload.get("end_at"),
                    int(payload.get("all_day", False)),
                    payload.get("sync_status", "synced"),
                    payload.get("editability_class", "readonly_mirror"),
                    int(payload.get("read_only", True)),
                    now,
                    now,
                    event_id,
                ),
            )
        return get_event(event_id)
    else:
        # New external event — assign fresh internal ID
        return create_event(
            {
                **payload,
                "editability_class": "readonly_mirror",
                "read_only": True,
                "sync_status": payload.get("sync_status", "synced"),
                "last_synced_at": datetime.now(UTC).isoformat(),
            }
        )
