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
