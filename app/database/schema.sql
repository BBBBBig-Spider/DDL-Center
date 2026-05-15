CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    teacher TEXT DEFAULT '',
    semester TEXT DEFAULT '',
    external_id TEXT,
    color TEXT DEFAULT 'Blue',
    source TEXT NOT NULL DEFAULT 'manual',
    raw_payload TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    course_id INTEGER,
    related_exam_id INTEGER,
    description TEXT DEFAULT '',
    due_time TEXT NOT NULL,
    estimated_hours REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'todo',
    priority INTEGER NOT NULL DEFAULT 2,
    source TEXT NOT NULL DEFAULT 'manual',
    user_modified INTEGER NOT NULL DEFAULT 0,
    external_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    raw_payload TEXT DEFAULT '',
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (related_exam_id) REFERENCES exams(id)
);

CREATE TABLE IF NOT EXISTS schedule_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    title TEXT NOT NULL,
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT DEFAULT '',
    slot_type TEXT NOT NULL DEFAULT 'lecture',
    start_week INTEGER NOT NULL DEFAULT 1,
    end_week INTEGER NOT NULL DEFAULT 16,
    week_type TEXT NOT NULL DEFAULT 'all',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT DEFAULT '',
    exam_type TEXT NOT NULL DEFAULT 'other',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    raw_payload TEXT DEFAULT '',
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    local_type TEXT NOT NULL,
    local_id INTEGER NOT NULL,
    raw_hash TEXT,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE (source_type, external_id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_due_time ON tasks(due_time);
CREATE INDEX IF NOT EXISTS idx_tasks_course_id ON tasks(course_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_external_id ON tasks(external_id);
CREATE INDEX IF NOT EXISTS idx_sync_records_external ON sync_records(source_type, external_id);
