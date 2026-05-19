"""app/repositories/alert_repository.py"""
from __future__ import annotations

from datetime import datetime
from typing import List

from app.database.database_manager import DatabaseManager
from app.models.alert import Alert


class AlertRepository:
    """alerts 表的增删改查。提供 add / list_unread / list_all / mark_read / mark_all_read / delete_old / delete。"""

    VALID_LEVELS = {"info", "warning", "urgent", "overdue"}
    VALID_KINDS = {"deadline", "overload", "progress"}
    VALID_TARGET_TYPES = {"task", "day", "global"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_alert(self, alert: Alert, *, require_id: bool = False) -> None:
        if not isinstance(alert, Alert):
            raise TypeError("alert must be an Alert")

        if require_id and alert.id is None:
            raise ValueError("alert.id is required")

        if alert.id is not None and not self._is_int(alert.id):
            raise TypeError("alert.id must be int or None")

        if alert.task_id is not None and not self._is_int(alert.task_id):
            raise TypeError("alert.task_id must be int or None")

        if not isinstance(alert.level, str):
            raise TypeError("alert.level must be str")

        if alert.level not in self.VALID_LEVELS:
            raise ValueError(
                f"alert.level must be one of: {', '.join(sorted(self.VALID_LEVELS))}"
            )

        if not isinstance(alert.kind, str):
            raise TypeError("alert.kind must be str")

        if alert.kind not in self.VALID_KINDS:
            raise ValueError(
                f"alert.kind must be one of: {', '.join(sorted(self.VALID_KINDS))}"
            )

        if not isinstance(alert.message, str) or not alert.message.strip():
            raise ValueError("alert.message cannot be empty")

        if not isinstance(alert.created_at, datetime):
            raise TypeError("alert.created_at must be datetime")

        if not isinstance(alert.is_read, bool):
            raise TypeError("alert.is_read must be bool")

        if not isinstance(alert.target_type, str):
            raise TypeError("alert.target_type must be str")

        if alert.target_type not in self.VALID_TARGET_TYPES:
            raise ValueError(
                f"alert.target_type must be one of: {', '.join(sorted(self.VALID_TARGET_TYPES))}"
            )

        if alert.target_type == "task" and alert.task_id is None:
            raise ValueError("alert.task_id is required when target_type='task'")

        if alert.target_type != "task" and alert.task_id is not None:
            raise ValueError(
                "alert.task_id must be None when target_type is 'day' or 'global'"
            )

    def _row_to_alert(self, row) -> Alert:
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
        self._validate_alert(alert)
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
        if not self._is_int(alert_id):
            raise TypeError("alert_id must be int")

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
        if not isinstance(before, datetime):
            raise TypeError("before must be datetime")

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
        if not self._is_int(alert_id):
            raise TypeError("alert_id must be int")

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
