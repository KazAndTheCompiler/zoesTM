CREATE TABLE IF NOT EXISTS command_logs (
  id TEXT PRIMARY KEY,
  command_text TEXT NOT NULL,
  intent TEXT NOT NULL,
  status TEXT NOT NULL,
  error TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habit_logs (
  id TEXT PRIMARY KEY,
  habit_name TEXT NOT NULL,
  done INTEGER NOT NULL,
  logged_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alarm_queue (
  id TEXT PRIMARY KEY,
  alarm_id TEXT NOT NULL,
  track_ref TEXT NOT NULL,
  position INTEGER NOT NULL,
  predownload_status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(alarm_id) REFERENCES alarms(id)
);
