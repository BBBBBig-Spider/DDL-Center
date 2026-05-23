"""app/repositories/course_repository.py"""
from __future__ import annotations

from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.course import Course


class CourseRepository:
    """courses 表的增删改查。"""

    VALID_SOURCES = {"manual", "sync"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_course(self, course: Course, *, require_id: bool = False) -> None:
        if not isinstance(course, Course):
            raise TypeError("course must be a Course")

        if require_id and course.id is None:
            raise ValueError("course.id is required")

        if course.id is not None and not self._is_int(course.id):
            raise TypeError("course.id must be int or None")

        if not isinstance(course.name, str) or not course.name.strip():
            raise ValueError("course.name cannot be empty")

        if not isinstance(course.teacher, str):
            raise TypeError("course.teacher must be str")

        if not isinstance(course.semester, str):
            raise TypeError("course.semester must be str")

        if course.external_id is not None and not isinstance(course.external_id, str):
            raise TypeError("course.external_id must be str or None")

        if not isinstance(course.color, str) or not course.color.strip():
            raise ValueError("course.color cannot be empty")

        if not isinstance(course.source, str):
            raise TypeError("course.source must be str")

        if course.source not in self.VALID_SOURCES:
            raise ValueError(
                f"course.source must be one of: {', '.join(sorted(self.VALID_SOURCES))}"
            )

        if not isinstance(course.raw_payload, str):
            raise TypeError("course.raw_payload must be str")

    def _row_to_course(self, row) -> Course:
        """把数据库的一行转成 Course 对象。"""
        return Course(
            id=row["id"],
            name=row["name"],
            teacher=row["teacher"] or "",
            semester=row["semester"] or "",
            external_id=row["external_id"],
            color=row["color"] or "#4F81BD",
            source=row["source"],
            raw_payload=row["raw_payload"] or "",
        )

    def add(self, course: Course) -> int:
        """插入一门课程，返回新记录的 id，并把 id 回写到入参对象。"""
        self._validate_course(course)
        if course.id is not None:
            raise ValueError("course.id must be None for add(); use update() instead")
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO courses (
                    name,
                    teacher,
                    semester,
                    external_id,
                    color,
                    source,
                    raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course.name,
                    course.teacher,
                    course.semester,
                    course.external_id,
                    course.color,
                    course.source,
                    course.raw_payload,
                ),
            )

        course.id = cursor.lastrowid
        return cursor.lastrowid

    def list_all(self) -> List[Course]:
        """返回所有课程，按 id 升序排列。"""
        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM courses
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()
        return [self._row_to_course(row) for row in rows]

    def get_by_id(self, course_id: int) -> Optional[Course]:
        """根据 id 查询课程。"""
        if not self._is_int(course_id):
            raise TypeError("course_id must be int")

        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM courses
            WHERE id = ?
            """,
            (course_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_course(row)

    def update(self, course: Course) -> bool:
        """
        根据 course.id 更新整条记录。
        返回 True 表示更新成功，False 表示没有找到该 id。
        """
        self._validate_course(course, require_id=True)

        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                UPDATE courses
                SET
                    name = ?,
                    teacher = ?,
                    semester = ?,
                    external_id = ?,
                    color = ?,
                    source = ?,
                    raw_payload = ?
                WHERE id = ?
                """,
                (
                    course.name,
                    course.teacher,
                    course.semester,
                    course.external_id,
                    course.color,
                    course.source,
                    course.raw_payload,
                    course.id,
                ),
            )

        return cursor.rowcount > 0

    def delete(self, course_id: int) -> bool:
        """根据 id 删除课程。返回 True 表示删除成功。"""
        if not self._is_int(course_id):
            raise TypeError("course_id must be int")

        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
                """
                DELETE FROM courses
                WHERE id = ?
                """,
                (course_id,),
            )

        return cursor.rowcount > 0

    def find_by_external_id(self, external_id: str) -> Optional[Course]:
        """根据教学网课程 ID 查询课程，找不到返回 None。同步流程使用。"""
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()

        cursor = conn.execute(
            """
            SELECT *
            FROM courses
            WHERE external_id = ?
            """,
            (external_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_course(row)
