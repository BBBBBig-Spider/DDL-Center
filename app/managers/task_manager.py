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
    VALID_PRIORITIES = {1, 2, 3}
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

    def _validate_field(self, field: str, value: object) -> object:
        """对单个字段做类型/枚举/取值校验，返回（可能已强制转换的）值。"""
        if field == "title":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("title must be a non-empty str")
            return value
        if field == "due_time":
            if not isinstance(value, datetime):
                raise TypeError("due_time must be datetime")
            return value
        if field == "course_id":
            if value is not None and not self._is_int(value):
                raise TypeError("course_id must be int or None")
            return value
        if field == "related_exam_id":
            if value is not None and not self._is_int(value):
                raise TypeError("related_exam_id must be int or None")
            return value
        if field == "description":
            if not isinstance(value, str):
                raise TypeError("description must be str")
            return value
        if field == "estimated_hours":
            return self._coerce_hours(value)
        if field == "status":
            if not isinstance(value, str):
                raise TypeError("status must be str")
            if value not in self.VALID_STATUSES:
                raise ValueError(
                    f"status must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
                )
            return value
        if field == "priority":
            if not self._is_int(value):
                raise TypeError("priority must be int")
            if value not in self.VALID_PRIORITIES:
                raise ValueError("priority must be 1, 2, or 3")
            return value
        if field == "external_id":
            if value is not None and not isinstance(value, str):
                raise TypeError("external_id must be str or None")
            return value
        if field == "raw_payload":
            if not isinstance(value, str):
                raise TypeError("raw_payload must be str")
            return value
        raise ValueError(f"unknown field: {field}")

    # ─── 增 ────────────────────────────────────────────────────

    def create_task(self, data: dict) -> int:
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        if "title" not in data:
            raise ValueError("title is required")
        if "due_time" not in data:
            raise ValueError("due_time is required")

        unknown = set(data) - self.UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"unknown or read-only fields: {', '.join(sorted(unknown))}")

        validated = {f: self._validate_field(f, v) for f, v in data.items()}

        now = datetime.now()
        task = Task(
            title=validated["title"],
            due_time=validated["due_time"],
            course_id=validated.get("course_id"),
            related_exam_id=validated.get("related_exam_id"),
            description=validated.get("description", ""),
            estimated_hours=validated.get("estimated_hours", 1.0),
            status=validated.get("status", "todo"),
            priority=validated.get("priority", 2),
            source="manual",
            user_modified=False,
            external_id=validated.get("external_id"),
            created_at=now,
            updated_at=now,
            raw_payload=validated.get("raw_payload", ""),
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
        # Done tasks sorted to the bottom; within each group sort by the requested key
        tasks.sort(key=lambda t: (t.status == "done", getattr(t, order_by)))

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

        validated = {f: self._validate_field(f, v) for f, v in data.items()}

        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")

        for field, value in validated.items():
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
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        if task.source == "sync":
            # Soft-delete: keep the row so re-sync won't re-import it
            if not self.task_repository.soft_delete(task_id):
                raise ValueError(f"task {task_id} not found")
        else:
            if not self.task_repository.delete(task_id):
                raise ValueError(f"task {task_id} not found")

    def purge_overdue_tasks(self) -> int:
        """清理所有未完成且已逾期的可见任务，返回清理数量。"""
        now = datetime.now()
        overdue = [
            t for t in self.task_repository.list_all()
            if t.due_time < now and t.status != "done"
        ]
        count = 0
        for task in overdue:
            if task.source == "sync":
                self.task_repository.soft_delete(task.id)
            else:
                self.task_repository.delete(task.id)
            count += 1
        return count
