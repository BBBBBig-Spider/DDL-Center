from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import BORDER, INK, PKU_GOLD, PKU_RED, PKU_RED_DARK, PKU_RED_LIGHT, TEXT, secondary_button_style
from app.gui._helpers import get_field


class AlertItemWidget(QFrame):
    def __init__(self, alert_obj, parent=None):
        super().__init__(parent)
        self.alert_obj = alert_obj
        self.level = get_field(alert_obj, "level", "info")
        self.kind = get_field(alert_obj, "kind", "deadline")
        self.message = get_field(alert_obj, "message", "暂无提醒内容")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("alertItem")
        self.setMinimumHeight(54)

        color, bg_color, icon = self._level_style()
        self.setStyleSheet(
            f"""
            QFrame#alertItem {{
                background-color: {bg_color};
                border: 1px solid {color};
                border-radius: 6px;
            }}
            QFrame#alertItem:hover {{
                border-color: {PKU_RED_DARK};
            }}
            QFrame#alertItem QLabel {{
                background-color: transparent;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setFixedWidth(18)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {color};")
        layout.addWidget(icon_label)

        msg_label = QLabel(str(self.message))
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {INK};")
        layout.addWidget(msg_label, stretch=1)

    def _level_style(self) -> tuple[str, str, str]:
        if self.level in {"overdue", "urgent"}:
            return PKU_RED, PKU_RED_LIGHT, "!"
        if self.level == "warning" or self.kind == "overload":
            return PKU_GOLD, "#FFF7E0", "!"
        return "#6B7D3A", "#F1F3E8", "i"


class AlertPanel(QWidget):
    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self._init_ui()
        self.refresh_display()

    def _init_ui(self) -> None:
        self.setFixedWidth(300)
        self.setObjectName("alertPanel")
        self.setStyleSheet(
            """
            QWidget#alertPanel {
                background-color: transparent;
            }
            QWidget#alertPanel QLabel {
                background-color: transparent;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("alertHeader")
        header.setStyleSheet(
            f"""
            QFrame#alertHeader {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QFrame#alertHeader QLabel {{
                background-color: transparent;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 7, 10, 7)

        title = QLabel("提醒")
        title.setStyleSheet(f"color: {INK}; font-weight: 700; font-size: 13px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(secondary_button_style())
        self.btn_refresh.clicked.connect(self.refresh_display)
        header_layout.addWidget(self.btn_refresh)
        main_layout.addWidget(header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            """
        )

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

    def refresh_display(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        alerts = self._load_alerts()
        if not alerts:
            empty = QLabel("暂无提醒")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #9CA3AF; font-size: 12px; padding-top: 28px; background-color: transparent;")
            self.list_layout.addWidget(empty)
            return

        for alert in alerts:
            self.list_layout.addWidget(AlertItemWidget(alert))

    def _load_alerts(self):
        if not self.facade:
            return self._fallback_alerts()

        generated = []
        try:
            if hasattr(self.facade, "generate_alerts"):
                generated = self.facade.generate_alerts()
        except Exception as exc:
            print(f"[GUI] failed to generate alerts: {exc}")

        persisted = self._load_persisted_alerts()
        alerts = persisted if persisted is not None else generated
        return self._filter_stale_task_alerts(alerts)

    def _load_persisted_alerts(self):
        try:
            if hasattr(self.facade, "list_all_alerts"):
                return self.facade.list_all_alerts()

            alert_repository = getattr(self.facade, "alert_repository", None)
            if alert_repository:
                return alert_repository.list_all()

            alert_manager = getattr(self.facade, "alert_manager", None)
            alert_repository = getattr(alert_manager, "alert_repository", None)
            if alert_repository:
                return alert_repository.list_all()
        except Exception as exc:
            print(f"[GUI] failed to load persisted alerts: {exc}")
        return None

    def _filter_stale_task_alerts(self, alerts):
        task_ids = self._current_task_ids()
        if task_ids is None:
            return alerts

        filtered = []
        for alert in alerts:
            task_id = get_field(alert, "task_id")
            if task_id is None or task_id in task_ids:
                filtered.append(alert)
        return filtered

    def _current_task_ids(self):
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return None
        try:
            tasks = self.facade.list_tasks(None)
        except Exception as exc:
            print(f"[GUI] failed to load current tasks for alerts: {exc}")
            return None
        return {get_field(task, "id") for task in tasks if get_field(task, "id") is not None}

    @staticmethod
    def _fallback_alerts():
        return [
            {"level": "urgent", "kind": "deadline", "message": "高数习题将在 24 小时内截止。"},
            {"level": "warning", "kind": "deadline", "message": "未来三天有多个任务需要处理。"},
            {"level": "info", "kind": "progress", "message": "建议定期检查任务列表和推荐时间。"},
        ]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = AlertPanel(facade=None)
    panel.resize(320, 450)
    panel.show()
    sys.exit(app.exec())
