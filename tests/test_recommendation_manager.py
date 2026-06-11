from datetime import date, datetime, time

from app.managers import recommendation_manager as recommendation_module
from app.managers.recommendation_manager import RecommendationManager
from app.models.schedule_slot import ScheduleSlot
from app.models.task import Task


class FakeTaskManager:
    def __init__(self, task):
        self.task = task

    def get_task(self, task_id):
        return self.task if task_id == self.task.id else None


class FakeScheduleManager:
    def get_free_slots(self, weekday, week):
        return [
            ScheduleSlot(
                title="Free time",
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(11, 0),
                location="",
                slot_type="free",
                start_week=week,
                end_week=week,
            )
        ]


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 6, 8)


def test_recommendations_do_not_use_past_semester_dates(monkeypatch):
    monkeypatch.setattr(recommendation_module, "date", FixedDate)
    task = Task(
        id=1,
        title="Report",
        due_time=datetime(2026, 6, 12, 23, 59),
        estimated_hours=1,
    )
    manager = RecommendationManager(FakeTaskManager(task), FakeScheduleManager())

    recommendations = manager.recommend_for_task(1, week=1, max_results=10)

    assert [slot.weekday for slot in recommendations] == [2, 3, 4, 5]
    assert all(slot.start_week == 15 for slot in recommendations)


def test_recommendations_skip_tasks_due_today(monkeypatch):
    monkeypatch.setattr(recommendation_module, "date", FixedDate)
    task = Task(
        id=1,
        title="Report",
        due_time=datetime(2026, 6, 8, 23, 59),
        estimated_hours=1,
    )
    manager = RecommendationManager(FakeTaskManager(task), FakeScheduleManager())

    assert manager.recommend_for_task(1) == []
