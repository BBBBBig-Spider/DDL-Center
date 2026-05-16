"""app/repositories/task_repository.py"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from app.models.task import Task
class TaskRepository:
    """tasks 表的增删改查。"""
    def __init__(self, db_manager):
        self.db_manager = db_manager

    # ─── 私有辅助方法 ───────────────────────────────────────────

    def _row_to_task(self, row) -> Task:
        """把数据库的一行转成 Task 对象。"""
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

    # ─── 增 ────────────────────────────────────────────────────

    def add(self, task: Task) -> int:
        """插入一条任务，返回新记录的 id。"""
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

    # ─── 查全部 ────────────────────────────────────────────────

    def list_all(self) -> List[Task]:
        """返回所有任务，按截止时间升序排列。"""
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY due_time ASC
            """
        )

        rows = cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    # ─── 查单个 ────────────────────────────────────────────────

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """根据 id 查询任务，找不到返回 None。"""
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

        if row is None:
            return None

        return self._row_to_task(row)

    # ─── 改 ────────────────────────────────────────────────────

    def update(self, task: Task) -> bool:
        """
        根据 task.id 更新整条记录。
        返回 True 表示更新成功，False 表示没有找到该 id。
        """
        if task.id is None:
            raise ValueError("无法更新没有 id 的任务")

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

    # ─── 删 ────────────────────────────────────────────────────

    def delete(self, task_id: int) -> bool:
        """根据 id 删除任务。返回 True 表示删除成功。"""
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

    # ─── 扩展查询（可选，按需添加）─────────────────────────────

    def list_by_status(self, status: str) -> List[Task]:
        """按状态筛选任务。"""
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

        rows = cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    def list_by_course(self, course_id: int) -> List[Task]:
        """按课程筛选任务。"""
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

        rows = cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    def list_due_before(self, deadline: datetime) -> List[Task]:
        """查询截止时间在 deadline 之前的所有未完成任务。"""
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

        rows = cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
