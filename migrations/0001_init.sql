CREATE TABLE IF NOT EXISTS update_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL,
  date TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  row_count INTEGER NOT NULL DEFAULT 0,
  message TEXT,
  raw_snapshot_key TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(idempotency_key)
);

CREATE TABLE IF NOT EXISTS ranking_rows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  brand TEXT NOT NULL,
  country TEXT NOT NULL,
  status TEXT NOT NULL,
  data_origin TEXT NOT NULL,
  revenue_rank_tools INTEGER,
  source TEXT,
  tooltip_date TEXT,
  status_detail TEXT,
  source_url TEXT,
  crawl_time TEXT,
  raw_tooltip_text TEXT,
  screenshot_path TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(date, brand, country)
);

CREATE INDEX IF NOT EXISTS idx_update_runs_date_created_at
  ON update_runs(date, created_at);

CREATE INDEX IF NOT EXISTS idx_update_runs_status
  ON update_runs(status);

CREATE INDEX IF NOT EXISTS idx_update_runs_updated_at
  ON update_runs(updated_at);

CREATE INDEX IF NOT EXISTS idx_ranking_rows_date
  ON ranking_rows(date);

CREATE INDEX IF NOT EXISTS idx_ranking_rows_brand_country
  ON ranking_rows(brand, country);
