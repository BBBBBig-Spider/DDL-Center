"""app/repositories/exam_repository.py"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.exam import Exam


class ExamRepository:
    """exams 表的增删改查。
    提供 add / get_by_id / list_all / list_by_course / update / delete / find_by_external_id。
    """

    VALID_EXAM_TYPES = {"midterm", "final", "quiz", "other"}
    VALID_SOURCES = {"manual", "sync"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_exam(self, exam: Exam, *, require_id: bool = False) -> None:
        if not isinstance(exam, Exam):
            raise TypeError("exam must be an Exam")

        if require_id and exam.id is None:
            raise ValueError("exam.id is required")

        if exam.id is not None and not self._is_int(exam.id):
            raise TypeError("exam.id must be int or None")

        if not isinstance(exam.name, str) or not exam.name.strip():
            raise ValueError("exam.name cannot be empty")

        if exam.course_id is not None and not self._is_int(exam.course_id):
            raise TypeError("exam.course_id must be int or None")

        if not isinstance(exam.start_time, datetime):
            raise TypeError("exam.start_time must be datetime")

        if not isinstance(exam.end_time, datetime):
            raise TypeError("exam.end_time must be datetime")

        if exam.end_time <= exam.start_time:
            raise ValueError("exam.end_time must be after exam.start_time")

        if not isinstance(exam.location, str):
            raise TypeError("exam.location must be str")

        if not isinstance(exam.seat, str):
            raise TypeError("exam.seat must be str")

        if not isinstance(exam.exam_type, str):
            raise TypeError("exam.exam_type must be str")

        if exam.exam_type not in self.VALID_EXAM_TYPES:
            raise ValueError(
                f"exam.exam_type must be one of: {', '.join(sorted(self.VALID_EXAM_TYPES))}"
            )

        if not isinstance(exam.source, str):
            raise TypeError("exam.source must be str")

        if exam.source not in self.VALID_SOURCES:
            raise ValueError(
                f"exam.source must be one of: {', '.join(sorted(self.VALID_SOURCES))}"
            )

        if exam.external_id is not None and not isinstance(exam.external_id, str):
            raise TypeError("exam.external_id must be str or None")

        if not isinstance(exam.raw_payload, str):
            raise TypeError("exam.raw_payload must be str")

    def _row_to_exam(self, row) -> Exam:
        return Exam(
            id=row["id"],
            course_id=row["course_id"],
            name=row["name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]),
            location=row["location"],
            seat=row["seat"],
            exam_type=row["exam_type"],
            source=row["source"],
            external_id=row["external_id"],
            raw_payload=row["raw_payload"],
        )

    # ─── 增 ────────────────────────────────────────────────────

    def add(self, exam: Exam) -> int:
        """插入一条考试记录，返回新记录的 id，并把 id 回写到入参对象。"""
        self._validate_exam(exam)
        if exam.id is not None:
            raise ValueError("exam.id must be None for add(); use update() instead")
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO exams (
                    course_id,
                    name,
                    start_time,
                    end_time,
                    location,
                    seat,
                    exam_type,
                    source,
                    external_id,
                    raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exam.course_id,
                    exam.name,
                    exam.start_time.isoformat(),
                    exam.end_time.isoformat(),
                    exam.location,
                    exam.seat,
                    exam.exam_type,
                    exam.source,
                    exam.external_id,
                    exam.raw_payload,
                ),
            )

        exam.id = cursor.lastrowid
        return cursor.lastrowid

    # ─── 查单个 ────────────────────────────────────────────────

    def get_by_id(self, exam_id: int) -> Optional[Exam]:
        """根据 id 查询考试，找不到返回 None。"""
        if not self._is_int(exam_id):
            raise TypeError("exam_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM exams
            WHERE id = ?
            """,
            (exam_id,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_exam(row)

    # ─── 查全部 ────────────────────────────────────────────────

    def list_all(self) -> List[Exam]:
        """返回所有考试，按开始时间升序排列。"""
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM exams
            ORDER BY start_time ASC
            """
        )
        return [self._row_to_exam(row) for row in cursor.fetchall()]

    # ─── 按 course 查 ─────────────────────────────────────────

    def list_by_course(self, course_id: int) -> List[Exam]:
        """按课程筛选考试，按开始时间升序排列。"""
        if not self._is_int(course_id):
            raise TypeError("course_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM exams
            WHERE course_id = ?
            ORDER BY start_time ASC
            """,
            (course_id,),
        )
        return [self._row_to_exam(row) for row in cursor.fetchall()]

    # ─── 改 ────────────────────────────────────────────────────

    def update(self, exam: Exam) -> bool:
        """根据 exam.id 更新整条记录。返回 True 表示更新成功。"""
        self._validate_exam(exam, require_id=True)
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE exams
                SET
                    course_id = ?,
                    name = ?,
                    start_time = ?,
                    end_time = ?,
                    location = ?,
                    seat = ?,
                    exam_type = ?,
                    source = ?,
                    external_id = ?,
                    raw_payload = ?
                WHERE id = ?
                """,
                (
                    exam.course_id,
                    exam.name,
                    exam.start_time.isoformat(),
                    exam.end_time.isoformat(),
                    exam.location,
                    exam.seat,
                    exam.exam_type,
                    exam.source,
                    exam.external_id,
                    exam.raw_payload,
                    exam.id,
                ),
            )

        return cursor.rowcount > 0

    # ─── 删 ────────────────────────────────────────────────────

    def delete(self, exam_id: int) -> bool:
        """根据 id 删除考试。返回 True 表示删除成功。"""
        if not self._is_int(exam_id):
            raise TypeError("exam_id must be int")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM exams
                WHERE id = ?
                """,
                (exam_id,),
            )

        return cursor.rowcount > 0

    # ─── 按 external_id 查 ────────────────────────────────────

    def find_by_external_id(self, external_id: str) -> Optional[Exam]:
        """根据教学网考试 ID 查询，找不到返回 None。同步流程使用。
        只匹配 source='sync' 的记录，避免 manual 行误用 external_id 命中。"""
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM exams
            WHERE external_id = ? AND source = 'sync'
            """,
            (external_id,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_exam(row)
