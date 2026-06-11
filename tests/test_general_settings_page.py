import pytest
from PySide6.QtWidgets import QApplication

from app.gui.general_settings_page import (
    DEFAULT_NOW_LINE_COLOR,
    SETTING_KEY_NOW_LINE_COLOR,
    GeneralSettingsPage,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _StubRepo:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)


class _StubFacade:
    def __init__(self):
        self.setting_repository = _StubRepo()


def test_loads_default_color_when_unset(qapp):
    page = GeneralSettingsPage(_StubFacade())
    assert page._color_hex_label.text() == DEFAULT_NOW_LINE_COLOR


def test_loads_stored_color(qapp):
    facade = _StubFacade()
    facade.setting_repository.set(SETTING_KEY_NOW_LINE_COLOR, "#FF8800")
    page = GeneralSettingsPage(facade)
    assert page._color_hex_label.text() == "#FF8800"


def test_reset_writes_default_and_emits(qapp):
    facade = _StubFacade()
    facade.setting_repository.set(SETTING_KEY_NOW_LINE_COLOR, "#FF8800")
    page = GeneralSettingsPage(facade)
    received = []
    page.now_line_color_changed.connect(lambda hex_: received.append(hex_))
    page._on_reset_color()
    assert received == [DEFAULT_NOW_LINE_COLOR]
    assert facade.setting_repository.get(SETTING_KEY_NOW_LINE_COLOR) == DEFAULT_NOW_LINE_COLOR


def test_apply_color_persists_and_broadcasts(qapp):
    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    received = []
    page.now_line_color_changed.connect(lambda hex_: received.append(hex_))
    page._apply_color("#10B981", persist=True, broadcast=True)
    assert received == ["#10B981"]
    assert facade.setting_repository.get(SETTING_KEY_NOW_LINE_COLOR) == "#10B981"
