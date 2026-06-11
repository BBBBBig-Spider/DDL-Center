from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import BORDER, INK, PKU_RED, TEXT


DEFAULT_NOW_LINE_COLOR = "#3B82F6"
SETTING_KEY_NOW_LINE_COLOR = "now_line_color"


class GeneralSettingsPage(QWidget):
    """通用设置页面。当前仅含「外观」组的「当前时间线颜色」一项。"""

    now_line_color_changed = Signal(str)

    def __init__(self, facade, parent=None) -> None:
        super().__init__(parent)
        self.facade = facade
        self._init_ui()
        self._load_current_color()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        title = QLabel("通用设置")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        appearance_card = self._build_appearance_card()
        layout.addWidget(appearance_card)
        layout.addStretch()

    def _build_appearance_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: #FFFFFF; border: 1px solid {BORDER}; "
            f"border-radius: 10px; }}"
        )
        outer = QVBoxLayout(card)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        heading = QLabel("外观")
        heading.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {PKU_RED}; background: transparent;"
        )
        outer.addWidget(heading)

        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel("当前时间线颜色：")
        label.setStyleSheet(f"color: {TEXT}; background: transparent;")
        row.addWidget(label)

        self._color_swatch = QFrame()
        self._color_swatch.setFixedSize(40, 24)
        row.addWidget(self._color_swatch)

        self._color_hex_label = QLabel(DEFAULT_NOW_LINE_COLOR)
        self._color_hex_label.setStyleSheet(
            f"color: {TEXT}; background: transparent; font-family: monospace;"
        )
        row.addWidget(self._color_hex_label)

        choose_button = QPushButton("选择…")
        choose_button.clicked.connect(self._on_choose_color)
        row.addWidget(choose_button)

        reset_button = QPushButton("恢复默认")
        reset_button.clicked.connect(self._on_reset_color)
        row.addWidget(reset_button)

        row.addStretch()
        outer.addLayout(row)
        return card

    def _load_current_color(self) -> None:
        repo = getattr(self.facade, "setting_repository", None)
        color = DEFAULT_NOW_LINE_COLOR
        if repo is not None:
            try:
                stored = repo.get(SETTING_KEY_NOW_LINE_COLOR, DEFAULT_NOW_LINE_COLOR)
            except Exception:
                stored = DEFAULT_NOW_LINE_COLOR
            if isinstance(stored, str) and stored.startswith("#"):
                color = stored
        self._apply_color(color, persist=False, broadcast=False)

    def _apply_color(self, hex_color: str, *, persist: bool, broadcast: bool) -> None:
        self._color_hex_label.setText(hex_color)
        self._color_swatch.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid {BORDER}; border-radius: 4px;"
        )
        if persist:
            repo = getattr(self.facade, "setting_repository", None)
            if repo is not None:
                try:
                    repo.set(SETTING_KEY_NOW_LINE_COLOR, hex_color)
                except Exception:
                    pass
        if broadcast:
            self.now_line_color_changed.emit(hex_color)

    def _on_choose_color(self) -> None:
        current = QColor(self._color_hex_label.text())
        chosen = QColorDialog.getColor(current, self, "选择当前时间线颜色")
        if chosen.isValid():
            self._apply_color(chosen.name().upper(), persist=True, broadcast=True)

    def _on_reset_color(self) -> None:
        self._apply_color(DEFAULT_NOW_LINE_COLOR, persist=True, broadcast=True)
