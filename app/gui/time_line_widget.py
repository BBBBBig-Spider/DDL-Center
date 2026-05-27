import sys
from PySide6.QtWidgets import (QScrollArea, QVBoxLayout, QWidget, QHBoxLayout, QMenu, QComboBox,
                               QPushButton, QCheckBox, QLabel, QFrame, QApplication, QDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from datetime import datetime, timedelta

from app.gui.task_list_widget import TaskCardWidget

class CourseColumnWidget(QFrame): 
    def __init__(self, title, color_str, tasks, parent_timeline): 
        super().__init__()
        self.title = title
        self.color_str = color_str
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

        lbl_section = QLabel(f"{self.title} ({len(self.tasks)})" if self.tasks else self.title)
        lbl_section.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self.color_str};")
        content_layout.addWidget(lbl_section)

        if not self.tasks: 
            lbl_empty = QLabel("哇塞！这个阶段没有待办任务，真棒！")
            lbl_empty.setStyleSheet("color: #999; font-size: 12px; font-style: italic; padding-left: 5px;")
            content_layout.addWidget(lbl_empty)
        else: 
            for task in self.tasks: 
                card = TaskCardWidget(task, self.parent_timeline)
                content_layout.addWidget(card)
        
        main_layout.addLayout(content_layout)
    
    def _draw_timeline_axis(self, event):
        painter = QPainter(self.axis_widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.axis_widget.width()
        h = self.axis_widget.height()
        center_x = w // 2

        pen = QPen(QColor("#E8E8E8"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(center_x, 0, center_x, h)

        node_color = QColor(self.color_str)
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
    def __init__(self, facade = None): 
        super().__init__()
        self.facade = facade
        self.task_manager = getattr(facade, "task_manager", facade)
        
        self.status_combo = None

        self.init_ui()
        self.refresh_display()

    def init_ui(self): 
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel("按时间线视图")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)    
        
        container = QWidget()
        self.timeline_layout = QVBoxLayout(container)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)

        self.scroll_area.setWidget(container)
        main_layout.addWidget(self.scroll_area)
    
    def refresh_display(self, filters = None): 
        while self.timeline_layout.count(): 
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        all_tasks = []
        if self.task_manager: 
            try: 
                all_tasks = getattr(self.task_manager, "list_tasks", lambda f=None: [])(filters)
            except Exception as e: 
                print(f"Error fetching tasks for timeline: {e}")
        
        else: 
            all_tasks = [
                {"id": 1, "title": "高数超期作业！", "course_name": "高等数学A", "due_time": datetime(2026, 5, 20, 12, 0), "status": "to do", "priority": 1},
                {"id": 2, "title": "程序设计：魔兽大作业一期", "course_name": "程序设计实习", "due_time": datetime(2026, 5, 21, 23, 59), "status": "to do", "priority": 1},
                {"id": 3, "title": "AI引论的lab", "course_name": "人工智能引论", "due_time": datetime(2026, 5, 22, 18, 0), "status": "to do", "priority": 2},
                {"id": 4, "title": "周日晚上截止的xigai论文", "course_name": "通用任务", "due_time": datetime(2026, 5, 24, 21, 0), "status": "to do", "priority": 3},
                {"id": 5, "title": "English", "course_name": "null", "due_time": datetime(2026, 5, 28, 10, 0), "status": "to do", "priority": 2},
            ]
            if filters and "status" in filters:
                all_tasks = [t for t in all_tasks if t.get("status") == filters["status"]]
        
    
        
        now = datetime.now()
        today_date = now.date()
        tomorrow_date = today_date + timedelta(days=1)
        days_to_sunday = (6 - today_date.weekday()) % 7
        this_week_sunday = today_date + timedelta(days=days_to_sunday)

        today_tasks = []
        tomorrow_tasks = []
        this_week_tasks = []
        future_tasks = []

        for task in all_tasks:
            dt = task.get("due_time") if isinstance(task, dict) else getattr(task, "due_time", None)

            if isinstance(dt, str):
                try: dt = datetime.fromisoformat(dt)
                except: continue
            
            if not isinstance(dt, datetime):
                future_tasks.append(task)
                continue
                
            task_date = dt.date()

            if task_date <= today_date:
                today_tasks.append(task)
            elif task_date == tomorrow_date:
                tomorrow_tasks.append(task)
            elif tomorrow_date <= task_date <= this_week_sunday:
                this_week_tasks.append(task)
            else:
                future_tasks.append(task)
        
        self.timeline_layout.addWidget(CourseColumnWidget("今天", "#FF6B6B", today_tasks, self))
        self.timeline_layout.addWidget(CourseColumnWidget("明天", "#FFA94D", tomorrow_tasks, self))
        self.timeline_layout.addWidget(CourseColumnWidget("本周", "#4D96FF", this_week_tasks, self))
        self.timeline_layout.addWidget(CourseColumnWidget("未来", "#AAAAAA", future_tasks, self))

        self.timeline_layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    board = TimelineWidget(facade=None)
    board.setWindowTitle("Week 2：时间线视图独立调试")
    board.resize(900, 500)
    board.show()
    sys.exit(app.exec())