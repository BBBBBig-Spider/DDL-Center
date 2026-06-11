from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.gui.schedule_widget import ScheduleWidget
from app.gui.ai_settings_dialog import AISettingsDialog
from app.gui.statistics_window import StatisticsWindow
from app.gui.task_list_widget import TaskListWidget
from app.gui.contact_page import ContactPage
from app.gui.general_settings_page import GeneralSettingsPage
from app.gui.theme import BACKGROUND, BORDER, INK, ACCENT, PRIMARY, PRIMARY_DARK, primary_button_style
from app.gui.widgets.ai_briefing_panel import AIBriefingPanel
from app.gui.widgets.ai_chat_panel import AIChatPanel
from app.services import credentials_store


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
        self._refresh_login_status()

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
        self.contact_page = ContactPage()
        self.general_settings_page = GeneralSettingsPage(self.facade)

        self.pages = {
            "tasks": self.task_list_page,
            "schedule": self.schedule_page,
            "statistics": self.statistics_page,
            "ai": self.ai_page,
            "general_settings": self.general_settings_page,
            "contact": self.contact_page,
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
                background-color: {PRIMARY_DARK};
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
                background-color: {PRIMARY};
                color: #FFFFFF;
            }}
            QPushButton[active="true"] {{
                background-color: {ACCENT};
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
        self.nav_buttons["general_settings"] = QPushButton("通用设置")
        self.nav_buttons["contact"] = QPushButton("联系作者")

        for button in self.nav_buttons.values():
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        layout.addStretch()

        self.login_card = QFrame()
        self.login_card.setObjectName("LoginCard")
        self.login_card.setStyleSheet(
            f"""
            QFrame#LoginCard {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px;
            }}
            QFrame#LoginCard QLabel {{
                color: #FFFFFF;
                background: transparent;
                font-size: 12px;
            }}
            QFrame#LoginCard QPushButton {{
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                text-align: center;
            }}
            QFrame#LoginCard QPushButton:hover {{
                background-color: {PRIMARY};
            }}
            """
        )
        self.login_card_layout = QVBoxLayout(self.login_card)
        self.login_card_layout.setContentsMargins(8, 8, 8, 8)
        self.login_card_layout.setSpacing(6)
        layout.addWidget(self.login_card)

        developer = QLabel("Developed by\n@Roast_Spider 小组")
        developer.setStyleSheet("color: #F3D9D9; font-size: 12px;")
        layout.addWidget(developer)
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
        self.open_ai_create_button = QPushButton("✨ 智能创建")
        for button in [self.open_settings_button, self.open_ai_create_button]:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(primary_button_style())
            actions.addWidget(button)
        layout.addLayout(actions)

        self.ai_chat_panel = AIChatPanel(facade=self.facade)
        layout.addWidget(self.ai_chat_panel, stretch=1)
        return page

    def _connect_signals(self) -> None:
        self.nav_buttons["tasks"].clicked.connect(lambda: self._switch_page("tasks"))
        self.nav_buttons["schedule"].clicked.connect(lambda: self._switch_page("schedule"))
        self.nav_buttons["statistics"].clicked.connect(lambda: self._switch_page("statistics"))
        self.nav_buttons["ai"].clicked.connect(lambda: self._switch_page("ai"))
        self.nav_buttons["general_settings"].clicked.connect(lambda: self._switch_page("general_settings"))
        self.nav_buttons["contact"].clicked.connect(lambda: self._switch_page("contact"))
        self.open_settings_button.clicked.connect(self._open_settings)
        self.open_ai_create_button.clicked.connect(self._open_ai_create_dialog)
        # Live-update the schedule's "current time" line color when the user
        # changes it in General Settings. The color itself is persisted via
        # setting_repository — this signal just nudges the widget to
        # re-render immediately rather than waiting for its 5-min timer.
        if hasattr(self.general_settings_page, "now_line_color_changed") and hasattr(
            self.schedule_page, "refresh_now_line"
        ):
            self.general_settings_page.now_line_color_changed.connect(
                self.schedule_page.refresh_now_line
            )
        # Refresh the login card avatar when the user changes it in settings.
        if hasattr(self.general_settings_page, "avatar_changed"):
            self.general_settings_page.avatar_changed.connect(self._on_avatar_changed)
        if hasattr(self.general_settings_page, "display_name_changed"):
            self.general_settings_page.display_name_changed.connect(
                lambda _name: self._refresh_login_status()
            )

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
        dialog = AISettingsDialog(facade=self.facade, parent=self)
        if dialog.exec() == AISettingsDialog.DialogCode.Accepted and hasattr(self.briefing_panel, "refresh"):
            self.briefing_panel.refresh()

    def _open_ai_create_dialog(self) -> None:
        from app.gui.ai_create_task_dialog import AICreateDialog
        dialog = AICreateDialog(self.facade, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            if hasattr(self.task_list_page, "refresh_display"):
                self.task_list_page.refresh_display()
            if hasattr(self.schedule_page, "refresh_schedule"):
                self.schedule_page.refresh_schedule()
            if hasattr(self.briefing_panel, "refresh"):
                self.briefing_panel.refresh()

    def _refresh_login_status(self) -> None:
        while self.login_card_layout.count():
            item = self.login_card_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()

        username, _ = credentials_store.load()
        if username:
            display = self._get_display_name() or username
            avatar_path = self._get_avatar_path()
            if avatar_path:
                from app.gui.general_settings_page import _make_circular_pixmap
                avatar_label = QLabel()
                avatar_label.setFixedSize(24, 24)
                avatar_label.setStyleSheet("background: transparent;")
                avatar_label.setPixmap(_make_circular_pixmap(avatar_path, 24))
                self.login_card_layout.addWidget(avatar_label)
                label = QLabel(display)
            else:
                label = QLabel(f"👤 {display}")
            label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600;")
            self.login_card_layout.addWidget(label)
            logout_btn = QPushButton("退出登录")
            logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            logout_btn.clicked.connect(self._handle_logout)
            self.login_card_layout.addWidget(logout_btn)
        else:
            label = QLabel("🔓 未登录")
            label.setStyleSheet("color: #FFFFFF; font-size: 12px;")
            self.login_card_layout.addWidget(label)
            login_btn = QPushButton("登录")
            login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            login_btn.clicked.connect(self._handle_login)
            self.login_card_layout.addWidget(login_btn)

    def _get_display_name(self) -> str:
        """Read the user-set display name (preferred over the bare username)."""
        repo = getattr(self.facade, "setting_repository", None)
        if repo is None:
            return ""
        try:
            value = repo.get("display_name", "")
        except Exception:
            return ""
        return value.strip() if isinstance(value, str) else ""

    def _get_avatar_path(self) -> str | None:
        """Read the persisted avatar path from setting_repository if any.

        Returns ``None`` when no path is set or the file no longer exists, so
        the login card falls back to the default emoji."""
        repo = getattr(self.facade, "setting_repository", None)
        if repo is None:
            return None
        try:
            value = repo.get("avatar_path", None)
        except Exception:
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        from pathlib import Path
        if not Path(value).is_file():
            return None
        return value

    def _on_avatar_changed(self, _path: str) -> None:
        self._refresh_login_status()

    def _handle_login(self) -> None:
        from app.gui.login_dialog import LoginDialog
        auth_client = None
        if hasattr(self.facade, "get_auth_client"):
            try:
                auth_client = self.facade.get_auth_client()
            except Exception:
                auth_client = None
        if auth_client is None:
            QMessageBox.warning(self, "无法登录", "登录服务不可用。")
            return
        if LoginDialog.run(self, auth_client):
            self._refresh_login_status()

    def _handle_logout(self) -> None:
        reply = QMessageBox.question(
            self,
            "退出登录并清除本地数据",
            "退出登录会清空所有本地数据，包括：\n"
            "  • 全部任务（手动添加的也会清）\n"
            "  • 全部课程、课表、考试\n"
            "  • 头像、显示名、主题、字号等所有偏好\n"
            "  • 保存的登录凭据\n\n"
            "唯一保留：DeepSeek API Key（系统密钥库）\n\n"
            "完成后应用会自动重启。确定继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.facade.logout_and_reset_local_state()
        except Exception as exc:
            QMessageBox.critical(self, "退出失败", str(exc))
            return

        # The facade's repositories are now stale (DB deleted). The cleanest
        # recovery is a process restart. We tell the user we're restarting,
        # spawn a fresh process, then exit this one.
        QMessageBox.information(
            self,
            "已清除本地数据",
            "本地数据已全部清空。点击确定后应用将重启。",
        )

        import subprocess

        # Re-launch the same Python entrypoint (`python -m app.main`).
        try:
            subprocess.Popen([sys.executable, "-m", "app.main"], close_fds=True)
        except Exception as exc:
            QMessageBox.critical(self, "重启失败",
                                 f"请手动重启应用。\n\n{exc}")
        QApplication.quit()


if __name__ == "__main__":
    from app.main import build_facade

    app = QApplication(sys.argv)
    window = MainWindow(build_facade())
    window.show()
    sys.exit(app.exec())
