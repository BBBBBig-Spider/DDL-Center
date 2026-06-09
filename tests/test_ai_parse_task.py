from datetime import datetime
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


def _make_manager(reply_json):
    fake_client = MagicMock()
    fake_client.chat.return_value = (reply_json, 100)
    factory = MagicMock(return_value=fake_client)
    return AIAssistantManager(key_store=_FakeKeyStore("sk-fake"), llm_client_factory=factory)


def test_parse_task_from_text_happy_path():
    m = _make_manager(
        '{"title":"提交研究报告","due_time":"2026-06-10T21:00",'
        '"description":"","estimated_hours":3}'
    )
    out = m.parse_task_from_text("提交研究报告，6月10号晚上9点截止")
    assert out["title"] == "提交研究报告"
    assert isinstance(out["due_time"], datetime)
    assert out["due_time"].hour == 21
    assert out["estimated_hours"] == 3.0
    assert out["priority"] == 2
    assert out["status"] == "todo"


def test_parse_task_strips_markdown_codeblocks():
    m = _make_manager(
        '```json\n{"title":"x","due_time":"2026-06-10T09:00",'
        '"description":"d","estimated_hours":1}\n```'
    )
    out = m.parse_task_from_text("随便")
    assert out["title"] == "x"
    assert out["due_time"].hour == 9
    assert out["description"] == "d"


def test_parse_task_rejects_empty_input():
    m = _make_manager("{}")
    with pytest.raises(ValueError):
        m.parse_task_from_text("")


def test_parse_task_no_key_uses_regex_fallback_with_explicit_date():
    # 无 key 时回退到正则
    m = AIAssistantManager(key_store=_FakeKeyStore(None))
    out = m.parse_task_from_text("写报告，2026-06-15 23:59 截止")
    assert "报告" in out["title"]
    assert out["due_time"].year == 2026
    assert out["due_time"].month == 6
    assert out["due_time"].day == 15
    assert out["due_time"].hour == 23
