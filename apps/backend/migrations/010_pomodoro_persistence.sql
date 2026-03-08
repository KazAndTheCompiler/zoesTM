CREATE TABLE IF NOT EXISTS focus_sessions (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT NOT NULL DEFAULT 'idle',
    mode TEXT NOT NULL DEFAULT 'focus',
    minutes INTEGER NOT NULL DEFAULT 25,
    ends_at TEXT,
    remaining_seconds INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial idle state if table is empty
INSERT OR IGNORE INTO focus_sessions (id, status, mode, minutes) VALUES (1, 'idle', 'focus', 25);
