from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.gui.schedule_widget import ScheduleWidget
from app.gui.settings_dialog import SettingsDialog
from app.gui.statistics_window import StatisticsWindow
from app.gui.sync_dialog import SyncDialog
from app.gui.task_list_widget import TaskListWidget
from app.gui.theme import BACKGROUND, BORDER, INK, PKU_GOLD, PKU_RED, PKU_RED_DARK, primary_button_style
from app.gui.widgets.ai_briefing_panel import AIBriefingPanel
from app.gui.widgets.ai_chat_panel import AIChatPanel


class MainWindow(QMainWindow):
    def __init__(self, facade):
        super().__init__()
        self.facade = facade
        self.nav_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle("DDL 指挥中心")
        self.resize(1120, 760)
        self._init_ui()
        self._connect_signals()
        self._switch_page("tasks")

    def _init_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {BACKGROUND};")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        self.briefing_panel = AIBriefingPanel(facade=self.facade)
        content_layout.addWidget(self.briefing_panel)

        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet(
            f"""
            QStackedWidget {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            """
        )
        content_layout.addWidget(self.content_area, stretch=1)

        self.task_list_page = TaskListWidget(facade=self.facade)
        self.schedule_page = ScheduleWidget(facade=self.facade)
        self.statistics_page = StatisticsWindow(facade=self.facade)
        self.ai_page = self._build_ai_page()
        self.sync_page = self._build_sync_page()

        self.pages = {
            "tasks": self.task_list_page,
            "schedule": self.schedule_page,
            "statistics": self.statistics_page,
            "ai": self.ai_page,
            "sync": self.sync_page,
        }
        for page in self.pages.values():
            self.content_area.addWidget(page)

        root_layout.addWidget(content_widget, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(178)
        sidebar.setStyleSheet(
            f"""
            QFrame#sidebar {{
                background-color: {PKU_RED_DARK};
                border: none;
            }}
            QLabel {{
                color: #FFFFFF;
                background: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                color: #D1D5DB;
                border: none;
                border-radius: 4px;
                padding: 10px 12px;
                text-align: left;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {PKU_RED};
                color: #FFFFFF;
            }}
            QPushButton[active="true"] {{
                background-color: {PKU_GOLD};
                color: #FFFFFF;
                font-weight: 700;
            }}
            """
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(8)

        brand = QLabel("DDL 指挥中心")
        brand.setStyleSheet("font-size: 16px; font-weight: 700; padding-bottom: 10px;")
        layout.addWidget(brand)

        self.nav_buttons["tasks"] = QPushButton("任务管理")
        self.nav_buttons["schedule"] = QPushButton("课程表")
        self.nav_buttons["statistics"] = QPushButton("进度统计")
        self.nav_buttons["ai"] = QPushButton("AI 助手")
        self.nav_buttons["sync"] = QPushButton("同步")

        for button in self.nav_buttons.values():
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        layout.addStretch()
        status = QLabel("真实接口模式")
        status.setStyleSheet("color: #F3D9D9; font-size: 12px;")
        layout.addWidget(status)
        return sidebar

    def _build_ai_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        actions = QHBoxLayout()
        title = QLabel("AI 助手")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        actions.addWidget(title)
        actions.addStretch()

        self.open_settings_button = QPushButton("AI 设置")
        self.open_sync_button = QPushButton("同步教学网")
        for button in [self.open_settings_button, self.open_sync_button]:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(primary_button_style())
            actions.addWidget(button)
        layout.addLayout(actions)

        self.ai_chat_panel = AIChatPanel(facade=self.facade)
        layout.addWidget(self.ai_chat_panel, stretch=1)
        return page

    def _build_sync_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        title = QLabel("教学网同步")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        body = QLabel("真实网络同步由后端负责。GUI 只打开同步对话框，并显示 facade 返回的结果。")
        body.setWordWrap(True)
        body.setStyleSheet("font-size: 13px; color: #4B5563;")
        open_button = QPushButton("打开同步窗口")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self._open_sync_dialog)
        open_button.setStyleSheet(primary_button_style() + "QPushButton { max-width: 140px; }")

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(open_button)
        layout.addStretch()
        return page

    def _connect_signals(self) -> None:
        self.nav_buttons["tasks"].clicked.connect(lambda: self._switch_page("tasks"))
        self.nav_buttons["schedule"].clicked.connect(lambda: self._switch_page("schedule"))
        self.nav_buttons["statistics"].clicked.connect(lambda: self._switch_page("statistics"))
        self.nav_buttons["ai"].clicked.connect(lambda: self._switch_page("ai"))
        self.nav_buttons["sync"].clicked.connect(lambda: self._switch_page("sync"))
        self.open_settings_button.clicked.connect(self._open_settings)
        self.open_sync_button.clicked.connect(self._open_sync_dialog)

    def _switch_page(self, page_key: str) -> None:
        page = self.pages[page_key]
        self.content_area.setCurrentWidget(page)
        self._set_active_button(page_key)
        self._refresh_page(page)

    def _set_active_button(self, active_key: str) -> None:
        for key, button in self.nav_buttons.items():
            button.setProperty("active", key == active_key)
            button.style().unpolish(button)
            button.style().polish(button)

    def _refresh_page(self, page: QWidget) -> None:
        if hasattr(self.briefing_panel, "refresh"):
            self.briefing_panel.refresh()
        if hasattr(page, "refresh_display"):
            page.refresh_display()
        elif hasattr(page, "refresh_schedule"):
            page.refresh_schedule()
        elif hasattr(page, "refresh"):
            page.refresh()

    def switch_to_task_list(self) -> None:
        self._switch_page("tasks")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(facade=self.facade, parent=self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted and hasattr(self.briefing_panel, "refresh"):
            self.briefing_panel.refresh()

    def _open_sync_dialog(self) -> None:
        dialog = SyncDialog(facade=self.facade, parent=self)
        dialog.exec()
        if hasattr(self.task_list_page, "refresh_display"):
            self.task_list_page.refresh_display()
        if hasattr(self.schedule_page, "refresh_schedule"):
            self.schedule_page.refresh_schedule()
        if hasattr(self.statistics_page, "refresh"):
            self.statistics_page.refresh()
        if hasattr(self.briefing_panel, "refresh"):
            self.briefing_panel.refresh()


if __name__ == "__main__":
    from app.main import build_facade

    app = QApplication(sys.argv)
    window = MainWindow(build_facade())
    window.show()
    sys.exit(app.exec())
