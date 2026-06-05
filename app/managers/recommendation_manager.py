"""Recommend free schedule slots for tasks."""
from __future__ import annotations

from app.models.schedule_slot import ScheduleSlot


class RecommendationManager:
    def __init__(self, task_manager, schedule_manager) -> None:
        self.task_manager = task_manager
        self.schedule_manager = schedule_manager

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

        weekday_order = list(range(1, 8))
        due_weekday = task.due_time.isoweekday()
        weekday_order.sort(key=lambda day: (day > due_weekday, day))

        candidates: list[ScheduleSlot] = []
        for weekday in weekday_order:
            for slot in self.schedule_manager.get_free_slots(weekday, week):
                if slot.can_hold_task(task):
                    candidates.append(slot)
        candidates.sort(key=lambda slot: (slot.weekday, slot.start_time))
        return candidates[:max_results]
