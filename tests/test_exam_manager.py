from datetime import datetime

from app.database.database_manager import DatabaseManager
from app.managers.exam_manager import ExamManager
from app.repositories.exam_repository import ExamRepository


def test_create_exam_adds_and_updates_by_external_id():
    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        manager = ExamManager(ExamRepository(db))
        payload = {
            "name": "高等数学考试",
            "start_time": "2026-06-20 09:00",
            "end_time": "2026-06-20 11:00",
            "location": "理教303",
            "exam_type": "final",
            "external_id": "portal-exam-1",
        }

        first_id = manager.create_exam(payload)
        second_id = manager.create_exam({**payload, "location": "理教305"})
        exams = manager.list_exams()

        assert second_id == first_id
        assert len(exams) == 1
        assert exams[0].start_time == datetime(2026, 6, 20, 9, 0)
        assert exams[0].location == "理教305"
    finally:
        db.close()
