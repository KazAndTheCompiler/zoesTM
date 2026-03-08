CREATE TABLE IF NOT EXISTS outbox_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT DEFAULT CURRENT_TIMESTAMP,
  last_error TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_idempotency ON outbox_events(idempotency_key);

CREATE TABLE IF NOT EXISTS webhooks (
  id TEXT PRIMARY KEY,
  target_url TEXT NOT NULL,
  secret TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_receipts (
  id TEXT PRIMARY KEY,
  webhook_id TEXT NOT NULL,
  outbox_event_id TEXT,
  signature TEXT NOT NULL,
  delivered_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(webhook_id) REFERENCES webhooks(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id TEXT PRIMARY KEY,
  connector TEXT NOT NULL,
  state TEXT NOT NULL,
  error TEXT,
  started_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);
