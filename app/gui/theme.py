# ── Real color constants (used to compose palettes) ─────────────
# Each constant is a literal hex; named after its actual hue, NOT after
# whatever role it plays in any specific palette.
PKU_RED = "#8C1515"
PKU_RED_DEEP = "#5F0F0F"
PKU_RED_BLUSH = "#F8EAEA"
PKU_GOLD = "#B8860B"

THU_PURPLE = "#660874"
THU_PURPLE_DEEP = "#4A0654"
THU_PURPLE_BLUSH = "#F3E5F8"
THU_PURPLE_ACCENT = "#9D4EDD"

OCEAN_BLUE = "#1E40AF"
OCEAN_BLUE_DEEP = "#1E3A8A"
OCEAN_BLUE_BLUSH = "#DBEAFE"
SKY_CYAN = "#0EA5E9"

DARK_RED = "#7F1D1D"
DARK_RED_DEEP = "#450A0A"
DARK_RED_BLUSH = "#FEE2E2"
AMBER_BROWN = "#92400E"

# ── Palettes: map a theme name to its 10 semantic color slots ───
# Slot semantics (NOT brand-specific):
#   PRIMARY        — main brand/accent color (buttons, headings)
#   PRIMARY_DARK   — hover / pressed state of PRIMARY
#   PRIMARY_LIGHT  — soft tint for selection / hover backgrounds
#   ACCENT         — secondary accent (highlights, badges)
#   INK / TEXT / MUTED — text colors (high → low contrast)
#   BORDER         — neutral divider color
#   SURFACE        — card / dialog background
#   BACKGROUND     — window / page background
PALETTES = {
    "pku_red": {
        "PRIMARY": PKU_RED,
        "PRIMARY_DARK": PKU_RED_DEEP,
        "PRIMARY_LIGHT": PKU_RED_BLUSH,
        "ACCENT": PKU_GOLD,
        "INK": "#111827",
        "TEXT": "#4B5563",
        "MUTED": "#6B7280",
        "BORDER": "#E5E7EB",
        "SURFACE": "#FFFFFF",
        "BACKGROUND": "#F7F3F0",
    },
    "thu_purple": {
        "PRIMARY": THU_PURPLE,
        "PRIMARY_DARK": THU_PURPLE_DEEP,
        "PRIMARY_LIGHT": THU_PURPLE_BLUSH,
        "ACCENT": THU_PURPLE_ACCENT,
        "INK": "#111827",
        "TEXT": "#4B5563",
        "MUTED": "#6B7280",
        "BORDER": "#E5E7EB",
        "SURFACE": "#FFFFFF",
        "BACKGROUND": "#F8F4FA",
    },
    "ocean_blue": {
        "PRIMARY": OCEAN_BLUE,
        "PRIMARY_DARK": OCEAN_BLUE_DEEP,
        "PRIMARY_LIGHT": OCEAN_BLUE_BLUSH,
        "ACCENT": SKY_CYAN,
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
        "PRIMARY": DARK_RED,
        "PRIMARY_DARK": DARK_RED_DEEP,
        "PRIMARY_LIGHT": DARK_RED_BLUSH,
        "ACCENT": AMBER_BROWN,
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
PRIMARY = _active["PRIMARY"]
PRIMARY_DARK = _active["PRIMARY_DARK"]
PRIMARY_LIGHT = _active["PRIMARY_LIGHT"]
ACCENT = _active["ACCENT"]
INK = _active["INK"]
TEXT = _active["TEXT"]
MUTED = _active["MUTED"]
BORDER = _active["BORDER"]
SURFACE = _active["SURFACE"]
BACKGROUND = _active["BACKGROUND"]


def primary_button_style() -> str:
    return f"""
    QPushButton {{
        background-color: {PRIMARY};
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_DARK};
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
        color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_LIGHT};
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
        selection-background-color: {PRIMARY_LIGHT};
        selection-color: {INK};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
        border-color: {PRIMARY};
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
        selection-background-color: {PRIMARY_LIGHT};
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
        color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 700;
        min-width: 72px;
    }}
    QDialogButtonBox QPushButton:hover {{
        background-color: {PRIMARY_LIGHT};
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
        color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: 4px;
        padding: 6px 14px;
        min-width: 72px;
        font-weight: 700;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {PRIMARY_LIGHT};
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
        background-color: {PRIMARY_LIGHT};
        color: {PRIMARY};
    }}
    {form_control_style()}
    """
