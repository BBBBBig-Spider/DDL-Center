"""Day 9 endpoint test: TaskManager."""
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


def _due(days: int) -> datetime:
    return datetime.now() + timedelta(days=days)


# ─── create_task ───────────────────────────────────────────────────

def test_create_task_returns_id_and_persists(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "review notes", "due_time": _due(1)})
    fetched = manager.get_task(task_id)

    assert fetched is not None
    assert fetched.id == task_id
    assert fetched.title == "review notes"
    assert fetched.source == "manual"
    assert fetched.user_modified is False


def test_create_task_rejects_missing_required_fields(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="title is required"):
        manager.create_task({"due_time": _due(1)})

    with pytest.raises(ValueError, match="due_time is required"):
        manager.create_task({"title": "x"})


def test_create_task_rejects_unknown_field(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="unknown task fields"):
        manager.create_task({"title": "x", "due_time": _due(1), "secret_field": 42})


def test_create_task_accepts_optional_fields(manager: TaskManager) -> None:
    task_id = manager.create_task(
        {
            "title": "hw1",
            "due_time": _due(2),
            "description": "do exercises",
            "estimated_hours": 2.5,
            "priority": 1,
        }
    )
    task = manager.get_task(task_id)
    assert task is not None
    assert task.description == "do exercises"
    assert task.estimated_hours == 2.5
    assert task.priority == 1


# ─── update_task ───────────────────────────────────────────────────

def test_update_task_modifies_fields_and_flags_user_modified(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "old", "due_time": _due(1)})

    manager.update_task(task_id, {"title": "new"})

    task = manager.get_task(task_id)
    assert task is not None
    assert task.title == "new"
    assert task.user_modified is True


def test_update_task_raises_for_missing_id(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="not found"):
        manager.update_task(99999, {"title": "x"})


def test_update_task_rejects_unknown_field(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    with pytest.raises(ValueError, match="unknown task fields"):
        manager.update_task(task_id, {"unknown": 1})


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

    ids = [t.id for t in manager.list_tasks()]
    assert ids == [sooner, later]


def test_list_tasks_filters_by_status(manager: TaskManager) -> None:
    a = manager.create_task({"title": "a", "due_time": _due(1)})
    b = manager.create_task({"title": "b", "due_time": _due(2), "status": "doing"})

    rows = manager.list_tasks({"status": "doing"})
    assert [t.id for t in rows] == [b]

    rows = manager.list_tasks({"status": "todo"})
    assert [t.id for t in rows] == [a]


def test_list_tasks_filter_due_before(manager: TaskManager) -> None:
    near = manager.create_task({"title": "near", "due_time": _due(1)})
    far = manager.create_task({"title": "far", "due_time": _due(10)})

    rows = manager.list_tasks({"due_before": _due(3)})
    assert [t.id for t in rows] == [near]
    assert far not in [t.id for t in rows]


def test_list_tasks_filter_include_done_false(manager: TaskManager) -> None:
    a = manager.create_task({"title": "a", "due_time": _due(1)})
    b = manager.create_task({"title": "b", "due_time": _due(2)})
    manager.mark_done(a)

    rows = manager.list_tasks({"include_done": False})
    assert [t.id for t in rows] == [b]


def test_list_tasks_unknown_filter_raises(manager: TaskManager) -> None:
    with pytest.raises(ValueError, match="unknown filter keys"):
        manager.list_tasks({"banana": 1})


# ─── mark_done / reopen ────────────────────────────────────────────

def test_mark_done_sets_status_and_completed_at(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    manager.mark_done(task_id)
    task = manager.get_task(task_id)

    assert task is not None
    assert task.is_done()
    assert task.completed_at is not None


def test_reopen_clears_completed_at(manager: TaskManager) -> None:
    task_id = manager.create_task({"title": "x", "due_time": _due(1)})
    manager.mark_done(task_id)
    manager.reopen(task_id)
    task = manager.get_task(task_id)

    assert task is not None
    assert task.status == "todo"
    assert task.completed_at is None


# ─── convenience listings ─────────────────────────────────────────

def test_list_by_course_and_list_by_status(manager_with_courses) -> None:
    manager, cid1, cid2 = manager_with_courses
    a = manager.create_task({"title": "a", "due_time": _due(1), "course_id": cid1})
    b = manager.create_task({"title": "b", "due_time": _due(2), "course_id": cid2})
    c = manager.create_task({"title": "c", "due_time": _due(3), "course_id": cid1, "status": "doing"})

    course1 = sorted(t.id for t in manager.list_by_course(cid1))
    assert course1 == sorted([a, c])

    doing = [t.id for t in manager.list_by_status("doing")]
    assert doing == [c]
