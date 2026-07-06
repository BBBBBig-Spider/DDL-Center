"""Sync v3 bug fixes:
- folder-like <li> entries (title='作业', 'Labs', etc) must not be treated as tasks
- AI must not fabricate a 'today 23:59' due_time when no deadline is in the input
"""
from __future__ import annotations

from datetime import datetime

import pytest


# --- Folder filter ---


def test_folder_li_dropped_for_known_navigation_words():
    """A bare '作业' or 'Labs' title with no due is a folder navigation
    entry, not a task — must not even reach AI fallback."""
    from app.managers.sync_manager import _looks_like_folder
    assert _looks_like_folder({"title": "作业"})
    assert _looks_like_folder({"title": "Labs"})
    assert _looks_like_folder({"title": "labs"})
    assert _looks_like_folder({"title": "Homework"})
    assert _looks_like_folder({"title": "homework"})
    assert _looks_like_folder({"title": "作业列表"})
    assert _looks_like_folder({"title": "资料"})
    assert _looks_like_folder({"title": "讲义"})
    assert _looks_like_folder({"title": "  Labs  "})  # whitespace tolerated


def test_folder_filter_does_not_match_real_assignments():
    """Real assignment titles must NOT be flagged as folders."""
    from app.managers.sync_manager import _looks_like_folder
    assert not _looks_like_folder({"title": "Lab 1 - Hello world"})
    assert not _looks_like_folder({"title": "Homework 1 (for Units 1+2)"})
    assert not _looks_like_folder({"title": "2026-作业一"})
    assert not _looks_like_folder({"title": "lab4"})
    assert not _looks_like_folder({"title": "Homework 6 (for Units 11+12)"})
    assert not _looks_like_folder({"title": ""})
    assert not _looks_like_folder({"title": "作业 1"})  # has number after space


# --- AI no fabrication ---


def test_ai_clean_task_payload_accepts_null_due_time():
    """If the LLM returns due_time=None (because the input had no deadline),
    that must be accepted as the canonical 'no deadline' answer."""
    from app.managers.ai_assistant_manager import AIAssistantManager
    cleaned = AIAssistantManager._clean_task_payload({
        "title": "Homework 1",
        "due_time": None,
        "description": "",
    })
    assert cleaned.get("due_time") is None
    assert cleaned.get("title") == "Homework 1"


def test_ai_clean_task_payload_accepts_empty_string_due_time():
    """LLM might return empty string instead of null; treat as None."""
    from app.managers.ai_assistant_manager import AIAssistantManager
    cleaned = AIAssistantManager._clean_task_payload({
        "title": "Homework 2",
        "due_time": "",
    })
    assert cleaned.get("due_time") is None


def test_ai_clean_task_payload_preserves_valid_iso_due_time():
    """When a real due_time is provided, it must be parsed normally."""
    from app.managers.ai_assistant_manager import AIAssistantManager
    cleaned = AIAssistantManager._clean_task_payload({
        "title": "Real task",
        "due_time": "2026-06-30T23:59",
    })
    assert isinstance(cleaned.get("due_time"), datetime)
    assert cleaned["due_time"].year == 2026
    assert cleaned["due_time"].month == 6
    assert cleaned["due_time"].day == 30


def test_ai_clean_task_payload_rejects_garbage_due_time():
    """Malformed strings still raise — only None / '' are the new exemption."""
    from app.managers.ai_assistant_manager import AIAssistantManager
    with pytest.raises(ValueError):
        AIAssistantManager._clean_task_payload({
            "title": "T",
            "due_time": "not a date",
        })
