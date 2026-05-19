"""app/repositories/alert_repository.py"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List
from app.models.alert import Alert


class AlertRepository:
    """alerts 表的增删改查。提供 add / list_unread / mark_read / delete_old。"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def _row_to_alert(self, row) -> Alert:
        """把数据库的一行转成 Alert 对象。"""
        return Alert(
            id=row["id"],
            task_id=row["task_id"],
            level=row["level"],
            kind=row["kind"],
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_read=bool(row["is_read"]),
            target_type=row["target_type"] or "task",
        )

    def add(self, alert: Alert) -> int:
        """插入一条提醒，返回新记录的 id。"""
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO alerts (
                    task_id,
                    target_type,
                    level,
                    kind,
                    message,
                    created_at,
                    is_read
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.task_id,
                    alert.target_type,
                    alert.level,
                    alert.kind,
                    alert.message,
                    alert.created_at.isoformat(),
                    int(alert.is_read),
                ),
            )

        return cursor.lastrowid

    def list_unread(self) -> List[Alert]:
        """返回所有未读提醒，按生成时间倒序排列（最新的在前）。"""
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM alerts
            WHERE is_read = 0
            ORDER BY created_at DESC
            """
        )

        rows = cursor.fetchall()
        return [self._row_to_alert(row) for row in rows]

    def list_all(self) -> List[Alert]:
        """返回所有提醒，按生成时间倒序排列。便于 AlertPanel 调用。"""
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM alerts
            ORDER BY created_at DESC
            """
        )

        rows = cursor.fetchall()
        return [self._row_to_alert(row) for row in rows]

    def mark_read(self, alert_id: int) -> bool:
        """将某条提醒标记为已读。返回 True 表示找到了对应记录。"""
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE alerts
                SET is_read = 1
                WHERE id = ?
                """,
                (alert_id,),
            )

        return cursor.rowcount > 0

    def mark_all_read(self) -> int:
        """把全部未读提醒标记为已读，返回更新的行数。"""
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE alerts
                SET is_read = 1
                WHERE is_read = 0
                """
            )

        return cursor.rowcount

    def delete_old(self, before: datetime) -> int:
        """
        删除 created_at 在 before 之前的提醒，返回删除的行数。
        用于定期清理过期提醒，避免 alerts 表无限增长。
        """
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                DELETE FROM alerts
                WHERE created_at < ?
                """,
                (before.isoformat(),),
            )

        return cursor.rowcount

    def delete(self, alert_id: int) -> bool:
        """根据 id 删除提醒。返回 True 表示删除成功。"""
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                DELETE FROM alerts
                WHERE id = ?
                """,
                (alert_id,),
            )

        return cursor.rowcount > 0
