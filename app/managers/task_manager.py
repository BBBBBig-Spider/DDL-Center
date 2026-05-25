from __future__ import annotations

import math
from datetime import datetime

from app.models.task import Task
from app.repositories.task_repository import TaskRepository


__all__ = ["TaskManager"]


_VALID_ORDER_KEYS = {"due_time", "priority", "created_at", "updated_at"}

# Fields user code is allowed to set via create_task() / update_task().
# id / created_at / updated_at / completed_at / source / user_modified are managed internally.
_MUTABLE_FIELDS = {
    "title",
    "course_id",
    "related_exam_id",
    "description",
    "due_time",
    "estimated_hours",
    "status",
    "priority",
    "external_id",
    "raw_payload",
}


class TaskManager:
    """Day 2-9 业务逻辑：任务的 CRUD + 列表过滤 + 完成状态变更。"""

    def __init__(self, task_repository: TaskRepository):
        if not isinstance(task_repository, TaskRepository):
            raise TypeError("task_repository must be a TaskRepository")
        self.task_repository = task_repository

    # ─── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    @staticmethod
    def _coerce_estimated_hours(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("estimated_hours must be a number (not bool/str)")
        f = float(value)
        if not math.isfinite(f):
            raise ValueError("estimated_hours must be finite (no nan/inf)")
        if f < 0:
            raise ValueError("estimated_hours must be >= 0")
        return f

    def _validate_data(self, data: dict, *, for_update: bool) -> None:
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        unknown = set(data.keys()) - _MUTABLE_FIELDS
        if unknown:
            raise ValueError(f"unknown task fields: {', '.join(sorted(unknown))}")

        if not for_update:
            if "title" not in data:
                raise ValueError("title is required")
            if "due_time" not in data:
                raise ValueError("due_time is required")

    # ─── CRUD ───────────────────────────────────────────────────────

    def create_task(self, data: dict) -> int:
        """根据 dict 创建一个 manual 任务，返回新 id。"""
        self._validate_data(data, for_update=False)
        now = self._now()

        if "estimated_hours" in data:
            estimated_hours = self._coerce_estimated_hours(data["estimated_hours"])
        else:
            estimated_hours = 1.0

        task = Task(
            title=data["title"],
            due_time=data["due_time"],
            course_id=data.get("course_id"),
            related_exam_id=data.get("related_exam_id"),
            description=data.get("description", ""),
            estimated_hours=estimated_hours,
            status=data.get("status", "todo"),
            priority=data.get("priority", 2),
            source="manual",
            user_modified=False,
            external_id=data.get("external_id"),
            created_at=now,
            updated_at=now,
            completed_at=None,
            raw_payload=data.get("raw_payload", ""),
        )

        return self.task_repository.add(task)

    def update_task(self, task_id: int, data: dict) -> None:
        """按 task_id 更新若干字段。手动改过的任务标记 user_modified=True，
        以便同步流程跳过覆盖。"""
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        self._validate_data(data, for_update=True)

        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        for field_name, value in data.items():
            if field_name == "estimated_hours":
                value = self._coerce_estimated_hours(value)
            setattr(task, field_name, value)

        task.user_modified = True
        task.updated_at = self._now()

        if not self.task_repository.update(task):
            raise ValueError(f"task {task_id} not found")

    def delete_task(self, task_id: int) -> None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        if not self.task_repository.delete(task_id):
            raise ValueError(f"task {task_id} not found")

    def get_task(self, task_id: int) -> Task | None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        return self.task_repository.get_by_id(task_id)

    # ─── list / filter ──────────────────────────────────────────────

    def list_tasks(self, filters: dict | None = None) -> list[Task]:
        """支持的 filters：
            status: str
            course_id: int
            due_before: datetime
            due_after: datetime
            include_done: bool（默认 True）
            order_by: 'due_time' | 'priority' | 'created_at' | 'updated_at'（默认 due_time）
        """
        if filters is not None and not isinstance(filters, dict):
            raise TypeError("filters must be a dict or None")

        filters = filters or {}
        unknown = set(filters.keys()) - {
            "status",
            "course_id",
            "due_before",
            "due_after",
            "include_done",
            "order_by",
        }
        if unknown:
            raise ValueError(f"unknown filter keys: {', '.join(sorted(unknown))}")

        tasks = self.task_repository.list_all()

        if "status" in filters:
            status = filters["status"]
            if not isinstance(status, str):
                raise TypeError("status filter must be str")
            tasks = [t for t in tasks if t.status == status]

        if "course_id" in filters:
            course_id = filters["course_id"]
            if not self._is_int(course_id):
                raise TypeError("course_id filter must be int")
            tasks = [t for t in tasks if t.course_id == course_id]

        if "due_before" in filters:
            due_before = filters["due_before"]
            if not isinstance(due_before, datetime):
                raise TypeError("due_before filter must be datetime")
            tasks = [t for t in tasks if t.due_time <= due_before]

        if "due_after" in filters:
            due_after = filters["due_after"]
            if not isinstance(due_after, datetime):
                raise TypeError("due_after filter must be datetime")
            tasks = [t for t in tasks if t.due_time >= due_after]

        if "include_done" in filters:
            include_done = filters["include_done"]
            if not isinstance(include_done, bool):
                raise TypeError("include_done filter must be bool")
            if not include_done:
                tasks = [t for t in tasks if not t.is_done()]

        order_by = filters.get("order_by", "due_time")
        if order_by not in _VALID_ORDER_KEYS:
            raise ValueError(f"order_by must be one of: {', '.join(sorted(_VALID_ORDER_KEYS))}")
        tasks.sort(key=lambda t: getattr(t, order_by))

        return tasks

    # ─── status transition ─────────────────────────────────────────

    def mark_done(self, task_id: int) -> None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        task.mark_done(self._now())
        self.task_repository.update(task)

    def reopen(self, task_id: int) -> None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        task.reopen(self._now())
        self.task_repository.update(task)

    # ─── convenience listings ──────────────────────────────────────

    def list_by_course(self, course_id: int) -> list[Task]:
        return self.list_tasks({"course_id": course_id})

    def list_by_status(self, status: str) -> list[Task]:
        return self.list_tasks({"status": status})
