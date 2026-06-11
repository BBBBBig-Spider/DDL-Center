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


def test_now_line_hidden_when_outside_class_hours(qapp, monkeypatch):
    w = _make_widget(qapp)
    # PERIODS first start ≈ 08:00 — pin "now" to 03:00 (well before).
    fake_now = datetime.combine(date.today(), time(3, 0))

    class _FakeDatetime:
        @staticmethod
        def now():
            return fake_now

    monkeypatch.setattr("app.gui.schedule_widget.datetime", _FakeDatetime)
    w._update_now_line()
    # After update with out-of-range time → indicator is hidden (or never created).
    if w._now_line is not None:
        assert not w._now_line.isVisible()
    if w._now_label is not None:
        assert not w._now_label.isVisible()


def test_now_line_hidden_when_not_current_week(qapp):
    w = _make_widget(qapp)
    real = w._current_semester_week()
    # Force a different week.
    w.current_week = real + 5 if real + 5 <= w._total_weeks else max(1, real - 5)
    w._update_now_line()
    if w._now_line is not None:
        assert not w._now_line.isVisible()


# ---------- live color update ----------


def test_set_now_line_color_accepts_valid_hex(qapp):
    w = _make_widget(qapp)
    # Should not raise on a valid hex.
    w.set_now_line_color("#FF8800")


def test_set_now_line_color_ignores_garbage(qapp):
    w = _make_widget(qapp)
    # Should not raise on bogus input.
    w.set_now_line_color("garbage")
    w.set_now_line_color(None)  # type: ignore[arg-type]


# ---------- timer wiring ----------


def test_timer_is_active_and_5min(qapp):
    w = _make_widget(qapp)
    assert w._now_line_timer.isActive()
    assert w._now_line_timer.interval() == 5 * 60 * 1000
