"""app/managers/task_manager.py"""
from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from app.models.task import Task
from app.repositories.task_repository import TaskRepository


__all__ = ["TaskManager"]


class TaskManager:
    """tasks 表的业务逻辑：CRUD + 过滤 + 完成/重开。"""

    VALID_ORDER_KEYS = {"due_time", "priority", "created_at", "updated_at"}
    VALID_STATUSES = {"todo", "doing", "done", "blocked"}
    VALID_FILTER_KEYS = {"status", "course_id", "due_before", "order_by"}
    UPDATABLE_FIELDS = {
        "title", "due_time", "course_id", "related_exam_id",
        "description", "estimated_hours", "status", "priority",
        "external_id", "raw_payload",
    }

    def __init__(self, task_repository: TaskRepository):
        if not isinstance(task_repository, TaskRepository):
            raise TypeError("task_repository must be a TaskRepository")
        self.task_repository = task_repository

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    @staticmethod
    def _coerce_hours(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("estimated_hours must be a number")
        f = float(value)
        if not math.isfinite(f):
            raise ValueError("estimated_hours must be finite")
        if f < 0:
            raise ValueError("estimated_hours must be >= 0")
        return f

    # ─── 增 ────────────────────────────────────────────────────

    def create_task(self, data: dict) -> int:
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        if "title" not in data:
            raise ValueError("title is required")
        if "due_time" not in data:
            raise ValueError("due_time is required")

        now = datetime.now()
        task = Task(
            title=data["title"],
            due_time=data["due_time"],
            course_id=data.get("course_id"),
            related_exam_id=data.get("related_exam_id"),
            description=data.get("description", ""),
            estimated_hours=self._coerce_hours(data.get("estimated_hours", 1.0)),
            status=data.get("status", "todo"),
            priority=data.get("priority", 2),
            source="manual",
            user_modified=False,
            external_id=data.get("external_id"),
            created_at=now,
            updated_at=now,
            raw_payload=data.get("raw_payload", ""),
        )

        return self.task_repository.add(task)

    # ─── 查 ────────────────────────────────────────────────────

    def get_task(self, task_id: int) -> Optional[Task]:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        return self.task_repository.get_by_id(task_id)

    def list_tasks(self, filters: dict | None = None) -> List[Task]:
        """支持的 filters：status / course_id / due_before / order_by。
        不传或传 None 返回所有任务，默认按 due_time 升序。"""
        if filters is not None and not isinstance(filters, dict):
            raise TypeError("filters must be a dict or None")
        filters = filters or {}

        unknown = set(filters) - self.VALID_FILTER_KEYS
        if unknown:
            raise ValueError(f"unknown filter keys: {', '.join(sorted(unknown))}")

        tasks = self.task_repository.list_all()

        if "status" in filters:
            status = filters["status"]
            if not isinstance(status, str):
                raise TypeError("filters['status'] must be str")
            if status not in self.VALID_STATUSES:
                raise ValueError(
                    f"filters['status'] must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
                )
            tasks = [t for t in tasks if t.status == status]

        if "course_id" in filters:
            cid = filters["course_id"]
            if not self._is_int(cid):
                raise TypeError("filters['course_id'] must be int")
            tasks = [t for t in tasks if t.course_id == cid]

        if "due_before" in filters:
            due_before = filters["due_before"]
            if not isinstance(due_before, datetime):
                raise TypeError("filters['due_before'] must be datetime")
            tasks = [t for t in tasks if t.due_time <= due_before]

        order_by = filters.get("order_by", "due_time")
        if order_by not in self.VALID_ORDER_KEYS:
            raise ValueError(
                f"order_by must be one of: {', '.join(sorted(self.VALID_ORDER_KEYS))}"
            )
        tasks.sort(key=lambda t: getattr(t, order_by))

        return tasks

    def list_by_course(self, course_id: int) -> List[Task]:
        return self.list_tasks({"course_id": course_id})

    def list_by_status(self, status: str) -> List[Task]:
        return self.list_tasks({"status": status})

    # ─── 改 ────────────────────────────────────────────────────

    def update_task(self, task_id: int, data: dict) -> None:
        """按 task_id 更新若干字段。GUI 手动编辑会把 user_modified=1，
        同步流程因此跳过覆盖（见架构 2.6 SyncManager 规则）。"""
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        unknown = set(data) - self.UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"unknown or read-only fields: {', '.join(sorted(unknown))}")

        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        if "estimated_hours" in data:
            data = dict(data)
            data["estimated_hours"] = self._coerce_hours(data["estimated_hours"])

        for field, value in data.items():
            setattr(task, field, value)

        task.user_modified = True
        task.updated_at = datetime.now()

        if not self.task_repository.update(task):
            raise ValueError(f"task {task_id} not found")

    def mark_done(self, task_id: int) -> None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        task.mark_done(datetime.now())
        if not self.task_repository.update(task):
            raise ValueError(f"task {task_id} not found")

    # ─── 删 ────────────────────────────────────────────────────

    def delete_task(self, task_id: int) -> None:
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")
        if not self.task_repository.delete(task_id):
            raise ValueError(f"task {task_id} not found")
