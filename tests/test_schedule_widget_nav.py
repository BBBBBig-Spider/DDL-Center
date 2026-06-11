"""tests/test_schedule_widget_nav.py — 课程表上一周/下一周快捷按钮测试。"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class StubFacade:
    """A no-op facade exposing every method ScheduleWidget may call."""

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


def _make_widget(qapp):
    from app.gui.schedule_widget import ScheduleWidget
    return ScheduleWidget(StubFacade())


def test_prev_button_disabled_at_week_1(qapp):
    w = _make_widget(qapp)
    w.week_combo.setCurrentIndex(0)
    assert not w.prev_week_button.isEnabled()
    assert w.next_week_button.isEnabled()


def test_next_button_disabled_at_last_week(qapp):
    w = _make_widget(qapp)
    last = w.week_combo.count() - 1
    w.week_combo.setCurrentIndex(last)
    assert w.prev_week_button.isEnabled()
    assert not w.next_week_button.isEnabled()


def test_clicking_next_advances_week(qapp):
    w = _make_widget(qapp)
    w.week_combo.setCurrentIndex(0)
    w.next_week_button.click()
    assert w.week_combo.currentIndex() == 1


def test_clicking_prev_goes_back(qapp):
    w = _make_widget(qapp)
    w.week_combo.setCurrentIndex(3)
    w.prev_week_button.click()
    assert w.week_combo.currentIndex() == 2


def test_both_buttons_enabled_in_middle(qapp):
    w = _make_widget(qapp)
    w.week_combo.setCurrentIndex(5)
    assert w.prev_week_button.isEnabled()
    assert w.next_week_button.isEnabled()
