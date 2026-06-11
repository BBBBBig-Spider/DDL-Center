"""Phase 2.1 (C): user-set display name in GeneralSettingsPage."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


class _StubRepo:
    def __init__(self, data=None):
        self._data = dict(data or {})

    def get(self, k, default=None):
        return self._data.get(k, default)

    def set(self, k, v):
        self._data[k] = v

    def delete(self, k):
        self._data.pop(k, None)


class _StubFacade:
    def __init__(self, repo=None):
        self.setting_repository = repo or _StubRepo()


def test_default_display_name_is_empty(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage
    page = GeneralSettingsPage(_StubFacade())
    assert page._get_display_name() == ""


def test_loads_persisted_display_name(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_DISPLAY_NAME
    facade = _StubFacade(_StubRepo({SETTING_KEY_DISPLAY_NAME: "杨恩华"}))
    page = GeneralSettingsPage(facade)
    assert page._get_display_name() == "杨恩华"
    assert page._display_name_input.text() == "杨恩华"


def test_apply_persists_and_emits(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_DISPLAY_NAME
    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    received = []
    page.display_name_changed.connect(lambda n: received.append(n))
    page._apply_display_name("张三")
    assert facade.setting_repository.get(SETTING_KEY_DISPLAY_NAME) == "张三"
    assert received == ["张三"]


def test_apply_strips_whitespace(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_DISPLAY_NAME
    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    page._apply_display_name("  李四  ")
    assert facade.setting_repository.get(SETTING_KEY_DISPLAY_NAME) == "李四"


def test_apply_truncates_to_max_len(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage, SETTING_KEY_DISPLAY_NAME, DISPLAY_NAME_MAX_LEN,
    )
    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    long_name = "X" * (DISPLAY_NAME_MAX_LEN + 10)
    page._apply_display_name(long_name)
    stored = facade.setting_repository.get(SETTING_KEY_DISPLAY_NAME)
    assert len(stored) == DISPLAY_NAME_MAX_LEN


def test_clear_removes_setting_and_broadcasts_empty(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_DISPLAY_NAME
    facade = _StubFacade(_StubRepo({SETTING_KEY_DISPLAY_NAME: "before"}))
    page = GeneralSettingsPage(facade)
    received = []
    page.display_name_changed.connect(lambda n: received.append(n))
    page._on_clear_display_name()
    assert not facade.setting_repository.get(SETTING_KEY_DISPLAY_NAME)
    assert received == [""]
    assert page._display_name_input.text() == ""
