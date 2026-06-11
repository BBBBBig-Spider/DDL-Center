"""tests/test_schedule_widget_now_line.py — 课程表「当前时间指示线」测试。"""
from __future__ import annotations

from datetime import date, datetime, time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class StubRepo:
    def __init__(self, data: dict | None = None) -> None:
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)


class StubFacade:
    def __init__(self, repo: StubRepo | None = None) -> None:
        self.setting_repository = repo or StubRepo()

    def list_schedule(self, *args, **kwargs):
        return []

    def list_courses(self):
        return []

    def list_exams(self):
        return []

    def list_task_arrangements(self, *args, **kwargs):
        return []

    def list_tasks(self, *args, **kwargs):
        return []

    def get_setting(self, *args, **kwargs):
        return None

    def get_semester_settings(self):
        return {"start": "2026-02-23", "total_weeks": 20}

    def get_exam_week_range(self):
        return (None, None)


def _make_widget(qapp, facade=None):
    from app.gui.schedule_widget import ScheduleWidget

    return ScheduleWidget(facade or StubFacade())


# ---------- color helpers ----------


def test_default_now_line_color_when_no_setting(qapp):
    w = _make_widget(qapp)
    assert w._get_now_line_color() == "#3B82F6"


def test_now_line_color_read_from_setting_repository(qapp):
    repo = StubRepo({"now_line_color": "#10B981"})
    w = _make_widget(qapp, StubFacade(repo))
    assert w._get_now_line_color() == "#10B981"


def test_invalid_stored_color_falls_back_to_default(qapp):
    repo = StubRepo({"now_line_color": "not-a-hex"})
    w = _make_widget(qapp, StubFacade(repo))
    assert w._get_now_line_color() == "#3B82F6"


# ---------- visibility logic ----------


def _patch_now(monkeypatch, fake_now):
    class _FakeDatetime:
        @staticmethod
        def now():
            return fake_now
    monkeypatch.setattr("app.gui.schedule_widget.datetime", _FakeDatetime)


def test_now_line_visible_after_last_period(qapp, monkeypatch):
    """At 21:31 — past the last period (ends 21:30) — the line should still
    render, clamped to the bottom of the grid. Mirrors how DDL red lines
    handle late-night deadlines like 23:59."""
    w = _make_widget(qapp)
    w.current_week = w._current_semester_week()
    _patch_now(monkeypatch, datetime.combine(date.today(), time(21, 31)))
    w.show()
    w.resize(900, 700)
    qapp.processEvents()
    w._update_now_line()
    assert w._now_line is not None
    assert w._now_line.isVisible()


def test_now_line_visible_before_first_period(qapp, monkeypatch):
    """At 03:00 — before the first period starts — the line should still
    render, clamped to the top of the grid."""
    w = _make_widget(qapp)
    w.current_week = w._current_semester_week()
    _patch_now(monkeypatch, datetime.combine(date.today(), time(3, 0)))
    w.show()
    w.resize(900, 700)
    qapp.processEvents()
    w._update_now_line()
    assert w._now_line is not None
    assert w._now_line.isVisible()


def test_now_line_renders_when_week_has_zero_tasks(qapp, monkeypatch):
    """Regression: when the current week has no tasks, _redraw_ddl_lines
    used to early-return before activating the grid layout. The now-line
    relies on that activation to compute cellRect, so it would never appear.
    With the fix, the now-line should still render even at 21:31 (past the
    last period) on a task-free week."""
    w = _make_widget(qapp)
    w.current_week = w._current_semester_week()
    _patch_now(monkeypatch, datetime.combine(date.today(), time(21, 31)))
    w.show()
    w.resize(900, 700)
    qapp.processEvents()
    # Trigger the full render pipeline (no tasks → previously returned early).
    w._redraw_ddl_lines()
    qapp.processEvents()
    assert w._now_line is not None
    assert w._now_line.isVisible()


def test_now_line_hidden_when_not_current_week(qapp):
    w = _make_widget(qapp)
    real = w._current_semester_week()
    # Force a different week.
    w.current_week = real + 5 if real + 5 <= w._total_weeks else max(1, real - 5)
    w._update_now_line()
    if w._now_line is not None:
        assert not w._now_line.isVisible()


# ---------- live color update ----------


def test_refresh_now_line_does_not_crash(qapp):
    w = _make_widget(qapp)
    # Should not raise, regardless of any payload the signal carries.
    w.refresh_now_line("#FF8800")


def test_refresh_now_line_ignores_garbage(qapp):
    w = _make_widget(qapp)
    # Should not raise on bogus payloads either — the method ignores its
    # arguments entirely (the real source of truth is setting_repository).
    w.refresh_now_line("garbage")
    w.refresh_now_line(None)
    w.refresh_now_line()


def test_refresh_now_line_picks_up_new_color_from_repo(qapp, monkeypatch):
    """Bug #3 regression: the old set_now_line_color(hex) silently ignored
    its argument and re-read the repo. Confirm the round-trip we *do*
    document — set repo, then refresh — actually paints the new color."""
    repo = StubRepo({"now_line_color": "#FF0000"})
    w = _make_widget(qapp, StubFacade(repo))
    w.current_week = w._current_semester_week()
    _patch_now(monkeypatch, datetime.combine(date.today(), time(10, 30)))
    w.show()
    w.resize(900, 700)
    qapp.processEvents()
    w.refresh_now_line()
    qapp.processEvents()
    assert w._now_line is not None
    assert "#FF0000" in w._now_line.styleSheet()


# ---------- timer wiring ----------


def test_timer_is_active_and_5min(qapp):
    w = _make_widget(qapp)
    assert w._now_line_timer.isActive()
    assert w._now_line_timer.interval() == 5 * 60 * 1000
