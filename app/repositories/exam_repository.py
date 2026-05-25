"""app/repositories/exam_repository.py"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.exam import Exam


class ExamRepository:
    """exams 表的增删改查。"""

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

        if exam.course_id is not None and not self._is_int(exam.course_id):
            raise TypeError("exam.course_id must be int or None")

        if not isinstance(exam.name, str) or not exam.name.strip():
            raise ValueError("exam.name cannot be empty")

        if not isinstance(exam.start_time, datetime):
            raise TypeError("exam.start_time must be datetime")

        if not isinstance(exam.end_time, datetime):
            raise TypeError("exam.end_time must be datetime")

        if exam.end_time <= exam.start_time:
            raise ValueError("exam.end_time must be after exam.start_time")

        if not isinstance(exam.location, str):
            raise TypeError("exam.location must be str")

        if not isinstance(exam.exam_type, str) or exam.exam_type not in self.VALID_EXAM_TYPES:
            raise ValueError(
                f"exam.exam_type must be one of: {', '.join(sorted(self.VALID_EXAM_TYPES))}"
            )

        if not isinstance(exam.source, str) or exam.source not in self.VALID_SOURCES:
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
            exam_type=row["exam_type"],
            source=row["source"],
            external_id=row["external_id"],
            raw_payload=row["raw_payload"],
        )

    def add(self, exam: Exam) -> int:
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
                    exam_type,
                    source,
                    external_id,
                    raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exam.course_id,
                    exam.name,
                    exam.start_time.isoformat(),
                    exam.end_time.isoformat(),
                    exam.location,
                    exam.exam_type,
                    exam.source,
                    exam.external_id,
                    exam.raw_payload,
                ),
            )

        exam.id = cursor.lastrowid
        return cursor.lastrowid

    def list_all(self) -> List[Exam]:
        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            "SELECT * FROM exams ORDER BY start_time ASC"
        )
        return [self._row_to_exam(r) for r in cursor.fetchall()]

    def get_by_id(self, exam_id: int) -> Optional[Exam]:
        if not self._is_int(exam_id):
            raise TypeError("exam_id must be int")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            "SELECT * FROM exams WHERE id = ?",
            (exam_id,),
        )
        row = cursor.fetchone()
        return self._row_to_exam(row) if row else None

    def update(self, exam: Exam) -> bool:
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
                    exam.exam_type,
                    exam.source,
                    exam.external_id,
                    exam.raw_payload,
                    exam.id,
                ),
            )

        return cursor.rowcount > 0

    def delete(self, exam_id: int) -> bool:
        if not self._is_int(exam_id):
            raise TypeError("exam_id must be int")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                "DELETE FROM exams WHERE id = ?",
                (exam_id,),
            )
        return cursor.rowcount > 0

    def list_upcoming(self, now: datetime) -> List[Exam]:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM exams
            WHERE start_time >= ?
            ORDER BY start_time ASC
            """,
            (now.isoformat(),),
        )
        return [self._row_to_exam(r) for r in cursor.fetchall()]

    def list_by_course(self, course_id: int) -> List[Exam]:
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
        return [self._row_to_exam(r) for r in cursor.fetchall()]

    def find_by_external_id(self, external_id: str) -> Optional[Exam]:
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            "SELECT * FROM exams WHERE external_id = ?",
            (external_id,),
        )
        row = cursor.fetchone()
        return self._row_to_exam(row) if row else None
