"""Recommend free schedule slots for tasks."""
from __future__ import annotations

from datetime import date, timedelta

from app.config import SEMESTER_START
from app.models.schedule_slot import ScheduleSlot
from app.utils.semester import compute_current_week


class RecommendationManager:
    def __init__(self, task_manager, schedule_manager) -> None:
        self.task_manager = task_manager
        self.schedule_manager = schedule_manager
        # task_id -> arrangement dict (in-memory; no DB table for arrangements yet)
        self._arrangements: dict[int, dict] = {}

    def recommend_for_task(
        self,
        task_id: int,
        *,
        week: int = 1,
        max_results: int = 5,
    ) -> list[ScheduleSlot]:
        task = self.task_manager.get_task(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        if task.is_done():
            return []

        today = date.today()
        first_allowed_date = today + timedelta(days=1)
        due_date = task.due_time.date()
        if due_date < first_allowed_date:
            return []

        current_week = compute_current_week(
            getattr(self.task_manager, "setting_repository", None)
        )
        week = max(week, current_week)

        weekday_order = list(range(1, 8))
        due_weekday = task.due_time.isoweekday()
        weekday_order.sort(key=lambda day: (day > due_weekday, day))

        candidates: list[ScheduleSlot] = []
        for weekday in weekday_order:
            slot_date = self._date_for_weekday(week, weekday)
            if slot_date < first_allowed_date or slot_date > due_date:
                continue
            for slot in self.schedule_manager.get_free_slots(weekday, week):
                if slot.can_hold_task(task):
                    candidates.append(slot)
        candidates.sort(key=lambda slot: (self._date_for_weekday(week, slot.weekday), slot.start_time))
        return candidates[:max_results]

    @staticmethod
    def _date_for_weekday(week: int, weekday: int) -> date:
        return SEMESTER_START + timedelta(days=(week - 1) * 7 + weekday - 1)

    # ─── 任务安排 CRUD（内存，重启后清空）────────────────────────

    def arrange_task_at_slot(self, task_id: int, slot_obj) -> None:
        """将 task_id 与某个时间段关联，覆盖旧安排。"""
        def _fmt(v) -> str:
            if v is None:
                return ""
            if isinstance(v, str):
                return v[:5]
            if hasattr(v, "strftime"):
                return v.strftime("%H:%M")
            return str(v)[:5]

        def _get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        task = self.task_manager.get_task(task_id)
        task_title = task.title if task else str(task_id)
        week = _get(slot_obj, "start_week")
        self._arrangements[task_id] = {
            "task_id": task_id,
            "task_title": task_title,
            "title": task_title,
            "weekday": _get(slot_obj, "weekday", 1),
            "start_time": _fmt(_get(slot_obj, "start_time", "09:00")),
            "end_time": _fmt(_get(slot_obj, "end_time", "11:00")),
            "location": _get(slot_obj, "location", "") or "任务安排",
            "week": week,
            "source": "gui",
        }

    def cancel_task_arrangement(self, task_id: int) -> None:
        self._arrangements.pop(task_id, None)

    def get_task_arrangement(self, task_id: int) -> dict | None:
        return self._arrangements.get(task_id)

    def list_task_arrangements(self, week: int | None = None) -> list[dict]:
        items = list(self._arrangements.values())
        if week is not None:
            items = [a for a in items if a.get("week") in (None, week)]
        return items
