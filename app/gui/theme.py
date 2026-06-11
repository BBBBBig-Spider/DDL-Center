PALETTES = {
    "pku_red": {
        "PKU_RED": "#8C1515",
        "PKU_RED_DARK": "#5F0F0F",
        "PKU_RED_LIGHT": "#F8EAEA",
        "PKU_GOLD": "#B8860B",
        "INK": "#111827",
        "TEXT": "#4B5563",
        "MUTED": "#6B7280",
        "BORDER": "#E5E7EB",
        "SURFACE": "#FFFFFF",
        "BACKGROUND": "#F7F3F0",
    },
    "thu_purple": {
        # 清华紫主色 #660874（清华大学官方校色）
        "PKU_RED": "#660874",
        "PKU_RED_DARK": "#4A0654",
        "PKU_RED_LIGHT": "#F3E5F8",
        "PKU_GOLD": "#9D4EDD",
        "INK": "#111827",
        "TEXT": "#4B5563",
        "MUTED": "#6B7280",
        "BORDER": "#E5E7EB",
        "SURFACE": "#FFFFFF",
        "BACKGROUND": "#F8F4FA",
    },
    "ocean_blue": {
        # Name kept as PKU_RED for backwards compatibility — semantically the
        # primary brand color slot, even when no longer red.
        "PKU_RED": "#1E40AF",
        "PKU_RED_DARK": "#1E3A8A",
        "PKU_RED_LIGHT": "#DBEAFE",
        "PKU_GOLD": "#0EA5E9",
        "INK": "#111827",
        "TEXT": "#4B5563",
        "MUTED": "#6B7280",
        "BORDER": "#E5E7EB",
        "SURFACE": "#FFFFFF",
        "BACKGROUND": "#EFF6FF",
    },
    "dark": {
        # 深色 palette 重新定位：用更深的红做主色（在白底卡片上对比度高），
        # 用深灰做窗口 BACKGROUND（视觉上"深色"），SURFACE 卡片仍保持浅底，
        # 这样：(a) 红色字在浅底上对比度最强；(b) 不需要改全项目 59 处硬编码
        # 白色卡片底；(c) 用户感受到"深色模式"，主要由窗口背景体现。
        "PKU_RED": "#7F1D1D",
        "PKU_RED_DARK": "#450A0A",
        "PKU_RED_LIGHT": "#FEE2E2",
        "PKU_GOLD": "#92400E",
        "INK": "#0F172A",
        "TEXT": "#1F2937",
        "MUTED": "#475569",
        "BORDER": "#94A3B8",
        "SURFACE": "#F8FAFC",
        "BACKGROUND": "#475569",
    },
}

PALETTE_LABELS = {
    "pku_red": "PKU 红（默认）",
    "thu_purple": "THU 紫",
    "ocean_blue": "海蓝",
    "dark": "深色",
}

DEFAULT_PALETTE = "pku_red"


def _read_active_palette_name() -> str:
    """Read which palette is active from a tiny standalone JSON-free file at
    ``data/.theme_palette``. We deliberately avoid the setting_repository here
    because ``theme`` is imported very early — before the facade is built."""
    from pathlib import Path
    try:
        path = Path("data") / ".theme_palette"
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value in PALETTES:
                return value
    except Exception:
        pass
    return DEFAULT_PALETTE


def _persist_palette_name(name: str) -> None:
    """Write the active palette name to ``data/.theme_palette``. Unknown
    names are silently ignored so callers can validate-by-trying."""
    from pathlib import Path
    if name not in PALETTES:
        return
    try:
        Path("data").mkdir(parents=True, exist_ok=True)
        (Path("data") / ".theme_palette").write_text(name, encoding="utf-8")
    except Exception:
        pass


_active = PALETTES[_read_active_palette_name()]
PKU_RED = _active["PKU_RED"]
PKU_RED_DARK = _active["PKU_RED_DARK"]
PKU_RED_LIGHT = _active["PKU_RED_LIGHT"]
PKU_GOLD = _active["PKU_GOLD"]
INK = _active["INK"]
TEXT = _active["TEXT"]
MUTED = _active["MUTED"]
BORDER = _active["BORDER"]
SURFACE = _active["SURFACE"]
BACKGROUND = _active["BACKGROUND"]


def primary_button_style() -> str:
    return f"""
    QPushButton {{
        background-color: {PKU_RED};
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {PKU_RED_DARK};
    }}
    QPushButton:disabled {{
        background-color: #C9B8B8;
        color: #F8F8F8;
    }}
    """


def secondary_button_style() -> str:
    return f"""
    QPushButton {{
        background-color: #FFFFFF;
        color: {PKU_RED};
        border: 1px solid {PKU_RED};
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {PKU_RED_LIGHT};
    }}
    """


def form_control_style() -> str:
    return f"""
    QDialog, QWidget {{
        background-color: {SURFACE};
        color: {INK};
    }}
    QLabel {{
        color: {TEXT};
        background-color: transparent;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit {{
        background-color: #FFFFFF;
        color: {INK};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 7px;
        selection-background-color: {PKU_RED_LIGHT};
        selection-color: {INK};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
        border-color: {PKU_RED};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled,
    QDateTimeEdit:disabled {{
        background-color: #F3F4F6;
        color: {MUTED};
        border-color: {BORDER};
    }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        color: {INK};
        selection-background-color: {PKU_RED_LIGHT};
        selection-color: {INK};
    }}
    QCheckBox, QRadioButton, QGroupBox {{
        color: {INK};
        background-color: transparent;
    }}
    QDialogButtonBox {{
        background-color: transparent;
    }}
    QDialogButtonBox QPushButton {{
        background-color: #FFFFFF;
        color: {PKU_RED};
        border: 1px solid {PKU_RED};
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 700;
        min-width: 72px;
    }}
    QDialogButtonBox QPushButton:hover {{
        background-color: {PKU_RED_LIGHT};
    }}
    """


def application_style() -> str:
    return f"""
    QWidget {{
        color: {INK};
    }}
    QToolTip {{
        background-color: {INK};
        color: #FFFFFF;
        border: none;
        padding: 4px 6px;
    }}
    QDialog, QMessageBox {{
        background-color: {SURFACE};
        color: {INK};
    }}
    QDialog QLabel, QMessageBox QLabel {{
        color: {TEXT};
        background-color: transparent;
    }}
    QMessageBox QPushButton {{
        background-color: #FFFFFF;
        color: {PKU_RED};
        border: 1px solid {PKU_RED};
        border-radius: 4px;
        padding: 6px 14px;
        min-width: 72px;
        font-weight: 700;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {PKU_RED_LIGHT};
    }}
    QMenu {{
        background-color: #FFFFFF;
        color: {INK};
        border: 1px solid {BORDER};
    }}
    QMenu::item {{
        background-color: transparent;
        color: {INK};
    }}
    QMenu::item:selected {{
        background-color: {PKU_RED_LIGHT};
        color: {PKU_RED};
    }}
    {form_control_style()}
    """
