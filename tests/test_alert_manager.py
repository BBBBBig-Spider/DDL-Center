"""Day 14 endpoint test: AlertManager."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.config import (
    ALERT_DAYS_URGENT,
    ALERT_DAYS_WARNING,
    CLOSE_DEADLINE_HOURS,
    OVERLOAD_THRESHOLD,
)
from app.database.database_manager import DatabaseManager
from app.managers.alert_manager import AlertManager
from app.models.task import Task
from app.repositories.alert_repository import AlertRepository
from app.repositories.task_repository import TaskRepository


@pytest.fixture
def env():
    db = DatabaseManager(":memory:")
    db.initialize_database()
    task_repo = TaskRepository(db)
    alert_repo = AlertRepository(db)
    manager = AlertManager(alert_repo, task_repo)
    try:
        yield manager, task_repo, alert_repo
    finally:
        db.close()


def _add_task(task_repo: TaskRepository, title: str, due: datetime, status: str = "todo") -> int:
    return task_repo.add(Task(title=title, due_time=due, status=status))


# ─── deadline alerts ──────────────────────────────────────────────

def test_overdue_task_yields_overdue_alert(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "late hw", now - timedelta(days=2))

    alerts = manager.generate_alerts(now=now)

    deadline = [a for a in alerts if a.kind == "deadline" and a.level == "overdue"]
    assert len(deadline) == 1
    assert "已逾期" in deadline[0].message


def test_urgent_task_yields_urgent_alert(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "tomorrow hw", now + timedelta(hours=12))  # within urgent window

    alerts = manager.generate_alerts(now=now)

    urgent = [a for a in alerts if a.kind == "deadline" and a.level == "urgent"]
    assert len(urgent) == 1


def test_warning_task_yields_warning_alert(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "next week", now + timedelta(days=ALERT_DAYS_WARNING - 0.5))

    alerts = manager.generate_alerts(now=now)

    warning = [
        a for a in alerts
        if a.kind == "deadline" and a.level == "warning" and a.target_type == "task"
    ]
    assert len(warning) == 1


def test_task_outside_warning_window_yields_nothing(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "far future", now + timedelta(days=ALERT_DAYS_WARNING + 5))

    alerts = manager.generate_alerts(now=now)

    assert not [a for a in alerts if a.kind == "deadline" and a.target_type == "task"]


def test_done_task_does_not_alert(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "finished", now - timedelta(days=1), status="done")

    alerts = manager.generate_alerts(now=now)

    assert alerts == []


# ─── overload ──────────────────────────────────────────────────────

def test_overload_alert_when_same_day_exceeds_threshold(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    day = now + timedelta(days=ALERT_DAYS_WARNING + 5)
    for i in range(OVERLOAD_THRESHOLD):
        _add_task(task_repo, f"t{i}", day.replace(hour=8 + i))

    alerts = manager.generate_alerts(now=now)

    overload = [a for a in alerts if a.kind == "overload"]
    assert len(overload) == 1
    assert overload[0].target_type == "day"
    assert overload[0].task_id is None


def test_no_overload_alert_below_threshold(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    day = now + timedelta(days=ALERT_DAYS_WARNING + 5)
    for i in range(OVERLOAD_THRESHOLD - 1):
        _add_task(task_repo, f"t{i}", day.replace(hour=8 + i))

    alerts = manager.generate_alerts(now=now)
    assert [a for a in alerts if a.kind == "overload"] == []


# ─── close-deadline pairs ─────────────────────────────────────────

def test_close_deadline_pair_yields_warning(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    far_base = now + timedelta(days=ALERT_DAYS_WARNING + 5)
    _add_task(task_repo, "a", far_base)
    _add_task(task_repo, "b", far_base + timedelta(hours=CLOSE_DEADLINE_HOURS - 1))

    alerts = manager.generate_alerts(now=now)

    close = [a for a in alerts if a.kind == "deadline" and "间隔不足" in a.message]
    assert len(close) == 2


def test_far_apart_pair_no_close_alert(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    base = now + timedelta(days=ALERT_DAYS_WARNING + 5)
    _add_task(task_repo, "a", base)
    _add_task(task_repo, "b", base + timedelta(hours=CLOSE_DEADLINE_HOURS + 1))

    alerts = manager.generate_alerts(now=now)

    close = [a for a in alerts if a.kind == "deadline" and "间隔不足" in a.message]
    assert close == []


# ─── idempotency ──────────────────────────────────────────────────

def test_generate_alerts_is_idempotent(env) -> None:
    manager, task_repo, alert_repo = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "soon", now + timedelta(hours=12))

    first = manager.generate_alerts(now=now)
    second = manager.generate_alerts(now=now)

    assert len(first) >= 1
    assert second == []
    assert len(alert_repo.list_all()) == len(first)


# ─── manager read-state passthrough ───────────────────────────────

def test_mark_read_and_list_unread(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "soon", now + timedelta(hours=12))

    [alert] = manager.generate_alerts(now=now)
    assert manager.list_unread() != []

    assert manager.mark_read(alert.id) is True
    assert manager.list_unread() == []


def test_mark_all_read(env) -> None:
    manager, task_repo, _ = env
    now = datetime(2026, 5, 25, 12, 0, 0)
    _add_task(task_repo, "a", now - timedelta(days=1))
    _add_task(task_repo, "b", now + timedelta(hours=12))

    manager.generate_alerts(now=now)
    n = manager.mark_all_read()

    assert n >= 2
    assert manager.list_unread() == []
