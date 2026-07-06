"""Verify that matplotlib's font resolution prefers a CJK-capable font."""
from __future__ import annotations
import importlib

import pytest

matplotlib = pytest.importorskip("matplotlib")


def test_install_chinese_font_prepends_candidate(monkeypatch):
    # Force the candidate detection to find a known fake font.
    import matplotlib.font_manager as fm
    fake_name = "Microsoft YaHei"

    class _Stub:
        def __init__(self, name): self.name = name

    monkeypatch.setattr(fm.fontManager, "ttflist", [_Stub(fake_name), _Stub("DejaVu Sans")])

    # Re-import statistics_window so the module-level call runs again.
    from app.gui import statistics_window
    importlib.reload(statistics_window)

    assert matplotlib.rcParams["font.sans-serif"][0] == fake_name
    assert matplotlib.rcParams["axes.unicode_minus"] is False
