from __future__ import annotations

from datetime import datetime

from app.models.task import Task
from app.models.course import Course
from app.models.exam import Exam
from app.models.schedule_slot import ScheduleSlot
from app.models.alert import Alert

from app.managers.task_manager import TaskManager

__all__ = ["AppFacade"]


class AppFacade:
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
    def create_task(self, data: dict) -> int:
        self.task_manager.create_task(data)
    def update_task(self, task_id: int, data: dict) -> None:
        self.task_manager.update_task(task_id, data)
    def delete_task(self, task_id: int) -> None:
        self.task_manager.delete_task(task_id)
    def get_task(self, task_id: int) -> Task | None:
        self.task_manager.get_task(task_id)
    def list_tasks(self, filters: dict | None = None) -> list[Task]:
        self.task_manager.list_tasks(filters)
    def mark_task_done(self, task_id: int) -> None:
        self.task_manager.mark_done(task_id)

    def list_courses(self) -> list[Course]:
        raise NotImplementedError
    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        raise NotImplementedError

    def list_schedule(self, weekday: int, week: int) -> list[ScheduleSlot]:
        raise NotImplementedError
    def get_free_slots(self, weekday: int, week: int) -> list[ScheduleSlot]:
        raise NotImplementedError

    def generate_alerts(self) -> list[Alert]:
        raise NotImplementedError
    def recommend_for_task(self, task_id: int) -> list[ScheduleSlot]:
        raise NotImplementedError

    def sync_from_teaching_site(self, username: str, password: str) -> SyncResult:
        raise NotImplementedError
    def get_statistics(self) -> StatisticsData:
        raise NotImplementedError

    # ─── AI 相关 ───
    def ai_decompose_task(self, description: str, due_time: datetime) -> list[dict]:  # 功能 1
        raise NotImplementedError
    def ai_chat(self, conversation_id: int | None, user_msg: str, 
                context_task_id: int | None = None) -> tuple[int, str]:         # 功能 3
        raise NotImplementedError
    def ai_generate_briefing(self) -> str:                                          # 功能 4
        raise NotImplementedError
    def ai_summarize_ddl(self, raw_text: str) -> str:                                 # 功能 5
        raise NotImplementedError

    # ─── AI 设置 ───
    def set_deepseek_api_key(self, key: str) -> None:
        raise NotImplementedError
    def get_deepseek_api_key(self) -> str | None:
        raise NotImplementedError
    def test_deepseek_api_key(self, key: str) -> bool:
        raise NotImplementedError
    def ai_is_available(self) -> bool:                  # Key 已配且未超额时返回 True
        raise NotImplementedError
    def ai_today_token_usage(self) -> int:              # 今日已用 token 数
        raise NotImplementedError