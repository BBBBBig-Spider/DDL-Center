"""Import schedule modes: overwrite vs merge.

These tests cover:
  1) The bug fix — repeating an import (merge mode) must NOT duplicate
     slots; the manager layer upserts on external_id.
  2) facade.clear_all_schedule_and_exams() drops both tables but leaves
     courses (and therefore tasks via course_id FK) untouched.
  3) The dialog defaults to 'overwrite'.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_db():
    from app.database.database_manager import DatabaseManager
    db = DatabaseManager(":memory:")
    db.initialize_database()
    return db


_SLOT_PAYLOAD = {
    "title": "线性代数A (II)",
    "weekday": 3,
    "start_time": "08:00",
    "end_time": "08:50",
    "location": "理教201",
    "start_week": 1,
    "end_week": 15,
    "week_type": "all",
    "slot_type": "lecture",
    "external_id": "portal:线性代数A (II):wd=3:p=1:wt=all:w=1-15",
}


def test_upsert_repeated_import_does_not_duplicate():
    """Merge mode (= no clear, just calls create_schedule_slot per item)
    relies on the new upsert behavior in schedule_manager. The same parsed
    slot, imported twice, must result in a single row — and the second
    call must overwrite the first (location change is observable)."""
    from app.repositories.schedule_repository import ScheduleRepository
    from app.managers.schedule_manager import ScheduleManager

    db = _make_db()
    try:
        repo = ScheduleRepository(db)
        mgr = ScheduleManager(repo)

        first_id = mgr.add_slot(_SLOT_PAYLOAD)
        second_id = mgr.add_slot({**_SLOT_PAYLOAD, "location": "理教305"})

        slots = repo.list_all()
        assert len(slots) == 1
        assert second_id == first_id
        assert slots[0].location == "理教305"
        # Imported slot is tagged source='sync' so find_by_external_id
        # (which restricts to source='sync') can match next time.
        assert slots[0].source == "sync"
    finally:
        db.close()


def test_manual_slot_without_external_id_still_marked_manual():
    """Slots added by hand (no external_id) keep source='manual'."""
    from app.repositories.schedule_repository import ScheduleRepository
    from app.managers.schedule_manager import ScheduleManager

    db = _make_db()
    try:
        repo = ScheduleRepository(db)
        mgr = ScheduleManager(repo)
        manual = {k: v for k, v in _SLOT_PAYLOAD.items() if k != "external_id"}
        mgr.add_slot(manual)
        slots = repo.list_all()
        assert len(slots) == 1
        assert slots[0].source == "manual"
        assert slots[0].external_id is None
    finally:
        db.close()


def test_clear_all_schedule_and_exams_drops_both_tables_and_keeps_courses():
    """The 'overwrite' button calls facade.clear_all_schedule_and_exams,
    which must wipe schedule_slots + exams but leave courses alone — tasks
    have a course_id FK, so dropping courses would orphan user tasks."""
    from app.repositories.schedule_repository import ScheduleRepository
    from app.repositories.exam_repository import ExamRepository
    from app.repositories.course_repository import CourseRepository
    from app.managers.schedule_manager import ScheduleManager
    from app.managers.exam_manager import ExamManager
    from app.managers.course_manager import CourseManager
    from app.managers.app_facade import AppFacade
    from app.models.course import Course

    db = _make_db()
    try:
        course_repo = CourseRepository(db)
        course_mgr = CourseManager(course_repo)
        # Pre-create a course so we can verify it survives the clear.
        course = Course(
            name="线性代数",
            teacher="",
            semester="",
            external_id=None,
            color="#4F81BD",
            source="manual",
            raw_payload="",
        )
        course_id = course_repo.add(course)

        sched_repo = ScheduleRepository(db)
        sched_mgr = ScheduleManager(sched_repo)
        sched_mgr.add_slot(_SLOT_PAYLOAD)

        exam_repo = ExamRepository(db)
        exam_mgr = ExamManager(exam_repo)
        exam_mgr.create_exam({
            "name": "高等数学考试",
            "start_time": "2026-06-20 09:00",
            "end_time": "2026-06-20 11:00",
            "location": "理教303",
            "exam_type": "final",
            "external_id": "portal-exam-1",
        })

        facade = AppFacade(
            task_manager=None,
            course_manager=course_mgr,
            schedule_manager=sched_mgr,
            exam_manager=exam_mgr,
        )
        result = facade.clear_all_schedule_and_exams()

        assert result["slots_deleted"] == 1
        assert result["exams_deleted"] == 1
        assert sched_repo.list_all() == []
        assert exam_repo.list_all() == []
        # Course must survive — task FK depends on it.
        assert course_repo.get_by_id(course_id) is not None
    finally:
        db.close()


def test_overwrite_radio_is_default(qapp):
    """Default mode in the dialog is 'overwrite' — user must explicitly
    opt into merge to keep old data."""
    from app.gui.import_schedule_dialog import ImportScheduleDialog

    class _StubFacade:
        def create_schedule_slot(self, *a, **kw):
            return 1

        def create_exam(self, *a, **kw):
            return 1

    dlg = ImportScheduleDialog(facade=_StubFacade())
    try:
        assert dlg.overwrite_radio.isChecked()
        assert not dlg.merge_radio.isChecked()
    finally:
        dlg.deleteLater()


def test_parser_emits_external_id_for_main_and_recitation_slots():
    """Stable hash anchor must be present on every parsed slot, so that the
    upsert path in schedule_manager can dedupe on re-import."""
    from app.parsers.portal_schedule_parser import parse_portal_import

    html = """
    <html><body><table>
      <tr>
        <td id="wed1">线性代数A (II)(主)<br>
        上课信息：1-15周 每周 理教201 教师：丁一文
        备注：习题课双周周一10~11节，教室：三教208<br>
        考试信息：20260624 星期三 上午 二教107</td>
      </tr>
    </table></body></html>
    """
    parsed = parse_portal_import(html)
    for slot in parsed["slots"]:
        ext = slot.get("external_id")
        assert isinstance(ext, str) and ext.startswith("portal:"), slot

    # Re-parsing the same HTML must produce identical external_ids
    # (stability is the whole point — that's what the upsert relies on).
    parsed2 = parse_portal_import(html)
    ids1 = sorted(s["external_id"] for s in parsed["slots"])
    ids2 = sorted(s["external_id"] for s in parsed2["slots"])
    assert ids1 == ids2
