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

    def add_slot(self, data: dict) -> int:
        slot = self._dict_to_slot(data)
        # Upsert by external_id: when an import re-runs, existing rows must be
        # updated in place rather than duplicated. find_by_external_id only
        # matches source='sync' rows, so any slot carrying an external_id is
        # treated as sync-origin (manual entry never sets external_id).
        if slot.external_id:
            existing = self.schedule_repository.find_by_external_id(slot.external_id)
            if existing is not None:
                slot.id = existing.id
                self.schedule_repository.update(slot)
                return existing.id
        return self.schedule_repository.add(slot)

    def delete_all(self) -> int:
        """Delete every schedule slot. Returns the number of rows removed."""
        return self.schedule_repository.delete_all()

    def update_slot(self, slot_id: int, data: dict) -> None:
        if not isinstance(slot_id, int) or isinstance(slot_id, bool):
            raise TypeError("slot_id must be int")
        conn = self.schedule_repository.db_manager.get_connection()
        row = conn.execute("SELECT * FROM schedule_slots WHERE id = ?", (slot_id,)).fetchone()
        if row is None:
            raise ValueError(f"schedule slot {slot_id} not found")
        slot = self.schedule_repository._row_to_slot(row)
        coerced = self._coerce_slot_fields(data)
        for field, value in coerced.items():
            setattr(slot, field, value)
        if not self.schedule_repository.update(slot):
            raise ValueError(f"schedule slot {slot_id} not found")

    def delete_slot(self, slot_id: int) -> None:
        if not isinstance(slot_id, int) or isinstance(slot_id, bool):
            raise TypeError("slot_id must be int")
        if not self.schedule_repository.delete(slot_id):
            raise ValueError(f"schedule slot {slot_id} not found")

    def _dict_to_slot(self, data: dict) -> ScheduleSlot:
        from datetime import time as _time
        coerced = self._coerce_slot_fields(data)
        external_id = coerced.get("external_id")
        # Slots that come from an import / sync carry an external_id; slots
        # the user adds by hand never do. Tag the source accordingly so
        # find_by_external_id (which restricts to source='sync') can match.
        explicit_source = coerced.get("source")
        if explicit_source in ("manual", "sync"):
            source = explicit_source
        else:
            source = "sync" if external_id else "manual"
        return ScheduleSlot(
            title=coerced.get("title", ""),
            weekday=coerced.get("weekday", 1),
            start_time=coerced.get("start_time", _time(8, 0)),
            end_time=coerced.get("end_time", _time(9, 0)),
            location=coerced.get("location", ""),
            slot_type=coerced.get("slot_type", "custom"),
            start_week=coerced.get("start_week", 1),
            end_week=coerced.get("end_week", 16),
            week_type=coerced.get("week_type", "all"),
            course_id=coerced.get("course_id"),
            source=source,
            external_id=external_id,
        )

    @staticmethod
    def _coerce_slot_fields(data: dict) -> dict:
        from datetime import time as _time
        result = {}
        for key, value in data.items():
            if key in ("start_time", "end_time"):
                if isinstance(value, str):
                    text = value.strip()
                    if len(text.split(":")[0]) == 1:
                        text = "0" + text
                    result[key] = _time.fromisoformat(text[:5])
                elif isinstance(value, _time):
                    result[key] = value
            else:
                result[key] = value
        return result

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
