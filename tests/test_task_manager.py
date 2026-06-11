"""tests/test_task_manager.py"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.database.database_manager import DatabaseManager
from app.managers.task_manager import TaskManager
from app.models.course import Course
from app.repositories.course_repository import CourseRepository
from app.repositories.task_repository import TaskRepository


@pytest.fixture
def manager() -> TaskManager:
    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        yield TaskManager(TaskRepository(db))
    finally:
        db.close()


@pytest.fixture
def manager_with_courses():
    db = DatabaseManager(":memory:")
    db.initialize_database()
    course_repo = CourseRepository(db)
    cid1 = course_repo.add(Course(name="C1"))
    cid2 = course_repo.add(Course(name="C2"))
    try:
        yield TaskManager(TaskRepository(db)), cid1, cid2
    finally:
        db.close()


def _due(days: float) -> datetime:
    return datetime.now() + timedelta(days=days)


# ─── create_task ───────────────────────────────────────────────────

def test_create_task_returns_id_and_persists(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "review notes", "due_time": _due(1)})
    task = manager.get_task(task_id)

    assert task is not None
    assert task.id == task_id
    assert task.title == "review notes"
    assert task.source == "manual"
    assert task.user_modified is False


def test_create_task_requires_title_and_due_time(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="title is required"):
        manager.create_task({"due_time": _due(1)})
    with pytest.raises(ValueError, match="due_time is required"):
        manager.create_task({"title": "x"})


@pytest.mark.parametrize(
    "bad_value, exc",
    [
        (True, TypeError),
        ("inf", TypeError),
        (float("inf"), ValueError),
        (float("nan"), ValueError),
        (-1.0, ValueError),
    ],
)
def test_create_task_rejects_bad_estimated_hours(
    manager: TaskManager, bad_value, exc
) -> None:
    with pytest.raises(exc):
        manager.create_task(
            {"title": "x", "due_time": _due(1), "estimated_hours": bad_value}
        )


# ─── update_task ───────────────────────────────────────────────────

def test_update_task_modifies_fields_and_flags_user_modified(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "old", "due_time": _due(1)})
    manager.update_task(task_id, {"title": "new"})

    task = manager.get_task(task_id)
    assert task is not None
    assert task.title == "new"
    assert task.user_modified is True


def test_update_task_missing_id_raises(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="not found"):
        manager.update_task(99999, {"title": "x"})


def test_update_task_rejects_bad_estimated_hours(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    with pytest.raises(TypeError):
        manager.update_task(task_id, {"estimated_hours": True})
    with pytest.raises(ValueError):
        manager.update_task(task_id, {"estimated_hours": float("nan")})


def test_update_task_rejects_unknown_or_readonly_fields(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    for field in ("id", "source", "created_at", "completed_at", "user_modified", "wat"):
        with pytest.raises(ValueError, match="unknown or read-only"):
            manager.update_task(task_id, {field: "anything"})


# ─── delete_task ───────────────────────────────────────────────────

def test_delete_task_removes_it(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    manager.delete_task(task_id)
    assert manager.get_task(task_id) is None


def test_delete_task_missing_id_raises(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="not found"):
        manager.delete_task(99999)


# ─── list_tasks ────────────────────────────────────────────────────

def test_list_tasks_default_sorts_by_due_time(manager: TaskManager) -> None:
    later = manager.create_task({"title": "later", "due_time": _due(5)})
    sooner = manager.create_task({"title": "sooner", "due_time": _due(1)})

    assert [t.id for t in manager.list_tasks()] == [sooner, later]


def test_list_tasks_filter_status(manager: TaskManager) -> None:
    a = manager.create_task({"title": "a", "due_time": _due(1)})
    b = manager.create_task({"title": "b", "due_time": _due(2), "status": "doing"})

    assert [t.id for t in manager.list_tasks({"status": "doing"})] == [b]
    assert [t.id for t in manager.list_tasks({"status": "todo"})] == [a]


def test_list_tasks_filter_due_before(manager: TaskManager) -> None:
    near = manager.create_task({"title": "near", "due_time": _due(1)})
    manager.create_task({"title": "far", "due_time": _due(10)})

    rows = manager.list_tasks({"due_before": _due(3)})
    assert [t.id for t in rows] == [near]


def test_list_tasks_invalid_order_by(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="order_by"):
        manager.list_tasks({"order_by": "wat"})


def test_list_tasks_rejects_unknown_filter_key(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="unknown filter keys"):
        manager.list_tasks({"include_done": True})


def test_list_tasks_rejects_bad_status(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="status"):
        manager.list_tasks({"status": "abc"})
    with pytest.raises(TypeError):
        manager.list_tasks({"status": 1})


def test_list_tasks_rejects_bad_course_id(manager: TaskManager) -> None:
    with pytest.raises(TypeError):
        manager.list_tasks({"course_id": "1"})
    with pytest.raises(TypeError):
        manager.list_tasks({"course_id": True})


def test_list_tasks_rejects_bad_due_before(manager: TaskManager) -> None:
    with pytest.raises(TypeError):
        manager.list_tasks({"due_before": "2026-05-25"})


# ─── mark_done ─────────────────────────────────────────────────────

def test_mark_done_sets_status_and_completed_at(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    manager.mark_done(task_id)
    task = manager.get_task(task_id)

    assert task is not None
    assert task.is_done()
    assert task.completed_at is not None


# ─── 便捷查询 ─────────────────────────────────────────────────────

def test_list_by_course_and_list_by_status(manager_with_courses) -> None:
    manager, cid1, cid2 = manager_with_courses
    a = manager.create_task({"title": "a", "due_time": _due(1), "course_id": cid1})
    manager.create_task({"title": "b", "due_time": _due(2), "course_id": cid2})
    c = manager.create_task(
        {"title": "c", "due_time": _due(3), "course_id": cid1, "status": "doing"}
    )

    assert sorted(t.id for t in manager.list_by_course(cid1)) == sorted([a, c])
    assert [t.id for t in manager.list_by_status("doing")] == [c]
