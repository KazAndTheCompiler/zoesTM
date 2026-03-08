CREATE TABLE IF NOT EXISTS alarm_meta (
  alarm_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'alarm',
  title TEXT,
  tts_text TEXT,
  youtube_link TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(alarm_id) REFERENCES alarms(id)
);
