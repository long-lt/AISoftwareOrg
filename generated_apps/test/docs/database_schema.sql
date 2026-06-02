CREATE TABLE IF NOT EXISTS todo_items (
  id TEXT PRIMARY KEY NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT,
  updated_at TEXT,
  completed INTEGER NOT NULL,
  due_date TEXT
);

CREATE TABLE IF NOT EXISTS dashboard_items (
  id TEXT PRIMARY KEY NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS settings_items (
  id TEXT PRIMARY KEY NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT,
  updated_at TEXT
);
