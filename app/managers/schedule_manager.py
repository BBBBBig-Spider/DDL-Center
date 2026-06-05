"""Schedule query and free-slot logic."""
from __future__ import annotations

from datetime import time

from app.models.schedule_slot import ScheduleSlot


class ScheduleManager:
    DAY_START = time(8, 0)
    DAY_END = time(22, 0)

    def __init__(self, schedule_repository) -> None:
        self.schedule_repository = schedule_repository

    def list_slots(self, week: int, weekday: int | None = None) -> list[ScheduleSlot]:
        self._validate_week(week)
        if weekday is not None:
            self._validate_weekday(weekday)
        return self.schedule_repository.list_by_week(week, weekday)

    def get_free_slots(self, weekday: int, week: int) -> list[ScheduleSlot]:
        self._validate_weekday(weekday)
        self._validate_week(week)
        occupied = sorted(
            self.schedule_repository.list_by_week(week, weekday),
            key=lambda slot: slot.start_time,
        )

        free_slots: list[ScheduleSlot] = []
        cursor = self.DAY_START
        for slot in occupied:
            if slot.start_time > cursor:
                free_slots.append(self._free_slot(weekday, week, cursor, slot.start_time))
            if slot.end_time > cursor:
                cursor = slot.end_time
        if cursor < self.DAY_END:
            free_slots.append(self._free_slot(weekday, week, cursor, self.DAY_END))
        return free_slots

    def has_conflict(self, candidate: ScheduleSlot) -> bool:
        if not isinstance(candidate, ScheduleSlot):
            raise TypeError("candidate must be ScheduleSlot")
        for slot in self.schedule_repository.list_by_weekday(candidate.weekday):
            if candidate.id is not None and slot.id == candidate.id:
                continue
            if candidate.overlaps_with(slot):
                return True
        return False

    @staticmethod
    def _free_slot(weekday: int, week: int, start: time, end: time) -> ScheduleSlot:
        return ScheduleSlot(
            title="Free time",
            weekday=weekday,
            start_time=start,
            end_time=end,
            location="",
            slot_type="free",
            start_week=week,
            end_week=week,
            week_type="all",
        )

    @staticmethod
    def _validate_week(week: int) -> None:
        if not isinstance(week, int) or isinstance(week, bool):
            raise TypeError("week must be int")
        if week < 1:
            raise ValueError("week must be >= 1")

    @staticmethod
    def _validate_weekday(weekday: int) -> None:
        if not isinstance(weekday, int) or isinstance(weekday, bool):
            raise TypeError("weekday must be int")
        if weekday not in range(1, 8):
            raise ValueError("weekday must be in 1..7")
