"""app/managers/app_facade.py"""
from __future__ import annotations

from datetime import datetime
from typing import TypeVar

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

_T = TypeVar("_T")


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

    def _require(self, attr_name: str) -> _T:
        """Return the named manager attribute or raise a uniform RuntimeError.

        Centralizes the "X_manager not wired into AppFacade" boilerplate so
        every method body can stay one line. Error string matches the previous
        per-method messages so existing callers and tests keep working.
        """
        manager = getattr(self, attr_name, None)
        if manager is None:
            raise RuntimeError(f"{attr_name} not wired into AppFacade")
        return manager

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
        return self._require("course_manager").list_courses()

    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        return self._require("exam_manager").list_exams(course_id)

    def create_exam(self, data: dict) -> int:
        manager = self._require("exam_manager")
        if not hasattr(manager, "create_exam"):
            raise RuntimeError("exam_manager does not support creating exams")
        return manager.create_exam(data)

    def list_schedule(self, weekday: int, week: int) -> list[ScheduleSlot]:
        return self._require("schedule_manager").list_slots(week, weekday)

    def get_free_slots(self, weekday: int, week: int) -> list[ScheduleSlot]:
        return self._require("schedule_manager").get_free_slots(weekday, week)

    def create_schedule_slot(self, data: dict) -> int:
        return self._require("schedule_manager").add_slot(data)

    def update_schedule_slot(self, slot_id: int, data: dict) -> None:
        self._require("schedule_manager").update_slot(slot_id, data)

    def delete_schedule_slot(self, slot_id: int) -> None:
        self._require("schedule_manager").delete_slot(slot_id)

    def clear_all_schedule_and_exams(self) -> dict:
        """Used by the 'overwrite' import mode.

        Deletes all schedule slots and exams, regardless of source (manual
        or sync). Does NOT touch courses, tasks, or anything else — tasks
        carry a course_id FK so dropping courses would orphan/break the
        user's task list. Returns a small summary the UI can display.
        """
        summary = {"slots_deleted": 0, "exams_deleted": 0}
        if self.schedule_manager is not None:
            try:
                summary["slots_deleted"] = self.schedule_manager.delete_all()
            except Exception as exc:
                print(f"[CLEAR] schedule delete failed: {exc}")
        if self.exam_manager is not None:
            try:
                summary["exams_deleted"] = self.exam_manager.delete_all()
            except Exception as exc:
                print(f"[CLEAR] exam delete failed: {exc}")
        return summary

    # ─── 提醒 ─────────────────────────────────────────────────

    def generate_alerts(self) -> list[Alert]:
        return self._require("alert_manager").generate_alerts()

    def list_all_alerts(self) -> list[Alert]:
        manager = self._require("alert_manager")
        if manager.alert_repository is None:
            raise RuntimeError("alert_repository not wired into AppFacade")
        return manager.alert_repository.list_all()

    def recommend_for_task(self, task_id: int, *, week: int = 1, max_results: int = 5) -> list[ScheduleSlot]:
        return self._require("recommendation_manager").recommend_for_task(
            task_id, week=week, max_results=max_results
        )

    def arrange_task_at_slot(self, task_id: int, slot_obj) -> None:
        self._require("recommendation_manager").arrange_task_at_slot(task_id, slot_obj)

    def cancel_task_arrangement(self, task_id: int) -> None:
        self._require("recommendation_manager").cancel_task_arrangement(task_id)

    def get_task_arrangement(self, task_id: int) -> dict | None:
        if self.recommendation_manager is None:
            return None
        return self.recommendation_manager.get_task_arrangement(task_id)

    def list_task_arrangements(self, week: int | None = None) -> list[dict]:
        if self.recommendation_manager is None:
            return []
        return self.recommendation_manager.list_task_arrangements(week)

    # ─── 同步 / 统计 ──────────────────────────────────────────

    def sync_from_teaching_site(self, username: str, password: str):
        return self._require("sync_manager").sync_from_teaching_site(username, password)

    def get_auth_client(self):
        return self._require("sync_manager").auth_client

    def logout_and_reset_local_state(self) -> dict:
        """Wipe ALL local user data so the next launch is a clean slate.

        Removes:
          - data/ddl_center.db        (tasks, courses, schedules, exams,
                                       alerts, settings — including avatar,
                                       display_name, theme choice, font scale,
                                       now-line color, deepseek_model)
          - data/.theme_palette       (active theme name)
          - .env (PKU_USERNAME / PKU_PASSWORD entries)

        Preserves:
          - The Deepseek API key in the OS keyring (independent of login)
          - Sync probe caches (data/last_*.json) — already gitignored

        The caller MUST restart the app after this returns: in-memory
        repositories still hold a reference to the now-deleted DB file.
        Returns a small dict for the UI to display in the confirmation toast.
        """
        from pathlib import Path
        from app.services import credentials_store

        summary = {
            "db_deleted": False,
            "theme_palette_deleted": False,
            "credentials_cleared": False,
        }

        # Best-effort: close any open DB connection so Windows lets us delete
        # the file. SQLite on Windows holds a file lock until close().
        db_manager = getattr(self, "db_manager", None)
        if db_manager is not None and hasattr(db_manager, "close"):
            try:
                db_manager.close()
            except Exception as exc:
                print(f"[LOGOUT] failed to close db_manager: {exc}")

        db_path = Path("data") / "ddl_center.db"
        try:
            if db_path.exists():
                db_path.unlink()
                summary["db_deleted"] = True
        except Exception as exc:
            print(f"[LOGOUT] failed to delete {db_path}: {exc}")

        palette_path = Path("data") / ".theme_palette"
        try:
            if palette_path.exists():
                palette_path.unlink()
                summary["theme_palette_deleted"] = True
        except Exception as exc:
            print(f"[LOGOUT] failed to delete {palette_path}: {exc}")

        try:
            credentials_store.clear()
            summary["credentials_cleared"] = True
        except Exception as exc:
            print(f"[LOGOUT] failed to clear credentials: {exc}")

        return summary

    def get_statistics(self):
        return self._require("statistics_manager").get_statistics()

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
        return self._require("ai_assistant_manager").decompose_task(description, due_time)

    def ai_chat(self, conversation_id: int | None, user_msg: str,
                context_task_id: int | None = None) -> tuple[int, str]:
        return self._require("ai_assistant_manager").chat(
            conversation_id, user_msg, context_task_id
        )

    def ai_reset_conversation(self, conversation_id: int | None = None) -> int | None:
        return self._require("ai_assistant_manager").reset_conversation(conversation_id)

    def ai_generate_briefing(self) -> str:
        return self._require("ai_assistant_manager").generate_briefing()

    def ai_summarize_ddl(self, raw_text: str) -> str:
        return self._require("ai_assistant_manager").summarize_ddl(raw_text)

    def ai_parse_task_from_text(self, raw_text: str) -> dict:
        return self._require("ai_assistant_manager").parse_task_from_text(raw_text)

    def ai_parse_item_from_text(self, raw_text: str) -> dict:
        return self._require("ai_assistant_manager").parse_item_from_text(raw_text)

    # ─── AI 设置 ──────────────────────────────────────────────

    def set_deepseek_api_key(self, key: str) -> None:
        self._require("ai_assistant_manager").set_api_key(key)

    def get_deepseek_api_key(self) -> str | None:
        return self._require("ai_assistant_manager").get_api_key()

    def set_deepseek_model(self, model: str) -> None:
        self._require("ai_assistant_manager").set_model(model)

    def get_deepseek_model(self) -> str:
        return self._require("ai_assistant_manager").get_model()

    def test_deepseek_api_key(self, key: str) -> bool:
        return self._require("ai_assistant_manager").test_api_key(key)

    def ai_is_available(self) -> bool:
        return (
            self.ai_assistant_manager is not None
            and self.ai_assistant_manager.is_available()
        )

    def ai_today_token_usage(self) -> int:
        if self.ai_assistant_manager is None:
            return 0
        return self.ai_assistant_manager.today_token_usage()

    # ─── 学期设置 ─────────────────────────────────────────────

    def get_semester_settings(self) -> dict:
        """Read semester start date and total weeks from setting_repository.

        Falls back to SEMESTER_START / 20 when nothing has been written yet."""
        from app.config import SEMESTER_START
        setting_repository = getattr(self, "setting_repository", None)
        start = SEMESTER_START.isoformat()
        total_weeks = 20
        if setting_repository is not None:
            try:
                stored_start = setting_repository.get("semester_start")
                if stored_start:
                    start = stored_start
                stored_weeks = setting_repository.get("semester_total_weeks")
                if stored_weeks:
                    total_weeks = int(stored_weeks)
            except Exception:
                pass
        return {"start": start, "total_weeks": total_weeks}

    def set_semester_settings(self, *, start: str, total_weeks: int) -> None:
        setting_repository = getattr(self, "setting_repository", None)
        if setting_repository is None:
            return
        if start:
            setting_repository.set("semester_start", start)
        if isinstance(total_weeks, int) and 1 <= total_weeks <= 30:
            setting_repository.set("semester_total_weeks", str(total_weeks))
