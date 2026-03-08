CREATE TABLE IF NOT EXISTS habits (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Seed with the three hardcoded ones so existing logs don't orphan
INSERT OR IGNORE INTO habits(id, name) VALUES
  (lower(hex(randomblob(16))), 'hydration'),
  (lower(hex(randomblob(16))), 'morning-walk'),
  (lower(hex(randomblob(16))), 'reading');
