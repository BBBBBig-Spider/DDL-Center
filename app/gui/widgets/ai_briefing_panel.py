from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.gui.theme import BORDER, INK, PRIMARY, PRIMARY_LIGHT, TEXT
from app.gui._helpers import get_field


class AIBriefingPanel(QFrame):
    """Compact daily briefing panel for the main window.

    It only calls AppFacade-compatible methods. When AI is not implemented, it
    falls back to a deterministic local summary built from tasks and alerts.
    """

    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.setObjectName("aiBriefingPanel")
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#aiBriefingPanel {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.title_label = QLabel("AI 每日简报")
        self.title_label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {INK};")

        self.content_label = QLabel("")
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"font-size: 12px; color: {TEXT};")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.content_label)
        layout.addLayout(text_layout, stretch=1)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setFixedWidth(64)
        self.refresh_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {PRIMARY};
                border: 1px solid {PRIMARY};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_LIGHT};
            }}
            """
        )
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignTop)

    def refresh(self) -> None:
        text = self._load_ai_briefing()
        if not text:
            text = self._build_local_briefing()
        self.content_label.setText(text)

    def _load_ai_briefing(self) -> str:
        if not self.facade or not hasattr(self.facade, "ai_generate_briefing"):
            return ""
        try:
            if hasattr(self.facade, "ai_is_available") and not self.facade.ai_is_available():
                return ""
            return str(self.facade.ai_generate_briefing() or "").strip()
        except NotImplementedError:
            return ""
        except Exception as exc:
            print(f"[GUI] failed to load AI briefing: {exc}")
            return ""

    def _build_local_briefing(self) -> str:
        tasks = self._safe_list_tasks()
        alerts = self._safe_generate_alerts()
        active_tasks = [task for task in tasks if get_field(task, "status") != "done"]
        now = datetime.now()
        urgent_tasks = [
            task
            for task in active_tasks
            if isinstance(get_field(task, "due_time"), datetime)
            and now <= get_field(task, "due_time") <= now + timedelta(days=1)
        ]
        overdue_tasks = [
            task
            for task in active_tasks
            if isinstance(get_field(task, "due_time"), datetime)
            and get_field(task, "due_time") < now
        ]

        if overdue_tasks:
            first = get_field(overdue_tasks[0], "title", "未命名任务")
            return f"今日优先处理：{first} 已逾期。当前共有 {len(active_tasks)} 个未完成任务，建议先清理红色提醒。"
        if urgent_tasks:
            first = get_field(urgent_tasks[0], "title", "未命名任务")
            return f"今日重点：{first} 将在 24 小时内截止。建议在课表空闲段中预留整块时间。"
        if alerts:
            return f"今日提醒：系统检测到 {len(alerts)} 条提醒。建议从任务列表右侧推荐时间开始安排。"
        if active_tasks:
            return f"今日节奏稳定：仍有 {len(active_tasks)} 个未完成任务，可以优先推进预计耗时最长的一项。"
        return "今日暂无待办压力，可以检查课表和后续 DDL。"

    def _safe_list_tasks(self) -> list:
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return []
        try:
            return list(self.facade.list_tasks(None))
        except Exception:
            return []

    def _safe_generate_alerts(self) -> list:
        if not self.facade or not hasattr(self.facade, "generate_alerts"):
            return []
        try:
            return list(self.facade.generate_alerts())
        except Exception:
            return []
