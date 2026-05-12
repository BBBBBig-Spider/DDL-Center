import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="app.db"):
        self.db_path = db_path

    def get_connection(self):
        """获取数据库连接，并开启外键支持"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;") # 你的表里有 FOREIGN KEY，必须手动开启
        conn.row_factory = sqlite3.Row            # 让查询结果可以像字典一样按列名访问
        return conn

    def init_database(self, schema_path="app/database/schema.sql"):
        """读取 schema.sql 并初始化数据库表"""
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"找不到 SQL 文件: {schema_path}")
            
        with self.get_connection() as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_script = f.read()
            conn.executescript(schema_script)
            print("✅ 数据库表初始化成功！")

# 测试运行块
if __name__ == "__main__":
    db = DatabaseManager()
    db.init_database()