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
from app.managers.course_manager import CourseManager
from app.managers.exam_manager import ExamManager
from app.managers.schedule_manager import ScheduleManager
from app.managers.recommendation_manager import RecommendationManager
from app.managers.statistics_manager import StatisticsManager
from app.managers.sync_manager import SyncManager
from app.managers.ai_assistant_manager import AIAssistantManager


__all__ = ["AppFacade"]


class AppFacade:
    def __init__(
        self,
        task_manager: TaskManager,
        alert_manager: AlertManager | None = None,
        course_manager: CourseManager | None = None,
        exam_manager: ExamManager | None = None,
        schedule_manager: ScheduleManager | None = None,
        recommendation_manager: RecommendationManager | None = None,
        statistics_manager: StatisticsManager | None = None,
        sync_manager: SyncManager | None = None,
        ai_assistant_manager: AIAssistantManager | None = None,
    ):
        self.task_manager = task_manager
        self.alert_manager = alert_manager
        self.course_manager = course_manager
        self.exam_manager = exam_manager
        self.schedule_manager = schedule_manager
        self.recommendation_manager = recommendation_manager
        self.statistics_manager = statistics_manager
        self.sync_manager = sync_manager
        self.ai_assistant_manager = ai_assistant_manager

    # ─── 任务 ─────────────────────────────────────────────────

    def create_task(self, data: dict) -> int:
        return self.task_manager.create_task(data)
    def update_task(self, task_id: int, data: dict) -> None:
        self.task_manager.update_task(task_id, data)
    def delete_task(self, task_id: int) -> None:
        self.task_manager.delete_task(task_id)
    def list_tasks(self, filters: dict | None = None) -> list[Task]:
        tasks = self.task_manager.list_tasks(filters)
        self._enrich_course_names(tasks)
        return tasks

    def _enrich_course_names(self, tasks: list[Task]) -> None:
        """Attach course_name attribute to each task so the GUI can display it."""
        if self.course_manager is None:
            return
        try:
            courses = {c.id: c.name for c in self.course_manager.list_courses()}
        except Exception:
            return
        for task in tasks:
            if task.course_id is not None:
                task.course_name = courses.get(task.course_id, "")  # type: ignore[attr-defined]
            else:
                task.course_name = ""  # type: ignore[attr-defined]
    def mark_task_done(self, task_id: int) -> None:
        self.task_manager.mark_done(task_id)

    # ─── 课程 / 考试 / 课表（Week 3 起补） ────────────────────

    def list_courses(self) -> list[Course]:
        if self.course_manager is None:
            raise RuntimeError("course_manager not wired into AppFacade")
        return self.course_manager.list_courses()

    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        if self.exam_manager is None:
            raise RuntimeError("exam_manager not wired into AppFacade")
        return self.exam_manager.list_exams(course_id)

    def create_exam(self, data: dict) -> int:
        if self.exam_manager is None:
            raise RuntimeError("exam_manager not wired into AppFacade")
        if not hasattr(self.exam_manager, "create_exam"):
            raise RuntimeError("exam_manager does not support creating exams")
        return self.exam_manager.create_exam(data)

    def list_schedule(self, weekday: int, week: int) -> list[ScheduleSlot]:
        if self.schedule_manager is None:
            raise RuntimeError("schedule_manager not wired into AppFacade")
        return self.schedule_manager.list_slots(week, weekday)

    def get_free_slots(self, weekday: int, week: int) -> list[ScheduleSlot]:
        if self.schedule_manager is None:
            raise RuntimeError("schedule_manager not wired into AppFacade")
        return self.schedule_manager.get_free_slots(weekday, week)

    def create_schedule_slot(self, data: dict) -> int:
        if self.schedule_manager is None:
            raise RuntimeError("schedule_manager not wired into AppFacade")
        return self.schedule_manager.add_slot(data)

    def update_schedule_slot(self, slot_id: int, data: dict) -> None:
        if self.schedule_manager is None:
            raise RuntimeError("schedule_manager not wired into AppFacade")
        self.schedule_manager.update_slot(slot_id, data)

    def delete_schedule_slot(self, slot_id: int) -> None:
        if self.schedule_manager is None:
            raise RuntimeError("schedule_manager not wired into AppFacade")
        self.schedule_manager.delete_slot(slot_id)

    # ─── 提醒 ─────────────────────────────────────────────────

    def generate_alerts(self) -> list[Alert]:
        if self.alert_manager is None:
            raise RuntimeError("alert_manager not wired into AppFacade")
        return self.alert_manager.generate_alerts()

    def list_all_alerts(self) -> list[Alert]:
        if self.alert_manager is None or self.alert_manager.alert_repository is None:
            raise RuntimeError("alert_repository not wired into AppFacade")
        return self.alert_manager.alert_repository.list_all()

    def recommend_for_task(self, task_id: int, *, week: int = 1, max_results: int = 5) -> list[ScheduleSlot]:
        if self.recommendation_manager is None:
            raise RuntimeError("recommendation_manager not wired into AppFacade")
        return self.recommendation_manager.recommend_for_task(task_id, week=week, max_results=max_results)

    def arrange_task_at_slot(self, task_id: int, slot_obj) -> None:
        if self.recommendation_manager is None:
            raise RuntimeError("recommendation_manager not wired into AppFacade")
        self.recommendation_manager.arrange_task_at_slot(task_id, slot_obj)

    def cancel_task_arrangement(self, task_id: int) -> None:
        if self.recommendation_manager is None:
            raise RuntimeError("recommendation_manager not wired into AppFacade")
        self.recommendation_manager.cancel_task_arrangement(task_id)

    def get_task_arrangement(self, task_id: int) -> dict | None:
        if self.recommendation_manager is None:
            return None
        return self.recommendation_manager.get_task_arrangement(task_id)

    def list_task_arrangements(self, week: int | None = None) -> list[dict]:
        if self.recommendation_manager is None:
            return []
        return self.recommendation_manager.list_task_arrangements(week)

    # ─── 同步 / 统计 ──────────────────────────────────────────

    def sync_from_teaching_site(self, username: str, password: str, otp_code: str = ""):
        if self.sync_manager is None:
            raise RuntimeError("sync_manager not wired into AppFacade")
        return self.sync_manager.sync_from_teaching_site(username, password, otp_code=otp_code)

    def get_statistics(self):
        if self.statistics_manager is None:
            raise RuntimeError("statistics_manager not wired into AppFacade")
        return self.statistics_manager.get_statistics()

    def purge_overdue_tasks(self) -> int:
        return self.task_manager.purge_overdue_tasks()

    def find_or_create_course_by_name(self, name: str) -> int | None:
        if self.course_manager is None:
            return None
        try:
            return self.course_manager.find_or_create_by_name(name)
        except Exception:
            return None

    def set_exam_week_range(self, start: str | None, end: str | None) -> None:
        setting_repository = getattr(self, "setting_repository", None)
        if setting_repository is None:
            return
        if start:
            setting_repository.set("exam_week_start", start)
        if end:
            setting_repository.set("exam_week_end", end)

    def get_exam_week_range(self) -> tuple[str | None, str | None]:
        setting_repository = getattr(self, "setting_repository", None)
        if setting_repository is None:
            return None, None
        return (
            setting_repository.get("exam_week_start"),
            setting_repository.get("exam_week_end"),
        )

    # ─── AI 相关 ──────────────────────────────────────────────

    def ai_decompose_task(self, description: str, due_time: datetime) -> list[dict]:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.decompose_task(description, due_time)

    def ai_chat(self, conversation_id: int | None, user_msg: str,
                context_task_id: int | None = None) -> tuple[int, str]:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.chat(conversation_id, user_msg, context_task_id)

    def ai_reset_conversation(self, conversation_id: int | None = None) -> int | None:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.reset_conversation(conversation_id)

    def ai_generate_briefing(self) -> str:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.generate_briefing()

    def ai_summarize_ddl(self, raw_text: str) -> str:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.summarize_ddl(raw_text)

    # ─── AI 设置 ──────────────────────────────────────────────

    def set_deepseek_api_key(self, key: str) -> None:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        self.ai_assistant_manager.set_api_key(key)

    def get_deepseek_api_key(self) -> str | None:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.get_api_key()

    def test_deepseek_api_key(self, key: str) -> bool:
        if self.ai_assistant_manager is None:
            raise RuntimeError("ai_assistant_manager not wired into AppFacade")
        return self.ai_assistant_manager.test_api_key(key)

    def ai_is_available(self) -> bool:
        return (
            self.ai_assistant_manager is not None
            and self.ai_assistant_manager.is_available()
        )

    def ai_today_token_usage(self) -> int:
        if self.ai_assistant_manager is None:
            return 0
        return self.ai_assistant_manager.today_token_usage()
