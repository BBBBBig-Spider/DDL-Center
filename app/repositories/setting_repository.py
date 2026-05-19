"""app/repositories/setting_repository.py"""
from __future__ import annotations
from typing import Dict, Optional

class SettingRepository:
    """
    user_settings 表的增删改查。
    schema 很简单：key TEXT PRIMARY KEY, value TEXT NOT NULL
    用于存放：每日 AI token 累计、上次同步时间、用户偏好等键值对。
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get(self, key: str) -> Optional[str]:
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT value
            FROM user_settings
            WHERE key = ?
            """,
            (key,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row["value"]

    def set(self, key: str, value: str) -> None:
        """
        写入或更新设置项。
        用 INSERT ... ON CONFLICT(key) DO UPDATE 实现 upsert，
        这样调用方不需要先 check 再决定 insert/update。
        """
        conn = self.db_manager.get_connection()

        with conn:
            conn.execute(
                """
                INSERT INTO user_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def list_all(self) -> Dict[str, str]:
        """返回所有设置项，作为 dict 返回，便于调用方一次拿走所有键。"""
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT key, value
            FROM user_settings
            ORDER BY key ASC
            """
        )

        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    def delete(self, key: str) -> bool:
        """删除某个设置项。返回 True 表示找到了对应键。"""
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                DELETE FROM user_settings
                WHERE key = ?
                """,
                (key,),
            )

        return cursor.rowcount > 0
