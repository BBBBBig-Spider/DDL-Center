"""Tests for AIAssistantManager.parse_item_from_text (task / class / exam)."""
from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from app.managers.ai_assistant_manager import AIAssistantManager


class _FakeKeyStore:
    def __init__(self, key=None):
        self._k = key

    def get_key(self):
        return self._k

    def set_key(self, k):
        self._k = k

    def has_key(self):
        return bool(self._k)


def _make_manager(reply_json: str) -> AIAssistantManager:
    fake_client = MagicMock()
    fake_client.chat.return_value = (reply_json, 100)
    factory = MagicMock(return_value=fake_client)
    return AIAssistantManager(
        key_store=_FakeKeyStore("sk-fake"), llm_client_factory=factory
    )


def test_parse_item_task_happy_path():
    m = _make_manager(
        '{"type":"task","payload":{"title":"提交研究报告",'
        '"due_time":"2026-06-10T21:00","description":"","estimated_hours":3}}'
    )
    item = m.parse_item_from_text("提交研究报告，6月10号晚上9点截止")
    assert item["type"] == "task"
    p = item["payload"]
    assert p["title"] == "提交研究报告"
    assert isinstance(p["due_time"], datetime)
    assert p["due_time"].hour == 21
    assert p["estimated_hours"] == 3.0
    assert p["priority"] == 2
    assert p["status"] == "todo"


def test_parse_item_class_happy_path():
    m = _make_manager(
        '{"type":"class","payload":{"title":"高数课","weekday":3,'
        '"start_time":"19:00","end_time":"21:00","location":"理教 303",'
        '"start_week":1,"end_week":16,"week_type":"all"}}'
    )
    item = m.parse_item_from_text("每周三晚 7-9 点高数课，理教 303，1-16 周")
    assert item["type"] == "class"
    p = item["payload"]
    assert p["title"] == "高数课"
    assert p["weekday"] == 3
    assert p["start_time"] == time(19, 0)
    assert p["end_time"] == time(21, 0)
    assert p["location"] == "理教 303"
    assert p["start_week"] == 1
    assert p["end_week"] == 16
    assert p["week_type"] == "all"
    assert p["slot_type"] == "lecture"


def test_parse_item_exam_happy_path():
    m = _make_manager(
        '{"type":"exam","payload":{"name":"高数期末",'
        '"start_time":"2026-06-20T09:00","end_time":"2026-06-20T11:00",'
        '"location":"理教 303","exam_type":"final"}}'
    )
    item = m.parse_item_from_text("高数期末，6月20日 9:00-11:00，理教 303")
    assert item["type"] == "exam"
    p = item["payload"]
    assert p["name"] == "高数期末"
    assert isinstance(p["start_time"], datetime)
    assert isinstance(p["end_time"], datetime)
    assert p["start_time"].hour == 9
    assert p["end_time"].hour == 11
    assert p["location"] == "理教 303"
    assert p["exam_type"] == "final"


def test_parse_item_strips_markdown_codeblock():
    m = _make_manager(
        '```json\n{"type":"task","payload":{"title":"x",'
        '"due_time":"2026-06-10T09:00","description":"d","estimated_hours":1}}\n```'
    )
    item = m.parse_item_from_text("随便")
    assert item["type"] == "task"
    assert item["payload"]["title"] == "x"
    assert item["payload"]["due_time"].hour == 9


def test_parse_item_rejects_empty():
    m = _make_manager("{}")
    with pytest.raises(ValueError):
        m.parse_item_from_text("")


def test_parse_item_no_key_falls_back_to_class():
    m = AIAssistantManager(key_store=_FakeKeyStore(None))
    item = m.parse_item_from_text("每周三 19:00-20:30 高数课")
    assert item["type"] == "class"
    p = item["payload"]
    assert p["weekday"] == 3
    assert p["start_time"] == time(19, 0)
    assert p["end_time"] == time(20, 30)


def test_parse_item_no_key_falls_back_to_exam():
    m = AIAssistantManager(key_store=_FakeKeyStore(None))
    item = m.parse_item_from_text("高数考试 2026-06-20 9:00-11:00")
    assert item["type"] == "exam"
    p = item["payload"]
    assert isinstance(p["start_time"], datetime)
    assert p["start_time"].year == 2026
    assert p["start_time"].month == 6
    assert p["start_time"].day == 20
    assert p["start_time"].hour == 9
    assert p["end_time"].hour == 11


def test_parse_item_no_key_falls_back_to_task():
    m = AIAssistantManager(key_store=_FakeKeyStore(None))
    item = m.parse_item_from_text("写报告，2026-06-15 23:59 截止")
    assert item["type"] == "task"
    p = item["payload"]
    assert "报告" in p["title"]
    assert p["due_time"].year == 2026
    assert p["due_time"].month == 6
    assert p["due_time"].day == 15


def test_parse_task_from_text_raises_when_ai_returns_class():
    m = _make_manager(
        '{"type":"class","payload":{"title":"高数","weekday":3,'
        '"start_time":"19:00","end_time":"21:00","location":"",'
        '"start_week":1,"end_week":16,"week_type":"all"}}'
    )
    with pytest.raises(ValueError):
        m.parse_task_from_text("每周三晚 7-9 点高数课")
