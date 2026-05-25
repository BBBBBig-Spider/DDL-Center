"""tests/test_alert_manager.py — Day 14 端到端测试。
按架构 line 1011-1016 测 4 个纯函数。"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.config import (
    ALERT_DAYS_URGENT,
    ALERT_DAYS_WARNING,
    CLOSE_DEADLINE_HOURS,
    OVERLOAD_THRESHOLD,
)
from app.managers.alert_manager import AlertManager
from app.models.task import Task


NOW = datetime(2026, 5, 25, 12, 0, 0)


def _task(title: str, due: datetime, status: str = "todo", tid: int = 1) -> Task:
    return Task(id=tid, title=title, due_time=due, status=status)


# ─── generate_deadline_alerts ─────────────────────────────────────

def test_overdue_yields_overdue_alert() -> None:
    am = AlertManager()
    alerts = am.generate_deadline_alerts(
        [_task("late", NOW - timedelta(days=2))], NOW
    )
    assert len(alerts) == 1
    assert alerts[0].level == "overdue"
    assert alerts[0].kind == "deadline"
    assert alerts[0].target_type == "task"


def test_within_urgent_window_yields_urgent() -> None:
    am = AlertManager()
    alerts = am.generate_deadline_alerts(
        [_task("soon", NOW + timedelta(hours=12))], NOW
    )
    assert [a.level for a in alerts] == ["urgent"]


def test_within_warning_window_yields_warning() -> None:
    am = AlertManager()
    due = NOW + timedelta(days=ALERT_DAYS_URGENT + 1)
    assert due <= NOW + timedelta(days=ALERT_DAYS_WARNING)
    alerts = am.generate_deadline_alerts([_task("mid", due)], NOW)
    assert [a.level for a in alerts] == ["warning"]


def test_far_future_no_alert() -> None:
    am = AlertManager()
    alerts = am.generate_deadline_alerts(
        [_task("far", NOW + timedelta(days=ALERT_DAYS_WARNING + 5))], NOW
    )
    assert alerts == []


def test_done_task_no_alert() -> None:
    am = AlertManager()
    alerts = am.generate_deadline_alerts(
        [_task("finished", NOW - timedelta(days=1), status="done")], NOW
    )
    assert alerts == []


def test_deadline_alerts_carry_task_id() -> None:
    am = AlertManager()
    alerts = am.generate_deadline_alerts(
        [_task("late", NOW - timedelta(days=2), tid=42)], NOW
    )
    assert alerts[0].task_id == 42


# ─── detect_same_day_overload ────────────────────────────────────

def test_overload_triggers_at_threshold() -> None:
    am = AlertManager()
    day = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [_task(f"t{i}", day.replace(hour=8 + i), tid=i + 1)
             for i in range(OVERLOAD_THRESHOLD)]

    alerts = am.detect_same_day_overload(tasks)

    assert len(alerts) == 1
    assert alerts[0].kind == "overload"
    assert alerts[0].target_type == "day"
    assert alerts[0].task_id is None
    assert str(OVERLOAD_THRESHOLD) in alerts[0].message


def test_overload_skipped_below_threshold() -> None:
    am = AlertManager()
    day = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [_task(f"t{i}", day.replace(hour=8 + i), tid=i + 1)
             for i in range(OVERLOAD_THRESHOLD - 1)]

    assert am.detect_same_day_overload(tasks) == []


def test_overload_ignores_done_tasks() -> None:
    am = AlertManager()
    day = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [_task(f"t{i}", day.replace(hour=8 + i), status="done", tid=i + 1)
             for i in range(OVERLOAD_THRESHOLD)]

    assert am.detect_same_day_overload(tasks) == []


# ─── detect_close_deadlines ───────────────────────────────────────

def test_close_pair_yields_two_warnings() -> None:
    am = AlertManager()
    base = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [
        _task("a", base, tid=1),
        _task("b", base + timedelta(hours=CLOSE_DEADLINE_HOURS - 1), tid=2),
    ]

    alerts = am.detect_close_deadlines(tasks)

    assert len(alerts) == 2
    assert {a.task_id for a in alerts} == {1, 2}
    assert all(a.kind == "deadline" and a.level == "warning" for a in alerts)


def test_far_apart_pair_no_alert() -> None:
    am = AlertManager()
    base = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [
        _task("a", base, tid=1),
        _task("b", base + timedelta(hours=CLOSE_DEADLINE_HOURS + 1), tid=2),
    ]

    assert am.detect_close_deadlines(tasks) == []


def test_close_deadlines_ignores_done() -> None:
    am = AlertManager()
    base = NOW + timedelta(days=ALERT_DAYS_WARNING + 5)
    tasks = [
        _task("a", base, status="done", tid=1),
        _task("b", base + timedelta(hours=1), tid=2),
    ]
    assert am.detect_close_deadlines(tasks) == []


# ─── generate_progress_alert ─────────────────────────────────────

def test_progress_alert_when_completion_rate_low() -> None:
    am = AlertManager()
    stats = SimpleNamespace(completion_rate=0.2)
    alerts = am.generate_progress_alert(stats)

    assert len(alerts) == 1
    assert alerts[0].kind == "progress"
    assert alerts[0].target_type == "global"


def test_progress_alert_skipped_when_rate_ok() -> None:
    am = AlertManager()
    stats = SimpleNamespace(completion_rate=0.9)
    assert am.generate_progress_alert(stats) == []


def test_progress_alert_skipped_when_missing_attr() -> None:
    am = AlertManager()
    assert am.generate_progress_alert(SimpleNamespace()) == []


# ─── AppFacade 编排：拉 task → 跑 3 类 → 持久化 ──────────────────

def test_app_facade_generate_alerts_persists_results() -> None:
    from app.database.database_manager import DatabaseManager
    from app.managers.app_facade import AppFacade
    from app.managers.task_manager import TaskManager
    from app.repositories.alert_repository import AlertRepository
    from app.repositories.task_repository import TaskRepository

    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        task_repo = TaskRepository(db)
        alert_repo = AlertRepository(db)
        facade = AppFacade(
            task_manager=TaskManager(task_repo),
            alert_manager=AlertManager(
                task_repository=task_repo,
                alert_repository=alert_repo,
            ),
        )

        facade.create_task({"title": "soon", "due_time": datetime.now() + timedelta(hours=12)})
        produced = facade.generate_alerts()

        assert len(produced) >= 1
        assert len(alert_repo.list_all()) == len(produced)
    finally:
        db.close()


def test_generate_alerts_is_idempotent() -> None:
    from app.database.database_manager import DatabaseManager
    from app.managers.task_manager import TaskManager
    from app.repositories.alert_repository import AlertRepository
    from app.repositories.task_repository import TaskRepository

    db = DatabaseManager(":memory:")
    db.initialize_database()
    try:
        task_repo = TaskRepository(db)
        alert_repo = AlertRepository(db)
        tm = TaskManager(task_repo)
        am = AlertManager(task_repository=task_repo, alert_repository=alert_repo)

        tm.create_task({"title": "soon", "due_time": datetime.now() + timedelta(hours=12)})

        first = am.generate_alerts()
        second = am.generate_alerts()

        assert len(first) >= 1
        assert second == []
        assert len(alert_repo.list_all()) == len(first)
    finally:
        db.close()
