"""Avatar setting in GeneralSettingsPage."""
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
    def get(self, k, default=None): return self._data.get(k, default)
    def set(self, k, v): self._data[k] = v
    def delete(self, k): self._data.pop(k, None)


class _StubFacade:
    def __init__(self, repo=None):
        self.setting_repository = repo or _StubRepo()


def test_default_avatar_is_empty(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage
    page = GeneralSettingsPage(_StubFacade())
    # Default state: no avatar path in repo.
    assert page._get_avatar_path() in (None, "")


def test_apply_avatar_persists_and_emits(qapp, tmp_path):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_AVATAR_PATH
    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    received = []
    page.avatar_changed.connect(lambda p: received.append(p))
    # Need a real image file
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import Qt
    img = QPixmap(64, 64)
    img.fill(Qt.GlobalColor.red)
    img_path = tmp_path / "test_avatar.png"
    img.save(str(img_path), "PNG")
    page._apply_avatar(str(img_path))
    assert facade.setting_repository.get(SETTING_KEY_AVATAR_PATH) == str(img_path)
    assert received == [str(img_path)]


def test_reset_avatar_clears_setting(qapp):
    from app.gui.general_settings_page import GeneralSettingsPage, SETTING_KEY_AVATAR_PATH
    facade = _StubFacade()
    facade.setting_repository.set(SETTING_KEY_AVATAR_PATH, "/some/path.png")
    page = GeneralSettingsPage(facade)
    received = []
    page.avatar_changed.connect(lambda p: received.append(p))
    page._reset_avatar()
    # After reset, the setting should be empty/None
    assert not facade.setting_repository.get(SETTING_KEY_AVATAR_PATH)
    assert received == [""]
