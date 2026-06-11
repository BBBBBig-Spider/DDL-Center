"""Verify the user-selectable AI model is wired through facade -> manager -> client."""
from __future__ import annotations

import pytest


class _StubKeyStore:
    def __init__(self, key="sk-fake"):
        self._key = key
    def get_key(self): return self._key
    def has_key(self): return bool(self._key)
    def set_key(self, k): self._key = k


class _StubSettingRepo:
    def __init__(self):
        self._data = {}
    def get(self, k, default=None): return self._data.get(k, default)
    def set(self, k, v): self._data[k] = v
    def delete(self, k): self._data.pop(k, None)


class _RecordingFactory:
    """Fake LLMClient factory that records the model it was called with."""
    def __init__(self):
        self.calls = []
    def __call__(self, api_key, *, base_url=None, model=None, timeout=None):
        self.calls.append({"api_key": api_key, "model": model})
        class _C:
            def chat(self, *a, **kw): return ("", 0)
        return _C()


def _make_manager(model=None):
    from app.managers.ai_assistant_manager import AIAssistantManager
    factory = _RecordingFactory()
    mgr = AIAssistantManager(
        task_manager=None,
        alert_manager=None,
        statistics_manager=None,
        setting_repository=_StubSettingRepo(),
        schedule_manager=None,
        course_manager=None,
        key_store=_StubKeyStore(),
        llm_client_factory=factory,
        model=model,
    )
    return mgr, factory


def test_default_model_is_deepseek_chat():
    mgr, _ = _make_manager()
    assert mgr.get_model() == "deepseek-chat"


def test_set_model_persists_to_settings():
    mgr, _ = _make_manager()
    mgr.set_model("deepseek-reasoner")
    assert mgr.setting_repository.get("deepseek_model") == "deepseek-reasoner"
    assert mgr.get_model() == "deepseek-reasoner"


def test_set_model_rejects_empty():
    mgr, _ = _make_manager()
    with pytest.raises(ValueError):
        mgr.set_model("")


def test_factory_called_with_current_model():
    mgr, factory = _make_manager(model="deepseek-reasoner")
    mgr.test_api_key("sk-test")
    assert factory.calls[-1]["model"] == "deepseek-reasoner"
