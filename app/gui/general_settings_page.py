from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import (
    BORDER,
    INK,
    PALETTE_LABELS,
    PALETTES,
    PRIMARY,
    TEXT,
    _persist_palette_name,
    _read_active_palette_name,
)


DEFAULT_NOW_LINE_COLOR = "#3B82F6"
SETTING_KEY_NOW_LINE_COLOR = "now_line_color"
SETTING_KEY_AVATAR_PATH = "avatar_path"

# ── Font scale ────────────────────────────────────────────────
FONT_SCALE_OPTIONS = [
    ("小", 0.85),
    ("中", 1.00),
    ("大", 1.15),
    ("特大", 1.30),
]
DEFAULT_FONT_SCALE = 1.00
SETTING_KEY_FONT_SCALE = "font_scale"
HARD_CAP_FONT_SCALE = 1.30  # never exceed; clamps absurd persisted values
MIN_FONT_SCALE = 0.85
# Fixed numeric base so scale is stable across runs — sampling app.font()
# each launch would compound the previous setPointSizeF() call.
FONT_BASE_PT = 10.0

# ── Display name ──────────────────────────────────────────────
SETTING_KEY_DISPLAY_NAME = "display_name"
DISPLAY_NAME_MAX_LEN = 20


def _make_circular_pixmap(source_path: str | None, diameter: int = 40) -> QPixmap:
    """Render a circular pixmap from ``source_path``; falls back to a light-gray
    disc when the path is empty/missing/unreadable. Shared by the settings page
    and the main-window login card so both render the same avatar shape."""
    src = QPixmap(source_path) if source_path else QPixmap()
    if src.isNull():
        result = QPixmap(diameter, diameter)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.lightGray)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, diameter, diameter)
        painter.end()
        return result
    src = src.scaled(
        diameter,
        diameter,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QPixmap(diameter, diameter)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, diameter, diameter)
    painter.setClipPath(path)
    # Center-crop the scaled source onto the disc.
    x = (diameter - src.width()) // 2
    y = (diameter - src.height()) // 2
    painter.drawPixmap(x, y, src)
    painter.end()
    return result


