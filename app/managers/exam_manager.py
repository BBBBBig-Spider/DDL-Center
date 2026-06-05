"""Business-facing exam queries."""
from __future__ import annotations

from app.models.exam import Exam


class ExamManager:
    def __init__(self, exam_repository) -> None:
        self.exam_repository = exam_repository

    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        if course_id is None:
            return self.exam_repository.list_all()
        if not isinstance(course_id, int) or isinstance(course_id, bool):
            raise TypeError("course_id must be int or None")
        return self.exam_repository.list_by_course(course_id)

    def get_exam(self, exam_id: int) -> Exam | None:
        if not isinstance(exam_id, int) or isinstance(exam_id, bool):
            raise TypeError("exam_id must be int")
        return self.exam_repository.get_by_id(exam_id)
