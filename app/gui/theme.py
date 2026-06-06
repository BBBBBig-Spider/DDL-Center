PKU_RED = "#8C1515"
PKU_RED_DARK = "#5F0F0F"
PKU_RED_LIGHT = "#F8EAEA"
PKU_GOLD = "#B8860B"
INK = "#111827"
TEXT = "#4B5563"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
SURFACE = "#FFFFFF"
BACKGROUND = "#F7F3F0"


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
        color: {INK};
    }}
    QLabel {{
        color: {TEXT};
        background-color: transparent;
    }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateTimeEdit {{
        background-color: #FFFFFF;
        color: {INK};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 7px;
        selection-background-color: {PKU_RED_LIGHT};
        selection-color: {INK};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateTimeEdit:focus {{
        border-color: {PKU_RED};
    }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        color: {INK};
        selection-background-color: {PKU_RED_LIGHT};
        selection-color: {INK};
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
