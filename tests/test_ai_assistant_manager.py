from datetime import date, datetime, time

from app.managers import ai_assistant_manager as ai_module
from app.managers.ai_assistant_manager import AIAssistantManager
from app.models.schedule_slot import ScheduleSlot
from app.models.task import Task


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 6, 8)


class FakeTaskManager:
    def list_tasks(self):
        return [
            Task(
                id=1,
                title="Essay",
                due_time=datetime(2026, 6, 12, 23, 59),
                estimated_hours=2,
            )
        ]

    def get_task(self, task_id):
        return self.list_tasks()[0] if task_id == 1 else None


class FakeScheduleManager:
    def __init__(self):
        self.slots = [
            ScheduleSlot(
                title="Linear Algebra",
                weekday=1,
                start_time=time(8, 0),
                end_time=time(9, 50),
                location="Room 101",
                slot_type="lecture",
                start_week=1,
                end_week=16,
            ),
            ScheduleSlot(
                title="Academic Writing",
                weekday=3,
                start_time=time(13, 0),
                end_time=time(14, 50),
                location="Room 202",
                slot_type="lecture",
                start_week=1,
                end_week=16,
            ),
        ]

    def list_slots(self, week, weekday=None):
        if weekday is None:
            return self.slots
        return [slot for slot in self.slots if slot.weekday == weekday]


def test_ai_context_includes_full_schedule_not_only_today(monkeypatch):
    monkeypatch.setattr(ai_module, "date", FixedDate)
    manager = AIAssistantManager(
        task_manager=FakeTaskManager(),
        schedule_manager=FakeScheduleManager(),
    )

    context = manager._build_data_context()

    assert "当前周完整课表" in context
    assert "全学期课表摘要" in context
    assert "Linear Algebra" in context
    assert "Academic Writing" in context


def test_reset_conversation_removes_history():
    manager = AIAssistantManager()

    conversation_id, _reply = manager.chat(None, "hello")
    assert conversation_id in manager._conversations

    assert manager.reset_conversation(conversation_id) is None
    assert conversation_id not in manager._conversations
