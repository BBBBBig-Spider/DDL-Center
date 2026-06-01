import sys
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget

from app.gui.task_list_widget import TaskCardWidget


def get_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class TimelineSectionWidget(QFrame):
    def __init__(self, title, color, tasks, parent_timeline):
        super().__init__()
        self.title = title
        self.color = color
        self.tasks = tasks
        self.parent_timeline = parent_timeline
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        self.axis_widget = QWidget()
        self.axis_widget.setFixedWidth(40)
        self.axis_widget.paintEvent = self._draw_timeline_axis
        main_layout.addWidget(self.axis_widget)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 5, 0, 15)

        section_label = QLabel(f"{self.title} ({len(self.tasks)})" if self.tasks else self.title)
        section_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self.color};")
        content_layout.addWidget(section_label)

        if not self.tasks:
            empty_label = QLabel("当前时段没有任务")
            empty_label.setStyleSheet("color: #999; font-size: 12px; font-style: italic; padding-left: 5px;")
            content_layout.addWidget(empty_label)
        else:
            for task in self.tasks:
                content_layout.addWidget(TaskCardWidget(task, self.parent_timeline))

        main_layout.addLayout(content_layout)

    def _draw_timeline_axis(self, event):
        painter = QPainter(self.axis_widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.axis_widget.width() // 2
        height = self.axis_widget.height()

        painter.setPen(QPen(QColor("#E8E8E8"), 2, Qt.PenStyle.SolidLine))
        painter.drawLine(center_x, 0, center_x, height)

        node_color = QColor(self.color)
        painter.setBrush(node_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - 6, 12, 12, 12)

        if self.tasks:
            glow_color = QColor(node_color)
            glow_color.setAlpha(50)
            painter.setBrush(glow_color)
            painter.drawEllipse(center_x - 10, 8, 20, 20)

        painter.end()


class TimelineWidget(QWidget):
    def __init__(self, facade=None):
        super().__init__()
        self.facade = facade
        self.current_filters = None

        self.init_ui()
        self.refresh_display()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel("Timeline")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.timeline_layout = QVBoxLayout(container)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)

        self.scroll_area.setWidget(container)
        main_layout.addWidget(self.scroll_area)

    def refresh_display(self, filters=None):
        if filters is None:
            filters = self.current_filters
        else:
            self.current_filters = filters

        self._clear_sections()
        tasks = self._load_tasks(filters)
        today, tomorrow, this_week, future = self._group_tasks(tasks)

        self.timeline_layout.addWidget(TimelineSectionWidget("Today", "#FF6B6B", today, self))
        self.timeline_layout.addWidget(TimelineSectionWidget("Tomorrow", "#FFA94D", tomorrow, self))
        self.timeline_layout.addWidget(TimelineSectionWidget("This Week", "#4D96FF", this_week, self))
        self.timeline_layout.addWidget(TimelineSectionWidget("Future", "#AAAAAA", future, self))
        self.timeline_layout.addStretch()

    def _clear_sections(self):
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_tasks(self, filters):
        if self.facade:
            try:
                return self.facade.list_tasks(filters)
            except Exception as exc:
                print(f"TimelineWidget failed to load tasks from Facade: {exc}")
                return []

        tasks = self._fallback_tasks()
        status = (filters or {}).get("status")
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        return tasks

    @staticmethod
    def _group_tasks(tasks):
        today_date = datetime.now().date()
        tomorrow_date = today_date + timedelta(days=1)
        this_week_sunday = today_date + timedelta(days=(6 - today_date.weekday()) % 7)

        today = []
        tomorrow = []
        this_week = []
        future = []

        for task in tasks:
            due_time = get_field(task, "due_time")
            if isinstance(due_time, str):
                try:
                    due_time = datetime.fromisoformat(due_time)
                except ValueError:
                    due_time = None

            if not isinstance(due_time, datetime):
                future.append(task)
                continue

            due_date = due_time.date()
            if due_date <= today_date:
                today.append(task)
            elif due_date == tomorrow_date:
                tomorrow.append(task)
            elif tomorrow_date < due_date <= this_week_sunday:
                this_week.append(task)
            else:
                future.append(task)

        return today, tomorrow, this_week, future

    @staticmethod
    def _fallback_tasks():
        return [
            {
                "id": 1,
                "title": "Math assignment",
                "course_name": "Advanced Mathematics",
                "due_time": datetime(2026, 6, 1, 12, 0),
                "status": "todo",
                "priority": 1,
            },
            {
                "id": 2,
                "title": "Programming project",
                "course_name": "Programming Practice",
                "due_time": datetime(2026, 6, 3, 23, 59),
                "status": "todo",
                "priority": 2,
            },
            {
                "id": 3,
                "title": "Physics lab report",
                "course_name": "College Physics",
                "due_time": datetime(2026, 6, 5, 18, 0),
                "status": "done",
                "priority": 3,
            },
        ]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    timeline = TimelineWidget(facade=None)
    timeline.setWindowTitle("TimelineWidget Debug")
    timeline.resize(900, 500)
    timeline.show()
    sys.exit(app.exec())
