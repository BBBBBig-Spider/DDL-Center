"""Smoke tests for the repository-layer changes:

1. DatabaseManager.get_connection() works across threads (check_same_thread=False).
2. add() writes back lastrowid to the input object's .id field.
3. add() rejects objects whose .id is already set.
4. AlertRepository.update() modifies fields but does NOT touch created_at.
"""
from __future__ import annotations

import threading
from datetime import datetime

import pytest

from app.database.database_manager import DatabaseManager
from app.models.alert import Alert
from app.models.course import Course
from app.models.task import Task
from app.repositories.alert_repository import AlertRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.task_repository import TaskRepository


@pytest.fixture
def db_manager() -> DatabaseManager:
    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        yield db
    finally:
        db.close()


# ─── 1. DatabaseManager 跨线程访问 ──────────────────────────────────────

def test_connection_is_usable_from_another_thread(db_manager: DatabaseManager) -> None:
    """check_same_thread=False 让 QThread / 同步线程能复用主连接。"""
    repo = TaskRepository(db_manager)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            repo.add(Task(title="from-thread", due_time=datetime(2026, 5, 20, 12, 0)))
        except BaseException as exc:  # noqa: BLE001 - re-raise after join
            errors.append(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert errors == [], f"cross-thread access raised: {errors!r}"
    assert len(repo.list_all()) == 1


# ─── 2 & 3. add() 写回 id + 拒绝已带 id 的对象 ─────────────────────────

def test_task_add_writes_back_id_and_rejects_preset_id(db_manager: DatabaseManager) -> None:
    repo = TaskRepository(db_manager)
    task = Task(title="hello", due_time=datetime(2026, 5, 20, 12, 0))

    assert task.id is None
    returned_id = repo.add(task)

    assert task.id == returned_id, "add() 必须把 lastrowid 回写到入参 task.id"
    assert task.id is not None
    assert repo.get_by_id(task.id) is not None

    with pytest.raises(ValueError, match="task.id must be None"):
        repo.add(task)  # 已经带 id，应该被拒绝


def test_course_add_writes_back_id_and_rejects_preset_id(db_manager: DatabaseManager) -> None:
    repo = CourseRepository(db_manager)
    course = Course(name="Algorithms")

    assert course.id is None
    returned_id = repo.add(course)

    assert course.id == returned_id
    assert repo.get_by_id(course.id) is not None

    with pytest.raises(ValueError, match="course.id must be None"):
        repo.add(course)


def test_alert_add_writes_back_id_and_rejects_preset_id(db_manager: DatabaseManager) -> None:
    # 先建一个 task 作为 alert.task_id 的外键目标
    task_repo = TaskRepository(db_manager)
    task_id = task_repo.add(Task(title="for-alert", due_time=datetime(2026, 5, 20, 12, 0)))

    alert_repo = AlertRepository(db_manager)
    alert = Alert(
        level="warning",
        kind="deadline",
        message="due soon",
        task_id=task_id,
        target_type="task",
    )

    assert alert.id is None
    returned_id = alert_repo.add(alert)

    assert alert.id == returned_id

    with pytest.raises(ValueError, match="alert.id must be None"):
        alert_repo.add(alert)


# ─── 4. AlertRepository.update() ───────────────────────────────────────

def test_alert_update_changes_fields_but_preserves_created_at(
    db_manager: DatabaseManager,
) -> None:
    task_repo = TaskRepository(db_manager)
    task_id = task_repo.add(Task(title="for-alert", due_time=datetime(2026, 5, 20, 12, 0)))

    alert_repo = AlertRepository(db_manager)
    original_created_at = datetime(2026, 5, 1, 9, 0, 0)
    alert = Alert(
        level="info",
        kind="deadline",
        message="initial",
        task_id=task_id,
        target_type="task",
        created_at=original_created_at,
        is_read=False,
    )
    alert_repo.add(alert)

    # 故意把 created_at 改坏，验证 update 不会写它
    alert.level = "urgent"
    alert.message = "updated message"
    alert.is_read = True
    alert.created_at = datetime(2099, 1, 1, 0, 0, 0)  # update 应当忽略

    assert alert_repo.update(alert) is True

    fetched = next(a for a in alert_repo.list_all() if a.id == alert.id)
    assert fetched.level == "urgent"
    assert fetched.message == "updated message"
    assert fetched.is_read is True
    assert fetched.created_at == original_created_at, "update() 不应修改 created_at"


def test_alert_update_requires_id(db_manager: DatabaseManager) -> None:
    alert_repo = AlertRepository(db_manager)
    alert = Alert(level="info", kind="deadline", message="x", task_id=None, target_type="global")

    with pytest.raises(ValueError):
        alert_repo.update(alert)


def test_alert_update_returns_false_for_missing_row(db_manager: DatabaseManager) -> None:
    alert_repo = AlertRepository(db_manager)
    alert = Alert(
        id=99999,
        level="info",
        kind="deadline",
        message="ghost",
        task_id=None,
        target_type="global",
    )

    assert alert_repo.update(alert) is False
