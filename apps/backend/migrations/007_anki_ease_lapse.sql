-- Add SM-2 algorithm support: ease factor and lapse tracking
ALTER TABLE cards ADD COLUMN ease_factor REAL NOT NULL DEFAULT 2.5;
ALTER TABLE cards ADD COLUMN lapse_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE cards ADD COLUMN last_interval_days INTEGER;
ALTER TABLE cards ADD COLUMN reviews_done INTEGER NOT NULL DEFAULT 0;