class GeneralSettingsPage(QWidget):
    """通用设置页面：外观（当前时间线颜色、头像、主题配色、字体大小） + 账户。"""

    now_line_color_changed = Signal(str)
    avatar_changed = Signal(str)
    font_scale_changed = Signal(float)
    display_name_changed = Signal(str)

    def __init__(self, facade, parent=None) -> None:
        super().__init__(parent)
        self.facade = facade
        self._init_ui()
        self._load_current_color()
        self._load_current_avatar()
        self._load_current_palette()
        self._load_current_font_scale()
        self._load_current_display_name()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        title = QLabel("通用设置")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        appearance_card = self._build_appearance_card()
        layout.addWidget(appearance_card)

        account_card = self._build_account_card()
        layout.addWidget(account_card)

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
            f"font-size: 16px; font-weight: 700; color: {PRIMARY}; background: transparent;"
        )
        outer.addWidget(heading)

        # ── Current-time-line color row ─────────────────────────
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

        # ── Avatar row ──────────────────────────────────────────
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(10)
        avatar_label = QLabel("头像：")
        avatar_label.setStyleSheet(f"color: {TEXT}; background: transparent;")
        avatar_row.addWidget(avatar_label)

        self._avatar_preview = QLabel()
        self._avatar_preview.setFixedSize(40, 40)
        self._avatar_preview.setStyleSheet("background: transparent;")
        avatar_row.addWidget(self._avatar_preview)

        choose_avatar_btn = QPushButton("选择图片…")
        choose_avatar_btn.clicked.connect(self._on_choose_avatar)
        avatar_row.addWidget(choose_avatar_btn)

        reset_avatar_btn = QPushButton("恢复默认")
        reset_avatar_btn.clicked.connect(self._reset_avatar)
        avatar_row.addWidget(reset_avatar_btn)

        avatar_row.addStretch()
        outer.addLayout(avatar_row)

        # ── Theme palette row ───────────────────────────────────
        palette_row = QHBoxLayout()
        palette_row.setSpacing(10)
        palette_label = QLabel("主题配色：")
        palette_label.setStyleSheet(f"color: {TEXT}; background: transparent;")
        palette_row.addWidget(palette_label)

        self._palette_combo = QComboBox()
        # Stable iteration order: pku_red first, then thu_purple, ocean_blue, dark.
        for key in ("pku_red", "thu_purple", "ocean_blue", "dark"):
            self._palette_combo.addItem(PALETTE_LABELS[key], key)
        palette_row.addWidget(self._palette_combo)

        self._palette_pending_label = QLabel("")
        self._palette_pending_label.setStyleSheet(
            f"color: {PRIMARY}; background: transparent; font-weight: 700;"
        )
        palette_row.addWidget(self._palette_pending_label)

        self._palette_combo.currentIndexChanged.connect(self._on_palette_combo_changed)

        apply_palette_btn = QPushButton("应用")
        apply_palette_btn.clicked.connect(self._on_apply_palette_clicked)
        palette_row.addWidget(apply_palette_btn)

        palette_row.addStretch()
        outer.addLayout(palette_row)

        # ── Font scale row ──────────────────────────────────────
        font_row = QHBoxLayout()
        font_row.setSpacing(10)
        font_label = QLabel("字体大小：")
        font_label.setStyleSheet(f"color: {TEXT}; background: transparent;")
        font_row.addWidget(font_label)

        self._font_scale_combo = QComboBox()
        for label, value in FONT_SCALE_OPTIONS:
            self._font_scale_combo.addItem(label, float(value))
        font_row.addWidget(self._font_scale_combo)

        self._font_scale_combo.currentIndexChanged.connect(self._on_font_scale_combo_changed)

        font_row.addStretch()
        outer.addLayout(font_row)
        return card

    # ─── Color logic ────────────────────────────────────────
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

    # ─── Avatar logic ───────────────────────────────────────
    def _get_avatar_path(self) -> str | None:
        repo = getattr(self.facade, "setting_repository", None)
        if repo is None:
            return None
        try:
            value = repo.get(SETTING_KEY_AVATAR_PATH, None)
        except Exception:
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    def _load_current_avatar(self) -> None:
        path = self._get_avatar_path()
        # If the file no longer exists, fall back to the default disc.
        if path and not Path(path).is_file():
            path = None
        self._avatar_preview.setPixmap(_make_circular_pixmap(path, 40))

    def _on_choose_avatar(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "选择头像",
            "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if not chosen:
            return
        if not Path(chosen).is_file():
            QMessageBox.warning(self, "无效图片", "选择的文件不存在。")
            return
        probe = QPixmap(chosen)
        if probe.isNull():
            QMessageBox.warning(self, "无效图片", "无法加载该图片，请选择其他文件。")
            return
        self._apply_avatar(chosen)

    def _apply_avatar(self, path: str) -> None:
        """Persist the avatar path, refresh the preview, and emit the signal."""
        repo = getattr(self.facade, "setting_repository", None)
        if repo is not None:
            try:
                repo.set(SETTING_KEY_AVATAR_PATH, path)
            except Exception:
                pass
        self._avatar_preview.setPixmap(_make_circular_pixmap(path, 40))
        self.avatar_changed.emit(path)

    def _reset_avatar(self) -> None:
        repo = getattr(self.facade, "setting_repository", None)
        if repo is not None:
            try:
                if hasattr(repo, "delete"):
                    repo.delete(SETTING_KEY_AVATAR_PATH)
                else:
                    repo.set(SETTING_KEY_AVATAR_PATH, "")
            except Exception:
                pass
        self._avatar_preview.setPixmap(_make_circular_pixmap(None, 40))
        self.avatar_changed.emit("")

    # ─── Palette logic ──────────────────────────────────────
    def _get_palette_name(self) -> str:
        """Currently active palette name (from disk)."""
        return _read_active_palette_name()

    def _load_current_palette(self) -> None:
        name = self._get_palette_name()
        for i in range(self._palette_combo.count()):
            if self._palette_combo.itemData(i) == name:
                # Block signal so loading doesn't trigger the "pending" badge.
                self._palette_combo.blockSignals(True)
                self._palette_combo.setCurrentIndex(i)
                self._palette_combo.blockSignals(False)
                break
        self._palette_pending_label.setText("")

    def _on_palette_combo_changed(self, _index: int) -> None:
        # Selection only — don't apply yet. Show "pending restart" hint when
        # the combo differs from the persisted value.
        chosen = self._palette_combo.currentData()
        if chosen != self._get_palette_name():
            self._palette_pending_label.setText("（待重启）")
        else:
            self._palette_pending_label.setText("")

    def _on_apply_palette_clicked(self) -> None:
        chosen = self._palette_combo.currentData()
        if not isinstance(chosen, str):
            return
        if self._apply_palette(chosen):
            self._restart_application()

    def _apply_palette(self, name: str) -> bool:
        """Persist the palette name. Takes effect after restart — theme
        constants are bound at module import time."""
        if name not in PALETTES:
            return False
        _persist_palette_name(name)
        self._palette_pending_label.setText("正在重启…")
        return True

    def _restart_application(self) -> None:
        app = QApplication.instance()
        try:
            subprocess.Popen([sys.executable, "-m", "app.main"], close_fds=True)
        except Exception as exc:
            self._palette_pending_label.setText("（重启失败）")
            QMessageBox.critical(
                self,
                "重启失败",
                f"主题已保存，但自动重启失败，请手动重启应用。\n\n{exc}",
            )
            return
        if app is not None:
            app.quit()

    # ─── Font scale logic ───────────────────────────────────
    def _get_font_scale(self) -> float:
        repo = getattr(self.facade, "setting_repository", None)
        if repo is None:
            return DEFAULT_FONT_SCALE
        try:
            stored = repo.get(SETTING_KEY_FONT_SCALE, DEFAULT_FONT_SCALE)
        except Exception:
            return DEFAULT_FONT_SCALE
        try:
            return float(stored)
        except (TypeError, ValueError):
            return DEFAULT_FONT_SCALE

    def _load_current_font_scale(self) -> None:
        scale = self._get_font_scale()
        # Pick the closest preset by absolute distance.
        best_idx = 0
        best_diff = float("inf")
        for i in range(self._font_scale_combo.count()):
            value = float(self._font_scale_combo.itemData(i))
            diff = abs(value - scale)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        self._font_scale_combo.blockSignals(True)
        self._font_scale_combo.setCurrentIndex(best_idx)
        self._font_scale_combo.blockSignals(False)

    def _on_font_scale_combo_changed(self, _index: int) -> None:
        value = self._font_scale_combo.currentData()
        try:
            scale = float(value)
        except (TypeError, ValueError):
            return
        self._apply_font_scale(scale)

    def _apply_font_scale(self, scale: float) -> None:
        """Clamp, apply to QApplication font, persist, and emit signal."""
        try:
            scale = float(scale)
        except (TypeError, ValueError):
            scale = DEFAULT_FONT_SCALE
        scale = max(MIN_FONT_SCALE, min(HARD_CAP_FONT_SCALE, scale))

        app = QApplication.instance()
        if app is not None:
            base_font = app.font()
            new_font = QFont(base_font)
            new_font.setPointSizeF(FONT_BASE_PT * scale)
            app.setFont(new_font)

        repo = getattr(self.facade, "setting_repository", None)
        if repo is not None:
            try:
                repo.set(SETTING_KEY_FONT_SCALE, scale)
            except Exception:
                pass

        self.font_scale_changed.emit(scale)

        # Bump the main window if the larger fonts make it cramped.
        if scale > 1.15:
            top = self.window()
            if top is not None:
                screen = top.screen()
                if screen is not None:
                    avail = screen.availableGeometry()
                    target_w = min(int(1120 * scale), int(avail.width() * 0.9))
                    target_h = min(int(760 * scale), int(avail.height() * 0.9))
                    current = top.geometry()
                    if current.width() < target_w or current.height() < target_h:
                        top.resize(target_w, target_h)

    # ── Account / display name ─────────────────────────────────

    def _build_account_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: #FFFFFF; border: 1px solid {BORDER}; "
            f"border-radius: 10px; }}"
        )
        outer = QVBoxLayout(card)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        heading = QLabel("账户")
        heading.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {PRIMARY}; background: transparent;"
        )
        outer.addWidget(heading)

        hint = QLabel("登录后左下角默认显示学号；填写显示名即可改为更友好的称呼。")
        hint.setStyleSheet("color: #888; background: transparent; font-size: 12px;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel("显示名：")
        label.setStyleSheet("background: transparent;")
        row.addWidget(label)

        self._display_name_input = QLineEdit()
        self._display_name_input.setMaxLength(DISPLAY_NAME_MAX_LEN)
        self._display_name_input.setPlaceholderText("如：大蜘蛛（留空则显示学号）")
        self._display_name_input.setMinimumWidth(220)
        row.addWidget(self._display_name_input, stretch=1)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save_display_name)
        row.addWidget(save_btn)

        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self._on_clear_display_name)
        row.addWidget(clear_btn)

        outer.addLayout(row)
        return card

    def _get_display_name(self) -> str:
        repo = getattr(self.facade, "setting_repository", None)
        if repo is None:
            return ""
        try:
            value = repo.get(SETTING_KEY_DISPLAY_NAME, "")
        except Exception:
            return ""
        return value if isinstance(value, str) else ""

    def _load_current_display_name(self) -> None:
        if hasattr(self, "_display_name_input"):
            self._display_name_input.setText(self._get_display_name())

    def _apply_display_name(self, name: str) -> None:
        name = (name or "").strip()[:DISPLAY_NAME_MAX_LEN]
        repo = getattr(self.facade, "setting_repository", None)
        if repo is not None:
            try:
                if name:
                    repo.set(SETTING_KEY_DISPLAY_NAME, name)
                else:
                    repo.delete(SETTING_KEY_DISPLAY_NAME)
            except Exception:
                pass
        self.display_name_changed.emit(name)

    def _on_save_display_name(self) -> None:
        self._apply_display_name(self._display_name_input.text())

    def _on_clear_display_name(self) -> None:
        self._display_name_input.clear()
        self._apply_display_name("")
