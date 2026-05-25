"""app/managers/app_facade.py"""
from __future__ import annotations

from datetime import datetime

from app.models.task import Task
from app.models.course import Course
from app.models.exam import Exam
from app.models.schedule_slot import ScheduleSlot
from app.models.alert import Alert

from app.managers.task_manager import TaskManager
from app.managers.alert_manager import AlertManager


__all__ = ["AppFacade"]


class AppFacade:
    def __init__(
        self,
        task_manager: TaskManager,
        alert_manager: AlertManager | None = None,
    ):
        self.task_manager = task_manager
        self.alert_manager = alert_manager

    # ─── 任务 ─────────────────────────────────────────────────

    def create_task(self, data: dict) -> int:
        return self.task_manager.create_task(data)
    def update_task(self, task_id: int, data: dict) -> None:
        self.task_manager.update_task(task_id, data)
    def delete_task(self, task_id: int) -> None:
        self.task_manager.delete_task(task_id)
    def list_tasks(self, filters: dict | None = None) -> list[Task]:
        return self.task_manager.list_tasks(filters)
    def mark_task_done(self, task_id: int) -> None:
        self.task_manager.mark_done(task_id)

    # ─── 课程 / 考试 / 课表（Week 3 起补） ────────────────────

    def list_courses(self) -> list[Course]:
        raise NotImplementedError
    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        raise NotImplementedError
    def list_schedule(self, weekday: int, week: int) -> list[ScheduleSlot]:
        raise NotImplementedError
    def get_free_slots(self, weekday: int, week: int) -> list[ScheduleSlot]:
        raise NotImplementedError

    # ─── 提醒 ─────────────────────────────────────────────────

    def generate_alerts(self) -> list[Alert]:
        if self.alert_manager is None:
            raise RuntimeError("alert_manager not wired into AppFacade")
        return self.alert_manager.generate_alerts()

    def recommend_for_task(self, task_id: int) -> list[ScheduleSlot]:
        raise NotImplementedError

    # ─── 同步 / 统计 ──────────────────────────────────────────

    def sync_from_teaching_site(self, username: str, password: str):
        raise NotImplementedError
    def get_statistics(self):
        raise NotImplementedError

    # ─── AI 相关 ──────────────────────────────────────────────

    def ai_decompose_task(self, description: str, due_time: datetime) -> list[dict]:
        raise NotImplementedError
    def ai_chat(self, conversation_id: int | None, user_msg: str,
                context_task_id: int | None = None) -> tuple[int, str]:
        raise NotImplementedError
    def ai_generate_briefing(self) -> str:
        raise NotImplementedError
    def ai_summarize_ddl(self, raw_text: str) -> str:
        raise NotImplementedError

    # ─── AI 设置 ──────────────────────────────────────────────

    def set_deepseek_api_key(self, key: str) -> None:
        raise NotImplementedError
    def get_deepseek_api_key(self) -> str | None:
        raise NotImplementedError
    def test_deepseek_api_key(self, key: str) -> bool:
        raise NotImplementedError
    def ai_is_available(self) -> bool:
        raise NotImplementedError
    def ai_today_token_usage(self) -> int:
        raise NotImplementedError
