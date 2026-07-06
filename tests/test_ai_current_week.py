"""tests/test_ai_current_week.py — AI manager honours the user's
``semester_total_weeks`` setting instead of the old hardcoded 16.

See REVIEW.md severe #2.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.managers.ai_assistant_manager import AIAssistantManager


class _StubRepo:
    def __init__(self, data: dict | None = None) -> None:
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def _mgr(repo=None) -> AIAssistantManager:
    return AIAssistantManager(setting_repository=repo)


def test_default_no_setting_uses_30_week_upper(monkeypatch):
    """Without ``semester_total_weeks`` in the repo, the upper clamp
    should default to 30 — not the legacy 16."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=29)).isoformat(),
    })
    mgr = _mgr(repo)
    # 29 weeks in, default upper 30 → week 30.
    assert mgr._current_semester_week() == 30


def test_setting_24_clamps_to_24():
    """User-configured upper actually applied."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=50)).isoformat(),
        "semester_total_weeks": 24,
    })
    mgr = _mgr(repo)
    assert mgr._current_semester_week() == 24


def test_setting_above_40_clamped_to_40():
    """Defensive upper — silly values can't escape the 40-week ceiling."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=200)).isoformat(),
        "semester_total_weeks": 100,
    })
    mgr = _mgr(repo)
    assert mgr._current_semester_week() == 40


def test_setting_garbage_value_falls_back_to_default():
    """Non-int ``semester_total_weeks`` shouldn't crash."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=18)).isoformat(),
        "semester_total_weeks": ["not", "an", "int"],
    })
    mgr = _mgr(repo)
    # Falls back to default 30; we're 18 weeks in → week 19.
    assert mgr._current_semester_week() == 19


def test_before_semester_start_returns_one():
    """Negative delta → week 1 (never 0 or below)."""
    repo = _StubRepo({
        "semester_start": (date.today() + timedelta(days=10)).isoformat(),
    })
    mgr = _mgr(repo)
    assert mgr._current_semester_week() == 1
