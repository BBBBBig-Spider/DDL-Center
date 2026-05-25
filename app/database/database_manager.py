import sqlite3
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

        # 使用 Pathlib 的 read_text() 更现代、更简洁，自动处理文件打开与关闭
        schema_sql: str = self.schema_path.read_text(encoding="utf-8")

        conn: sqlite3.Connection = self.get_connection()
        
        # 使用上下文管理器自动处理 commit 和 rollback
        with conn:
            conn.executescript(schema_sql)

    def close(self) -> None:
        """
        关闭数据库连接并释放资源。
        """
        if self._connection is not None:
            self._connection.close()
            self._connection = None
