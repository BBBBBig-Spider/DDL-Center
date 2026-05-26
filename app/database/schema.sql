CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    teacher TEXT NOT NULL DEFAULT '',
    semester TEXT NOT NULL DEFAULT '',
    external_id TEXT,
    color TEXT NOT NULL DEFAULT '#4F81BD',
    source TEXT NOT NULL DEFAULT 'manual',
    raw_payload TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    course_id INTEGER,
    related_exam_id INTEGER,
    description TEXT NOT NULL DEFAULT '',
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
    raw_payload TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL,
    FOREIGN KEY (related_exam_id) REFERENCES exams(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS schedule_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    title TEXT NOT NULL,
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    slot_type TEXT NOT NULL DEFAULT 'lecture',
    start_week INTEGER NOT NULL DEFAULT 1,
    end_week INTEGER NOT NULL DEFAULT 16,
    week_type TEXT NOT NULL DEFAULT 'all',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    seat TEXT NOT NULL DEFAULT '',
    exam_type TEXT NOT NULL DEFAULT 'other',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    raw_payload TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    target_type TEXT NOT NULL DEFAULT 'task',
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    local_type TEXT NOT NULL,
    local_id INTEGER NOT NULL,
    raw_hash TEXT NOT NULL DEFAULT '',
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
CREATE INDEX IF NOT EXISTS idx_courses_external_id ON courses(external_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read);
CREATE INDEX IF NOT EXISTS idx_sync_records_external ON sync_records(source_type, external_id);
