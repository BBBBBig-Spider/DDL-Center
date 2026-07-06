from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.gui.widgets.ai_briefing_panel import AIBriefingPanel


class FakeFacade:
    def __init__(self) -> None:
        self.calls = 0

    def ai_is_available(self) -> bool:
        return True

    def ai_generate_briefing(self) -> str:
        self.calls += 1
        return f"briefing-{self.calls}"


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def test_briefing_refresh_uses_startup_cache_until_forced(qapp):
    facade = FakeFacade()
    panel = AIBriefingPanel(facade=facade)

    assert facade.calls == 1
    assert panel.content_label.text() == "briefing-1"

    panel.refresh()
    panel.refresh()

    assert facade.calls == 1
    assert panel.content_label.text() == "briefing-1"

    panel.refresh(force_ai=True)

    assert facade.calls == 2
    assert panel.content_label.text() == "briefing-2"
