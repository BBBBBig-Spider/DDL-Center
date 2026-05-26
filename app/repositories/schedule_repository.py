"""app/repositories/schedule_repository.py"""
from __future__ import annotations

from datetime import time
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.schedule_slot import ScheduleSlot


class ScheduleRepository:
    """schedule_slots 表的增删改查。
    提供 add / list_by_weekday / list_by_week / list_all / update / delete / find_by_external_id。
    """

    VALID_SLOT_TYPES = {"lecture", "lab", "tutorial", "custom", "free"}
    VALID_WEEK_TYPES = {"all", "odd", "even"}
    VALID_SOURCES = {"manual", "sync"}
    VALID_WEEKDAYS = set(range(1, 8))  # 1=Monday ... 7=Sunday

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_slot(self, slot: ScheduleSlot, *, require_id: bool = False) -> None:
        if not isinstance(slot, ScheduleSlot):
            raise TypeError("slot must be a ScheduleSlot")

        if require_id and slot.id is None:
            raise ValueError("slot.id is required")

        if slot.id is not None and not self._is_int(slot.id):
            raise TypeError("slot.id must be int or None")

        if not isinstance(slot.title, str) or not slot.title.strip():
            raise ValueError("slot.title cannot be empty")

        if slot.course_id is not None and not self._is_int(slot.course_id):
            raise TypeError("slot.course_id must be int or None")

        if not self._is_int(slot.weekday):
            raise TypeError("slot.weekday must be int")

        if slot.weekday not in self.VALID_WEEKDAYS:
            raise ValueError("slot.weekday must be in 1..7")

        if not isinstance(slot.start_time, time):
            raise TypeError("slot.start_time must be datetime.time")

        if not isinstance(slot.end_time, time):
            raise TypeError("slot.end_time must be datetime.time")

        if slot.end_time <= slot.start_time:
            raise ValueError("slot.end_time must be after slot.start_time")

        if not isinstance(slot.location, str):
            raise TypeError("slot.location must be str")

        if not isinstance(slot.slot_type, str):
            raise TypeError("slot.slot_type must be str")

        if slot.slot_type not in self.VALID_SLOT_TYPES:
            raise ValueError(
                f"slot.slot_type must be one of: {', '.join(sorted(self.VALID_SLOT_TYPES))}"
            )

        if not self._is_int(slot.start_week):
            raise TypeError("slot.start_week must be int")

        if not self._is_int(slot.end_week):
            raise TypeError("slot.end_week must be int")

        if slot.start_week < 1:
            raise ValueError("slot.start_week must be >= 1")

        if slot.end_week < slot.start_week:
            raise ValueError("slot.end_week must be >= slot.start_week")

        if not isinstance(slot.week_type, str):
            raise TypeError("slot.week_type must be str")

        if slot.week_type not in self.VALID_WEEK_TYPES:
            raise ValueError(
                f"slot.week_type must be one of: {', '.join(sorted(self.VALID_WEEK_TYPES))}"
            )

        if not isinstance(slot.source, str):
            raise TypeError("slot.source must be str")

        if slot.source not in self.VALID_SOURCES:
            raise ValueError(
                f"slot.source must be one of: {', '.join(sorted(self.VALID_SOURCES))}"
            )

        if slot.external_id is not None and not isinstance(slot.external_id, str):
            raise TypeError("slot.external_id must be str or None")

    def _validate_weekday(self, weekday: int) -> None:
        if not self._is_int(weekday):
            raise TypeError("weekday must be int")
        if weekday not in self.VALID_WEEKDAYS:
            raise ValueError("weekday must be in 1..7")

    def _validate_week(self, week: int) -> None:
        if not self._is_int(week):
            raise TypeError("week must be int")
        if week < 1:
            raise ValueError("week must be >= 1")

    def _row_to_slot(self, row) -> ScheduleSlot:
        return ScheduleSlot(
            id=row["id"],
            course_id=row["course_id"],
            title=row["title"],
            weekday=row["weekday"],
            start_time=time.fromisoformat(row["start_time"]),
            end_time=time.fromisoformat(row["end_time"]),
            location=row["location"],
            slot_type=row["slot_type"],
            start_week=row["start_week"],
            end_week=row["end_week"],
            week_type=row["week_type"],
            source=row["source"],
            external_id=row["external_id"],
        )

    # ─── 增 ────────────────────────────────────────────────────

    def add(self, slot: ScheduleSlot) -> int:
        """插入一条课表时段，返回新记录的 id，并把 id 回写到入参对象。"""
        self._validate_slot(slot)
        if slot.id is not None:
            raise ValueError("slot.id must be None for add(); use update() instead")
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO schedule_slots (
                    course_id,
                    title,
                    weekday,
                    start_time,
                    end_time,
                    location,
                    slot_type,
                    start_week,
                    end_week,
                    week_type,
                    source,
                    external_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slot.course_id,
                    slot.title,
                    slot.weekday,
                    slot.start_time.isoformat(),
                    slot.end_time.isoformat(),
                    slot.location,
                    slot.slot_type,
                    slot.start_week,
                    slot.end_week,
                    slot.week_type,
                    slot.source,
                    slot.external_id,
                ),
            )

        slot.id = cursor.lastrowid
        return cursor.lastrowid

    # ─── 查全部 ────────────────────────────────────────────────

    def list_all(self) -> List[ScheduleSlot]:
        """返回所有时段，按 weekday、start_time 排序。"""
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM schedule_slots
            ORDER BY weekday ASC, start_time ASC
            """
        )
        return [self._row_to_slot(row) for row in cursor.fetchall()]

    # ─── 按 weekday 查 ────────────────────────────────────────

    def list_by_weekday(self, weekday: int) -> List[ScheduleSlot]:
        """返回指定星期几的所有时段，按 start_time 排序。"""
        self._validate_weekday(weekday)
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM schedule_slots
            WHERE weekday = ?
            ORDER BY start_time ASC
            """,
            (weekday,),
        )
        return [self._row_to_slot(row) for row in cursor.fetchall()]

    # ─── 按 week 查 ───────────────────────────────────────────

    def list_by_week(self, week: int, weekday: int | None = None) -> List[ScheduleSlot]:
        """返回在指定周次出现的所有时段（处理 start_week/end_week 范围 + 单双周）。
        传入 weekday 时进一步限定到某一天。"""
        self._validate_week(week)
        if weekday is not None:
            self._validate_weekday(weekday)

        parity = "odd" if week % 2 == 1 else "even"
        conn = self.db_manager.get_connection()

        if weekday is None:
            cursor = conn.execute(
                """
                SELECT *
                FROM schedule_slots
                WHERE start_week <= ?
                  AND end_week >= ?
                  AND (week_type = 'all' OR week_type = ?)
                ORDER BY weekday ASC, start_time ASC
                """,
                (week, week, parity),
            )
        else:
            cursor = conn.execute(
                """
                SELECT *
                FROM schedule_slots
                WHERE start_week <= ?
                  AND end_week >= ?
                  AND (week_type = 'all' OR week_type = ?)
                  AND weekday = ?
                ORDER BY start_time ASC
                """,
                (week, week, parity, weekday),
            )
        return [self._row_to_slot(row) for row in cursor.fetchall()]

    # ─── 改 ────────────────────────────────────────────────────

    def update(self, slot: ScheduleSlot) -> bool:
        """根据 slot.id 更新整条记录。返回 True 表示更新成功。"""
        self._validate_slot(slot, require_id=True)
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE schedule_slots
                SET
                    course_id = ?,
                    title = ?,
                    weekday = ?,
                    start_time = ?,
                    end_time = ?,
                    location = ?,
                    slot_type = ?,
                    start_week = ?,
                    end_week = ?,
                    week_type = ?,
                    source = ?,
                    external_id = ?
                WHERE id = ?
                """,
                (
                    slot.course_id,
                    slot.title,
                    slot.weekday,
                    slot.start_time.isoformat(),
                    slot.end_time.isoformat(),
                    slot.location,
                    slot.slot_type,
                    slot.start_week,
                    slot.end_week,
                    slot.week_type,
                    slot.source,
                    slot.external_id,
                    slot.id,
                ),
            )

        return cursor.rowcount > 0

    # ─── 删 ────────────────────────────────────────────────────

    def delete(self, slot_id: int) -> bool:
        """根据 id 删除时段。返回 True 表示删除成功。"""
        if not self._is_int(slot_id):
            raise TypeError("slot_id must be int")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM schedule_slots
                WHERE id = ?
                """,
                (slot_id,),
            )

        return cursor.rowcount > 0

    # ─── 按 external_id 查 ────────────────────────────────────

    def find_by_external_id(self, external_id: str) -> Optional[ScheduleSlot]:
        """根据教学网时段 ID 查询，找不到返回 None。同步流程使用。
        只匹配 source='sync' 的记录，避免 manual 行误用 external_id 命中。"""
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM schedule_slots
            WHERE external_id = ? AND source = 'sync'
            """,
            (external_id,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_slot(row)
