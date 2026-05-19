"""app/repositories/course_repository.py"""
from __future__ import annotations
from typing import List, Optional
from app.models.course import Course


class CourseRepository:
    """courses 表的增删改查。"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

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
        """插入一门课程，返回新记录的 id。"""
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
        """根据 id 查询课程，找不到返回 None。"""
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
        if course.id is None:
            raise ValueError("无法更新没有 id 的课程")

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
