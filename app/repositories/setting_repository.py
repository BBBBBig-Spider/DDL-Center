"""app/repositories/setting_repository.py"""
from __future__ import annotations

from typing import Dict, Optional

from app.database.database_manager import DatabaseManager


class SettingRepository:
    """
    user_settings 表的增删改查
    用于存放：每日 AI token 累计、上次同步时间、用户偏好等键值对
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be str")

        if not key:
            raise ValueError("key cannot be empty")

    @staticmethod
    def _validate_value(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("value must be str")

    def get(self, key: str) -> Optional[str]:
        self._validate_key(key)
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
        写入或更新设置项
        """
        self._validate_key(key)
        self._validate_value(value)

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
        """删除某个设置项"""
        self._validate_key(key)
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
