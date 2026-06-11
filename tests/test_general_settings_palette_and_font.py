"""Phase 2.2 + 2.3: theme palette switch + font scaling."""
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


# ----- palette -----

def test_palettes_dict_has_expected_options():
    from app.gui import theme

    assert set(theme.PALETTES.keys()) == {"pku_red", "thu_purple", "ocean_blue", "dark"}


def test_each_palette_defines_all_color_keys():
    from app.gui import theme

    required = {
        "PKU_RED", "PKU_RED_DARK", "PKU_RED_LIGHT", "PKU_GOLD",
        "INK", "TEXT", "MUTED", "BORDER", "SURFACE", "BACKGROUND",
    }
    for name, palette in theme.PALETTES.items():
        missing = required - set(palette.keys())
        assert not missing, f"palette {name!r} missing color keys: {missing}"


def test_palette_labels_cover_all_palettes():
    from app.gui import theme

    assert set(theme.PALETTE_LABELS.keys()) == set(theme.PALETTES.keys())


def test_persist_palette_round_trip(tmp_path, monkeypatch):
    from app.gui import theme

    # Redirect persistence to a tmp dir by switching cwd — theme writes to
    # ./data/.theme_palette relative to the working directory.
    monkeypatch.chdir(tmp_path)
    theme._persist_palette_name("ocean_blue")
    assert theme._read_active_palette_name() == "ocean_blue"


def test_persist_palette_rejects_unknown(tmp_path, monkeypatch):
    from app.gui import theme

    monkeypatch.chdir(tmp_path)
    theme._persist_palette_name("ocean_blue")
    theme._persist_palette_name("not-a-palette")
    # Bogus name is ignored, prior value retained.
    assert theme._read_active_palette_name() == "ocean_blue"


def test_read_active_palette_defaults_when_missing(tmp_path, monkeypatch):
    from app.gui import theme

    monkeypatch.chdir(tmp_path)
    assert theme._read_active_palette_name() == theme.DEFAULT_PALETTE


# ----- font scale -----

def test_default_font_scale(qapp):
    from app.gui.general_settings_page import (
        DEFAULT_FONT_SCALE,
        GeneralSettingsPage,
    )

    page = GeneralSettingsPage(_StubFacade())
    assert page._get_font_scale() == DEFAULT_FONT_SCALE


def test_apply_font_scale_persists(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage,
        SETTING_KEY_FONT_SCALE,
    )

    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    received = []
    page.font_scale_changed.connect(lambda v: received.append(v))
    page._apply_font_scale(1.15)
    assert facade.setting_repository.get(SETTING_KEY_FONT_SCALE) == 1.15
    assert received == [1.15]


def test_apply_font_scale_clamps_to_cap(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage,
        HARD_CAP_FONT_SCALE,
        SETTING_KEY_FONT_SCALE,
    )

    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    page._apply_font_scale(99.0)  # absurd value
    assert facade.setting_repository.get(SETTING_KEY_FONT_SCALE) == HARD_CAP_FONT_SCALE


def test_apply_font_scale_clamps_to_floor(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage,
        SETTING_KEY_FONT_SCALE,
    )

    facade = _StubFacade()
    page = GeneralSettingsPage(facade)
    page._apply_font_scale(0.1)
    assert facade.setting_repository.get(SETTING_KEY_FONT_SCALE) == 0.85


def test_apply_font_scale_emits_signal_with_clamped_value(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage,
        HARD_CAP_FONT_SCALE,
    )

    page = GeneralSettingsPage(_StubFacade())
    received = []
    page.font_scale_changed.connect(lambda v: received.append(v))
    page._apply_font_scale(99.0)
    assert received == [HARD_CAP_FONT_SCALE]


def test_load_font_scale_picks_closest_preset(qapp):
    from app.gui.general_settings_page import (
        GeneralSettingsPage,
        SETTING_KEY_FONT_SCALE,
    )

    repo = _StubRepo({SETTING_KEY_FONT_SCALE: 1.15})
    page = GeneralSettingsPage(_StubFacade(repo))
    # Combo should select the "大" preset (1.15).
    assert float(page._font_scale_combo.currentData()) == pytest.approx(1.15)


# ----- palette UI -----

def test_palette_apply_persists(qapp, tmp_path, monkeypatch):
    from app.gui import theme
    from app.gui.general_settings_page import GeneralSettingsPage

    monkeypatch.chdir(tmp_path)
    page = GeneralSettingsPage(_StubFacade())
    page._apply_palette("dark")
    assert theme._read_active_palette_name() == "dark"


def test_palette_apply_unknown_is_noop(qapp, tmp_path, monkeypatch):
    from app.gui import theme
    from app.gui.general_settings_page import GeneralSettingsPage

    monkeypatch.chdir(tmp_path)
    theme._persist_palette_name("ocean_blue")
    page = GeneralSettingsPage(_StubFacade())
    page._apply_palette("bogus-palette")
    assert theme._read_active_palette_name() == "ocean_blue"


def test_palette_combo_loads_active(qapp, tmp_path, monkeypatch):
    from app.gui import theme
    from app.gui.general_settings_page import GeneralSettingsPage

    monkeypatch.chdir(tmp_path)
    theme._persist_palette_name("dark")
    page = GeneralSettingsPage(_StubFacade())
    assert page._palette_combo.currentData() == "dark"
