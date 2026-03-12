-- ZoesCal Migration 001: Events table
-- Follows ADR 0002 (stable IDs), ADR 0005 (external editability)

CREATE TABLE IF NOT EXISTS events (
    -- Canonical identity (ADR 0002: stable, prefixed, never recycled)
    id TEXT PRIMARY KEY,                      -- evt_<uuid_hex>

    -- Core fields
    title TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    start_at TEXT,                            -- ISO 8601 UTC
    end_at TEXT,                              -- ISO 8601 UTC
    all_day INTEGER DEFAULT 0,

    -- Source metadata (ADR 0002: external IDs stored separately)
    source_type TEXT DEFAULT 'zoescal',       -- 'zoescal' | 'zoestm' | 'google' | 'caldav'
    source_instance_id TEXT DEFAULT 'local',  -- identifies which account/install
    source_external_id TEXT,                  -- provider's own ID, never used as canonical
    source_origin_app TEXT DEFAULT 'zoescal',

    -- Editability (ADR 0005)
    editability_class TEXT DEFAULT 'local',   -- 'local' | 'readonly_mirror' | 'limited_editable'
    read_only INTEGER DEFAULT 0,
    can_edit_time INTEGER DEFAULT 1,
    can_edit_title INTEGER DEFAULT 1,
    can_edit_description INTEGER DEFAULT 1,
    can_delete INTEGER DEFAULT 1,

    -- App-owned overlays (separate from provider truth, ADR 0005)
    local_note TEXT,
    local_color TEXT,
    linked_task_id TEXT,                      -- internal ZoesTM task ID if linked

    -- Sync state (ADR 0003)
    sync_status TEXT DEFAULT 'local_only',    -- 'local_only'|'pending_sync'|'synced'|'conflict'|'error'
    last_synced_at TEXT,
    sync_conflict_reason TEXT,

    -- Soft delete (ADR 0002: tombstone, IDs never recycled)
    deleted INTEGER DEFAULT 0,
    deleted_at TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_start_at ON events(start_at);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_type, source_instance_id, source_external_id);
CREATE INDEX IF NOT EXISTS idx_events_deleted ON events(deleted);
