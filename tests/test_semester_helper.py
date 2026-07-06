"""tests/test_semester_helper.py — single-source-of-truth current-week math.

Covers REVIEW.md severe #4 — see ``app/utils/semester.py`` for the rationale.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.utils import semester as semester_mod
from app.utils.semester import compute_current_week


class _StubRepo:
    def __init__(self, data: dict | None = None) -> None:
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)


def test_no_repo_uses_config_start_and_default_upper(monkeypatch):
    """When no repo is wired, fall back to ``config.SEMESTER_START`` and a
    30-week upper bound."""
    # Pin the start to "today" so we know the week is exactly 1.
    monkeypatch.setattr("app.config.SEMESTER_START", date.today())
    week = compute_current_week(None)
    assert week == 1


def test_repo_with_custom_start(monkeypatch):
    """A semester_start in the repo overrides the config constant."""
    # Config start is far future — shouldn't be used because the repo wins.
    monkeypatch.setattr("app.config.SEMESTER_START", date(2099, 1, 1))
    repo = _StubRepo({"semester_start": (date.today() - timedelta(days=14)).isoformat()})
    week = compute_current_week(repo)
    # ~14 days after start → week 3.
    assert week == 3


def test_repo_total_weeks_clamps_result(monkeypatch):
    """If we're 50 weeks past start but total_weeks=20, clamp to 20."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=50)).isoformat(),
        "semester_total_weeks": 20,
    })
    assert compute_current_week(repo) == 20


def test_repo_total_weeks_above_40_clamped_to_40():
    """Defensive: silly values in the repo can't push the upper past 40."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=200)).isoformat(),
        "semester_total_weeks": 9999,
    })
    assert compute_current_week(repo) == 40


def test_before_semester_start_returns_one(monkeypatch):
    """Today < start → week 1 (never 0 or negative)."""
    repo = _StubRepo({
        "semester_start": (date.today() + timedelta(days=30)).isoformat(),
    })
    assert compute_current_week(repo) == 1


def test_garbage_total_weeks_falls_back_to_default():
    """A non-int ``semester_total_weeks`` shouldn't raise — just use 30."""
    repo = _StubRepo({
        "semester_start": (date.today() - timedelta(weeks=35)).isoformat(),
        "semester_total_weeks": "not-an-int",
    })
    # Default upper is 30; we'd be at week 36 untruncated, so result is 30.
    assert compute_current_week(repo) == 30


def test_garbage_start_falls_back_to_config(monkeypatch):
    """A bogus ``semester_start`` doesn't raise — falls back to config."""
    monkeypatch.setattr("app.config.SEMESTER_START", date.today())
    repo = _StubRepo({"semester_start": "this-is-not-a-date"})
    # Config start is "today", so week == 1.
    assert compute_current_week(repo) == 1


def test_explicit_fallback_start_overrides_config(monkeypatch):
    """When the caller passes ``fallback_start``, it's preferred over
    ``config.SEMESTER_START`` (used by ScheduleWidget which already
    resolves a per-user start)."""
    monkeypatch.setattr("app.config.SEMESTER_START", date(2099, 1, 1))
    week = compute_current_week(
        None,
        fallback_start=date.today() - timedelta(weeks=4),
    )
    assert week == 5
