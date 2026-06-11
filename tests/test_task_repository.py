from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest

from app.database.database_manager import DatabaseManager
from app.models.task import Task
from app.repositories.task_repository import TaskRepository


@pytest.fixture
def db_manager() -> Iterator[DatabaseManager]:
    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def repository(db_manager: DatabaseManager) -> TaskRepository:
    return TaskRepository(db_manager)


def test_add_and_get_by_id_round_trips_task(repository: TaskRepository) -> None:
    due_time = datetime(2026, 5, 20, 12, 0, 0)
    created_at = datetime(2026, 5, 16, 9, 0, 0)
    updated_at = datetime(2026, 5, 16, 10, 0, 0)
    completed_at = datetime(2026, 5, 16, 11, 0, 0)
    task = Task(
        title="Write report",
        due_time=due_time,
        description="Draft the weekly report",
        estimated_hours=2.5,
        status="done",
        priority=1,
        source="manual",
        user_modified=True,
        external_id="external-1",
        created_at=created_at,
        updated_at=updated_at,
        completed_at=completed_at,
        raw_payload='{"source":"test"}',
    )

    task_id = repository.add(task)
    fetched = repository.get_by_id(task_id)

    assert fetched is not None
    assert fetched.id == task_id
    assert fetched.title == task.title
    assert fetched.description == task.description
    assert fetched.due_time == due_time
    assert fetched.estimated_hours == task.estimated_hours
    assert fetched.status == "done"
    assert fetched.priority == 1
    assert fetched.user_modified is True
    assert fetched.external_id == "external-1"
    assert fetched.created_at == created_at
    assert fetched.updated_at == updated_at
    assert fetched.completed_at == completed_at
    assert fetched.raw_payload == task.raw_payload


def test_get_by_id_returns_none_for_missing_task(repository: TaskRepository) -> None:
    assert repository.get_by_id(999) is None


def test_list_all_orders_by_due_time(repository: TaskRepository) -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    repository.add(Task(title="later", due_time=now + timedelta(days=2)))
    repository.add(Task(title="earlier", due_time=now + timedelta(days=1)))

    assert [task.title for task in repository.list_all()] == ["earlier", "later"]


def test_update_existing_task(repository: TaskRepository) -> None:
    task = Task(title="before", due_time=datetime(2026, 5, 20, 12, 0, 0))
    task.id = repository.add(task)
    task.title = "after"
    task.status = "doing"
    task.estimated_hours = 3.0
    task.updated_at = datetime(2026, 5, 17, 12, 0, 0)

    assert repository.update(task) is True
    fetched = repository.get_by_id(task.id)

    assert fetched is not None
    assert fetched.title == "after"
    assert fetched.status == "doing"
    assert fetched.estimated_hours == 3.0
    assert fetched.updated_at == task.updated_at


def test_update_requires_id(repository: TaskRepository) -> None:
    task = Task(title="no id", due_time=datetime(2026, 5, 20, 12, 0, 0))

    with pytest.raises(ValueError):
        repository.update(task)


def test_update_returns_false_for_missing_task(repository: TaskRepository) -> None:
    task = Task(id=999, title="missing", due_time=datetime(2026, 5, 20, 12, 0, 0))

    assert repository.update(task) is False


def test_delete_existing_and_missing_task(repository: TaskRepository) -> None:
    task_id = repository.add(Task(title="delete me", due_time=datetime(2026, 5, 20)))

    assert repository.delete(task_id) is True
    assert repository.get_by_id(task_id) is None
    assert repository.delete(task_id) is False


def test_list_by_status(repository: TaskRepository) -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    repository.add(Task(title="todo later", due_time=now + timedelta(days=2), status="todo"))
    repository.add(Task(title="done", due_time=now + timedelta(days=1), status="done"))
    repository.add(Task(title="todo earlier", due_time=now + timedelta(hours=1), status="todo"))

    assert [task.title for task in repository.list_by_status("todo")] == [
        "todo earlier",
        "todo later",
    ]


def test_list_by_course(db_manager: DatabaseManager, repository: TaskRepository) -> None:
    conn = db_manager.get_connection()
    course_id = conn.execute("INSERT INTO courses (name) VALUES (?)", ("Math",)).lastrowid
    repository.add(Task(title="math", due_time=datetime(2026, 5, 20), course_id=course_id))
    repository.add(Task(title="uncategorized", due_time=datetime(2026, 5, 20)))

    assert [task.title for task in repository.list_by_course(course_id)] == ["math"]


def test_add_rejects_missing_foreign_key(repository: TaskRepository) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        repository.add(Task(title="bad course", due_time=datetime(2026, 5, 20), course_id=999))


@pytest.mark.parametrize(
    ("task", "error_type"),
    [
        (Task(title="", due_time=datetime(2026, 5, 20)), ValueError),
        (Task(title="bad", due_time="2026-05-20"), TypeError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), estimated_hours=-1), ValueError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), status="unknown"), ValueError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), status=1), TypeError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), priority=9), ValueError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), priority=True), TypeError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), source="api"), ValueError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), course_id=True), TypeError),
        (Task(title="bad", due_time=datetime(2026, 5, 20), related_exam_id=False), TypeError),
    ],
)
def test_add_validates_task_fields(
    repository: TaskRepository, task: Task, error_type: type[Exception]
) -> None:
    with pytest.raises(error_type):
        repository.add(task)


@pytest.mark.parametrize(
    ("method_name", "argument", "error_type"),
    [
        ("get_by_id", True, TypeError),
        ("delete", False, TypeError),
        ("list_by_status", "unknown", ValueError),
        ("list_by_status", 1, TypeError),
        ("list_by_course", True, TypeError),
        ("list_by_course", "1", TypeError),
        ("list_due_before", "2026-05-20", TypeError),
    ],
)
def test_query_methods_validate_arguments(
    repository: TaskRepository,
    method_name: str,
    argument: object,
    error_type: type[Exception],
) -> None:
    method = getattr(repository, method_name)

    with pytest.raises(error_type):
        method(argument)


def test_list_due_before_excludes_done_tasks(repository: TaskRepository) -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    repository.add(Task(title="open soon", due_time=now + timedelta(days=1), status="todo"))
    repository.add(Task(title="done soon", due_time=now + timedelta(hours=1), status="done"))
    repository.add(Task(title="open later", due_time=now + timedelta(days=5), status="todo"))

    assert [task.title for task in repository.list_due_before(now + timedelta(days=2))] == [
        "open soon"
    ]
