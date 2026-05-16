from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.task import Task


class TaskRepository:
    """CRUD access for rows in the tasks table."""

    VALID_STATUSES = {"todo", "doing", "done", "blocked"}
    VALID_PRIORITIES = {1, 2, 3}
    VALID_SOURCES = {"manual", "sync"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_task(self, task: Task, *, require_id: bool = False) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be a Task")

        if require_id and task.id is None:
            raise ValueError("task.id is required")

        if task.id is not None and not self._is_int(task.id):
            raise TypeError("task.id must be int or None")

        if not isinstance(task.title, str) or not task.title.strip():
            raise ValueError("task.title cannot be empty")

        if task.course_id is not None and not self._is_int(task.course_id):
            raise TypeError("task.course_id must be int or None")

        if task.related_exam_id is not None and not self._is_int(task.related_exam_id):
            raise TypeError("task.related_exam_id must be int or None")

        if not isinstance(task.description, str):
            raise TypeError("task.description must be str")

        if not isinstance(task.due_time, datetime):
            raise TypeError("task.due_time must be datetime")

        if not isinstance(task.estimated_hours, (int, float)) or isinstance(
            task.estimated_hours, bool
        ):
            raise TypeError("task.estimated_hours must be a number")

        if task.estimated_hours < 0:
            raise ValueError("task.estimated_hours cannot be negative")

        if not isinstance(task.status, str):
            raise TypeError("task.status must be str")

        if task.status not in self.VALID_STATUSES:
            raise ValueError(
                f"task.status must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

        if not self._is_int(task.priority):
            raise TypeError("task.priority must be int")

        if task.priority not in self.VALID_PRIORITIES:
            raise ValueError("task.priority must be one of: 1, 2, 3")

        if not isinstance(task.source, str):
            raise TypeError("task.source must be str")

        if task.source not in self.VALID_SOURCES:
            raise ValueError(
                f"task.source must be one of: {', '.join(sorted(self.VALID_SOURCES))}"
            )

        if not isinstance(task.user_modified, bool):
            raise TypeError("task.user_modified must be bool")

        if task.external_id is not None and not isinstance(task.external_id, str):
            raise TypeError("task.external_id must be str or None")

        if not isinstance(task.created_at, datetime):
            raise TypeError("task.created_at must be datetime")

        if not isinstance(task.updated_at, datetime):
            raise TypeError("task.updated_at must be datetime")

        if task.completed_at is not None and not isinstance(task.completed_at, datetime):
            raise TypeError("task.completed_at must be datetime or None")

        if not isinstance(task.raw_payload, str):
            raise TypeError("task.raw_payload must be str")

    def _validate_status(self, status: str) -> None:
        if not isinstance(status, str):
            raise TypeError("status must be str")

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

    def _validate_course_id(self, course_id: int) -> None:
        if not self._is_int(course_id):
            raise TypeError("course_id must be int")

    @staticmethod
    def _validate_deadline(deadline: datetime) -> None:
        if not isinstance(deadline, datetime):
            raise TypeError("deadline must be datetime")

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            course_id=row["course_id"],
            related_exam_id=row["related_exam_id"],
            description=row["description"] or "",
            due_time=datetime.fromisoformat(row["due_time"]),
            estimated_hours=row["estimated_hours"],
            status=row["status"],
            priority=row["priority"],
            source=row["source"],
            user_modified=bool(row["user_modified"]),
            external_id=row["external_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            raw_payload=row["raw_payload"] or "",
        )

    def add(self, task: Task) -> int:
        """Insert a task and return its generated id."""
        self._validate_task(task)
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    title,
                    course_id,
                    related_exam_id,
                    description,
                    due_time,
                    estimated_hours,
                    status,
                    priority,
                    source,
                    user_modified,
                    external_id,
                    created_at,
                    updated_at,
                    completed_at,
                    raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.course_id,
                    task.related_exam_id,
                    task.description,
                    task.due_time.isoformat(),
                    task.estimated_hours,
                    task.status,
                    task.priority,
                    task.source,
                    int(task.user_modified),
                    task.external_id,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.raw_payload,
                ),
            )

        return cursor.lastrowid

    def list_all(self) -> List[Task]:
        """Return all tasks ordered by due time."""
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY due_time ASC
            """
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Return a task by id, or None when it does not exist."""
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        return self._row_to_task(row) if row is not None else None

    def update(self, task: Task) -> bool:
        """Update an existing task. Return True if a row was updated."""
        self._validate_task(task, require_id=True)
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET
                    title = ?,
                    course_id = ?,
                    related_exam_id = ?,
                    description = ?,
                    due_time = ?,
                    estimated_hours = ?,
                    status = ?,
                    priority = ?,
                    source = ?,
                    user_modified = ?,
                    external_id = ?,
                    updated_at = ?,
                    completed_at = ?,
                    raw_payload = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.course_id,
                    task.related_exam_id,
                    task.description,
                    task.due_time.isoformat(),
                    task.estimated_hours,
                    task.status,
                    task.priority,
                    task.source,
                    int(task.user_modified),
                    task.external_id,
                    task.updated_at.isoformat(),
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.raw_payload,
                    task.id,
                ),
            )

        return cursor.rowcount > 0

    def delete(self, task_id: int) -> bool:
        """Delete a task by id. Return True if a row was deleted."""
        if not self._is_int(task_id):
            raise TypeError("task_id must be int")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            )

        return cursor.rowcount > 0

    def list_by_status(self, status: str) -> List[Task]:
        """Return tasks with the given status ordered by due time."""
        self._validate_status(status)
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = ?
            ORDER BY due_time ASC
            """,
            (status,),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def list_by_course(self, course_id: int) -> List[Task]:
        """Return tasks for the given course ordered by due time."""
        self._validate_course_id(course_id)
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE course_id = ?
            ORDER BY due_time ASC
            """,
            (course_id,),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def list_due_before(self, deadline: datetime) -> List[Task]:
        """Return unfinished tasks due on or before the given deadline."""
        self._validate_deadline(deadline)
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE due_time <= ? AND status != 'done'
            ORDER BY due_time ASC
            """,
            (deadline.isoformat(),),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]
