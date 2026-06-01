import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget, QPushButton


class AlertItemWidget(QFrame):
    def __init__(self, alert_obj):
        super().__init__()
        self.level = self._get_field(alert_obj, "level", "info")
        self.kind = self._get_field(alert_obj, "kind", "deadline")
        self.message = self._get_field(alert_obj, "message", "暂无提醒内容")
        self.init_ui()

    @staticmethod
    def _get_field(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def init_ui(self):
        self.setMinimumHeight(50)

        styles = {
            "overdue": ("!", "#FF4D4F", "#FFF1F0"),
            "urgent": ("!", "#FF4D4F", "#FFF1F0"),
            "warning": ("i", "#FAAD14", "#FFFBE6"),
            "info": ("i", "#1890FF", "#E6F7FF"),
        }
        icon_str, color, bg_color = styles.get(self.level, styles["info"])
        if self.kind == "overload":
            icon_str = "!"

        self.setStyleSheet(
            f"""
            AlertItemWidget {{
                background-color: {bg_color};
                border: 1px solid {color}80;
                border-radius: 6px;
            }}
            AlertItemWidget:hover {{
                border: 1px solid {color};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        lbl_icon = QLabel(icon_str)
        lbl_icon.setFixedWidth(16)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")
        layout.addWidget(lbl_icon)

        lbl_msg = QLabel(self.message)
        text_color = color if self.level in ["overdue", "urgent"] else "#333"
        lbl_msg.setStyleSheet(f"font-weight: 500; font-size: 12px; color: {text_color};")
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg, stretch=1)


class AlertPanel(QWidget):
    def __init__(self, facade=None):
        super().__init__()
        self.facade = facade
        self.init_ui()
        self.refresh_display()

    def init_ui(self):
        self.setFixedWidth(300)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(6)

        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 4px; border: 1px solid #E8E8E8;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(8, 6, 8, 6)

        lbl_panel_title = QLabel("提醒")
        lbl_panel_title.setStyleSheet("color: #262626; font-weight: bold; font-size: 12px;")
        title_layout.addWidget(lbl_panel_title)

        title_layout.addStretch()  
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #595959;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FAFAFA;
                color: #262626;
                border-color: #40A9FF; 
            }
            QPushButton:pressed {
                background-color: #F0F0F0;
            }
        """
        )

        self.btn_refresh.clicked.connect(self.refresh_display)
        title_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(title_frame)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 4, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh_display(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts_data = self._load_alerts()

        if not alerts_data:
            lbl_empty = QLabel("暂无提醒")
            lbl_empty.setStyleSheet("color: #BFBFBF; font-size: 12px; font-style: italic; margin-top: 20px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl_empty)
            return

        for alert in alerts_data:
            self.list_layout.addWidget(AlertItemWidget(alert))

    def _load_alerts(self):
        if not self.facade:
            return self._fallback_alerts()

        generated = []
        try:
            if hasattr(self.facade, "generate_alerts"):
                generated = self.facade.generate_alerts()
        except Exception as exc:
            print(f"[GUI Error] AlertPanel failed to generate alerts: {exc}")

        persisted = self._load_persisted_alerts()
        if persisted is not None:
            return self._filter_stale_task_alerts(persisted)
        return self._filter_stale_task_alerts(generated)

    def _load_persisted_alerts(self):
        try:
            if hasattr(self.facade, "list_all_alerts"):
                return self.facade.list_all_alerts()
            if hasattr(self.facade, "alert_repository") and self.facade.alert_repository:
                return self.facade.alert_repository.list_all()

            alert_manager = getattr(self.facade, "alert_manager", None)
            alert_repository = getattr(alert_manager, "alert_repository", None)
            if alert_repository:
                return alert_repository.list_all()
        except Exception as exc:
            print(f"[GUI Error] AlertPanel failed to load persisted alerts: {exc}")
        return None

    def _filter_stale_task_alerts(self, alerts):
        task_ids = self._current_task_ids()
        if task_ids is None:
            return alerts

        filtered = []
        for alert in alerts:
            task_id = self._get_field(alert, "task_id")
            if task_id is None or task_id in task_ids:
                filtered.append(alert)
        return filtered

    def _current_task_ids(self):
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return None
        try:
            tasks = self.facade.list_tasks(None)
        except Exception as exc:
            print(f"[GUI Error] AlertPanel failed to load current tasks: {exc}")
            return None

        ids = set()
        for task in tasks:
            task_id = self._get_field(task, "id")
            if task_id is not None:
                ids.add(task_id)
        return ids

    @staticmethod
    def _get_field(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _fallback_alerts():
        return [
            {"level": "urgent", "kind": "deadline", "message": "A task is due soon."},
            {"level": "warning", "kind": "deadline", "message": "Several tasks are approaching their deadlines."},
            {"level": "info", "kind": "progress", "message": "Keep reviewing your task list regularly."},
        ]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = AlertPanel(facade=None)
    panel.setWindowTitle("AlertPanel Debug")
    panel.resize(320, 450)
    panel.show()
    sys.exit(app.exec())
