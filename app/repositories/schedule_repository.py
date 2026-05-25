"""app/repositories/schedule_repository.py"""
from __future__ import annotations

from datetime import time
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.schedule_slot import ScheduleSlot


class ScheduleRepository:
    """schedule_slots 表的增删改查。"""

    VALID_SLOT_TYPES = {"lecture", "lab", "tutorial", "custom", "free"}
    VALID_WEEK_TYPES = {"all", "odd", "even"}
    VALID_SOURCES = {"manual", "sync"}

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

        if slot.course_id is not None and not self._is_int(slot.course_id):
            raise TypeError("slot.course_id must be int or None")

        if not isinstance(slot.title, str) or not slot.title.strip():
            raise ValueError("slot.title cannot be empty")

        if not self._is_int(slot.weekday):
            raise TypeError("slot.weekday must be int")

        if slot.weekday < 1 or slot.weekday > 7:
            raise ValueError("slot.weekday must be in 1..7")

        if not isinstance(slot.start_time, time):
            raise TypeError("slot.start_time must be time")

        if not isinstance(slot.end_time, time):
            raise TypeError("slot.end_time must be time")

        if slot.end_time <= slot.start_time:
            raise ValueError("slot.end_time must be after slot.start_time")

        if not isinstance(slot.location, str):
            raise TypeError("slot.location must be str")

        if not isinstance(slot.slot_type, str) or slot.slot_type not in self.VALID_SLOT_TYPES:
            raise ValueError(
                f"slot.slot_type must be one of: {', '.join(sorted(self.VALID_SLOT_TYPES))}"
            )

        if not self._is_int(slot.start_week) or slot.start_week < 1:
            raise ValueError("slot.start_week must be a positive int")

        if not self._is_int(slot.end_week) or slot.end_week < slot.start_week:
            raise ValueError("slot.end_week must be >= slot.start_week")

        if not isinstance(slot.week_type, str) or slot.week_type not in self.VALID_WEEK_TYPES:
            raise ValueError(
                f"slot.week_type must be one of: {', '.join(sorted(self.VALID_WEEK_TYPES))}"
            )

        if not isinstance(slot.source, str) or slot.source not in self.VALID_SOURCES:
            raise ValueError(
                f"slot.source must be one of: {', '.join(sorted(self.VALID_SOURCES))}"
            )

        if slot.external_id is not None and not isinstance(slot.external_id, str):
            raise TypeError("slot.external_id must be str or None")

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

    def add(self, slot: ScheduleSlot) -> int:
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

    def list_all(self) -> List[ScheduleSlot]:
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM schedule_slots
            ORDER BY weekday ASC, start_time ASC
            """
        )
        return [self._row_to_slot(r) for r in cursor.fetchall()]

    def get_by_id(self, slot_id: int) -> Optional[ScheduleSlot]:
        if not self._is_int(slot_id):
            raise TypeError("slot_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            "SELECT * FROM schedule_slots WHERE id = ?",
            (slot_id,),
        )
        row = cursor.fetchone()
        return self._row_to_slot(row) if row else None

    def update(self, slot: ScheduleSlot) -> bool:
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

    def delete(self, slot_id: int) -> bool:
        if not self._is_int(slot_id):
            raise TypeError("slot_id must be int")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                "DELETE FROM schedule_slots WHERE id = ?",
                (slot_id,),
            )
        return cursor.rowcount > 0

    def list_by_weekday(self, weekday: int) -> List[ScheduleSlot]:
        if not self._is_int(weekday) or weekday < 1 or weekday > 7:
            raise ValueError("weekday must be in 1..7")

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
        return [self._row_to_slot(r) for r in cursor.fetchall()]

    def list_by_course(self, course_id: int) -> List[ScheduleSlot]:
        if not self._is_int(course_id):
            raise TypeError("course_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM schedule_slots
            WHERE course_id = ?
            ORDER BY weekday ASC, start_time ASC
            """,
            (course_id,),
        )
        return [self._row_to_slot(r) for r in cursor.fetchall()]

    def find_by_external_id(self, external_id: str) -> Optional[ScheduleSlot]:
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            "SELECT * FROM schedule_slots WHERE external_id = ?",
            (external_id,),
        )
        row = cursor.fetchone()
        return self._row_to_slot(row) if row else None
