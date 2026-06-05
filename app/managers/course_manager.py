"""Business-facing course queries."""
from __future__ import annotations

from app.models.course import Course


class CourseManager:
    def __init__(self, course_repository) -> None:
        self.course_repository = course_repository

    def list_courses(self) -> list[Course]:
        return self.course_repository.list_all()

    def get_course(self, course_id: int) -> Course | None:
        if not isinstance(course_id, int) or isinstance(course_id, bool):
            raise TypeError("course_id must be int")
        return self.course_repository.get_by_id(course_id)
