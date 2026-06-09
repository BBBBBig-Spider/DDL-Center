import sqlite3
from datetime import datetime
from pathlib import Path
from app.config import DB_PATH

class DatabaseManager:
    def __init__(self, db_path: str | Path | None = None):
        """
        初始化数据库管理器。
        Args:
            db_path: SQLite 数据库文件路径。
                     如果不传，则默认存储在项目根目录的 data/ddl_center.db
        """
        # 动态获取当前文件所在目录，确保在任何路径下运行都不会丢失相对位置
        self.base_dir: Path = Path(__file__).resolve().parent
        self.project_root: Path = self.base_dir.parent.parent

        if db_path is None:
            self.db_path: Path = Path(DB_PATH)
        else:
            self.db_path = Path(db_path)

        self.schema_path: Path = self.base_dir / "schema.sql"
        
        # 内部维护一个连接实例，避免重复创建连接
        self._connection: sqlite3.Connection | None = None

        # 确保数据存放的父目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接（使用单例模式复用连接）。
        """
        if self._connection is None:
            # check_same_thread=False 允许 QThread 中的 SyncManager 复用同一连接；
            # 调用方需自行保证不会并发写（GUI 主线程与同步线程串行调用即可）
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row

            # 必须显式开启外键约束，这是 SQLite 的最佳实践
            self._connection.execute("PRAGMA foreign_keys = ON")

        return self._connection

    def initialize_database(self) -> None:
        """
        初始化数据库：读取并执行 schema.sql，创建表结构。
        """
        if not self.schema_path.exists():
            raise FileNotFoundError(f"schema.sql not found at: {self.schema_path}")

        schema_sql: str = self.schema_path.read_text(encoding="utf-8")

        conn: sqlite3.Connection = self.get_connection()

        with conn:
            conn.executescript(schema_sql)

        self._run_migrations(conn)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Apply incremental schema migrations that cannot be expressed as CREATE IF NOT EXISTS."""
        cursor = conn.execute("PRAGMA table_info(tasks)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "is_hidden" not in existing_cols:
            with conn:
                conn.execute(
                    "ALTER TABLE tasks ADD COLUMN is_hidden INTEGER NOT NULL DEFAULT 0"
                )
        cursor = conn.execute("PRAGMA table_info(exams)")
        exam_cols = {row[1] for row in cursor.fetchall()}
        if "seat" not in exam_cols:
            with conn:
                conn.execute("ALTER TABLE exams ADD COLUMN seat TEXT NOT NULL DEFAULT ''")
        self._relax_exams_course_id_not_null(conn)
        self._fix_wrong_year_due_times(conn)

    @staticmethod
    def _relax_exams_course_id_not_null(conn: sqlite3.Connection) -> None:
        """Drop the legacy NOT NULL constraint on exams.course_id.

        Older databases were created when course_id was required; the current
        schema declares it nullable so manual / AI-created exams without a
        linked course can be stored. SQLite cannot ALTER a column's NOT NULL,
        so this rebuilds the table when the legacy constraint is detected.
        """
        rows = conn.execute("PRAGMA table_info(exams)").fetchall()
        course_id_row = next((r for r in rows if r[1] == "course_id"), None)
        if course_id_row is None:
            return
        # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
        if not course_id_row[3]:
            return  # already nullable

        with conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            try:
                conn.execute(
                    """
                    CREATE TABLE exams_new (
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
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO exams_new (
                        id, course_id, name, start_time, end_time, location,
                        seat, exam_type, source, external_id, raw_payload
                    )
                    SELECT
                        id, course_id, name, start_time, end_time, location,
                        seat, exam_type, source, external_id, raw_payload
                    FROM exams
                    """
                )
                conn.execute("DROP TABLE exams")
                conn.execute("ALTER TABLE exams_new RENAME TO exams")
            finally:
                conn.execute("PRAGMA foreign_keys = ON")

    @staticmethod
    def _fix_wrong_year_due_times(conn: sqlite3.Connection) -> None:
        """Correct sync tasks whose due_time was stored with an off-by-one year.

        The DDL parser used to bump any no-explicit-year date that appeared >30
        days in the past by +1 year unconditionally, which turned a genuine
        overdue date (e.g. 2026-03-16) into a far-future date (2027-03-16).
        This migration finds such rows and rolls the year back by exactly 1.

        We only touch tasks where:
          - year stored == current year + 1  (the classic off-by-one bump)
          - rolling back by 1 year gives a date in the past  (genuinely overdue)
        This leaves legitimate near-future tasks (year == current year) untouched.
        """
        now = datetime.now()
        wrong_year = now.year + 1
        rows = conn.execute(
            "SELECT id, due_time FROM tasks WHERE source = 'sync' AND is_hidden = 0"
        ).fetchall()
        to_fix: list[tuple[str, int]] = []
        for row in rows:
            raw_dt = row["due_time"]
            if not raw_dt:
                continue
            try:
                dt = datetime.fromisoformat(raw_dt)
            except ValueError:
                continue
            # The codebase stores naive datetimes by convention; if a tz-aware
            # value ever sneaks in, drop the tz before comparing so the whole
            # migration doesn't abort with TypeError.
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            if dt.year != wrong_year:
                continue  # not the classic bump pattern
            try:
                corrected = dt.replace(year=dt.year - 1)
            except ValueError:
                continue
            if corrected < now:
                # Rolling back confirms this date is genuinely in the past
                to_fix.append((corrected.isoformat(sep=" "), row["id"]))
        if to_fix:
            with conn:
                conn.executemany(
                    "UPDATE tasks SET due_time = ? WHERE id = ?", to_fix
                )

    def close(self) -> None:
        """
        关闭数据库连接并释放资源。
        """
        if self._connection is not None:
            self._connection.close()
            self._connection = None
