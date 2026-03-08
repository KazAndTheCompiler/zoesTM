ALTER TABLE tasks ADD COLUMN tags TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS player_queue (
  id TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  track_ref TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_player_queue_position ON player_queue(position);
