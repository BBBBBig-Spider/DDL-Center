import sys
from PySide6.QtWidgets import (QScrollArea, QVBoxLayout, QWidget, QHBoxLayout, QMenu, QComboBox,
                               QPushButton, QCheckBox, QLabel, QFrame, QApplication, QDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from datetime import datetime

from app.gui.task_list_widget import TaskCardWidget

class CourseColumnWidget(QFrame): 
    def __init__(self, course_id: int, course_name: str, tasks: list, facade, parent_board): 
        super().__init__()
        self.course_id = course_id
        self.course_name = course_name
        self.parent_board = parent_board

        self.init_ui(tasks)
    
    def init_ui(self, tasks):
        self.setFixedWidth(250)
        self.setStyleSheet("""
            CourseColumnWidget {
                background-color: #F4F5F7;
                border-radius: 6px;
            }
        """)
        column_layout = QVBoxLayout(self)
        column_layout.setContentsMargins(8, 8, 8, 8)
        column_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.course_name)
        lbl_title.setStyleSheet("color: #4D4D4D; font-weight: bold; font-size: 16px;")

        lbl_count = QLabel(f"{len(tasks)} 任务")
        lbl_count.setStyleSheet("""
            background-color: #E2E4E6; color: #4D4D4D; 
            padding: 2px 6px; border-radius: 10px; font-size: 11px; font-weight: bold;
        """)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(lbl_count)
        column_layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)    
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(12)
        self.list_layout.setContentsMargins(0, 0, 0, 0)

        for task in tasks: 
            card = TaskCardWidget(task, self.parent_board)
            self.list_layout.addWidget(card)

        scroll.setWidget(container)
        column_layout.addWidget(scroll)

class CourseBoardWidget(QWidget): 
    def __init__(self, facade = None):
        super().__init__()
        self.facade = facade
        self.task_manager = getattr(facade, "task_manager", None)

        self.status_combo = None

        self.init_ui()
        self.refresh_display()
    
    def init_ui(self): 
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel("按课程分类视图")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.board_container = QWidget()
        self.board_layout = QHBoxLayout(self.board_container)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(16)
        self.board_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.board_container)
        main_layout.addWidget(self.scroll_area)
    
    def refresh_display(self, filters=None): 
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.task_manager: 
            try: 
                courses = getattr(self.task_manager, "list_courses", lambda: [])()
                all_tasks = getattr(self.task_manager, "list_tasks", lambda filters=None: [])()
            except Exception as e: 
                print(f"Error fetching data from TaskManager: {e}")
                courses = []
                all_tasks = []
        
        else: 
            courses = [
                {"id": 101, "name": "高等数学A"},
                {"id": 202, "name": "程序设计实习"},
                {"id": 303, "name": "大学物理"}
            ]
            all_tasks = [
                {"id": 1, "title": "高数课后习题 1-5", "course_id": 101, "course_name": "高等数学A", "description": "周五前交", "due_time": datetime(2026, 5, 22), "estimated_hours": 2, "status": "to do", "priority": 1},
                {"id": 2, "title": "魔兽大作业：第一阶段", "course_id": 202, "course_name": "程序设计实习", "description": "多态与继承练习", "due_time": datetime(2026, 5, 25), "estimated_hours": 8, "status": "to do", "priority": 2},
                {"id": 3, "title": "期中模拟上机测验", "course_id": 202, "course_name": "程序设计实习", "description": "练习赛", "due_time": datetime(2026, 5, 28), "estimated_hours": 3, "status": "done", "priority": 3},
                {"id": 4, "title": "大物实验报告：单摆", "course_id": 303, "course_name": "大学物理", "description": "记得画误差分析图", "due_time": datetime(2026, 5, 24), "estimated_hours": 1, "status": "to do", "priority": 2}
            ]
        
        has_general_task = any(t.get("course_id") is None for t in all_tasks)
        if has_general_task:
            courses.append({"id": None, "name": "📅 通用任务"})

        for course in courses: 
            c_id = course.get("id")
            c_name = course.get("name", "未知课程")
            course_tasks = [t for t in all_tasks if t.get("course_id") == c_id]
            column_widget = CourseColumnWidget(c_id, c_name, course_tasks, self.facade, self)
            self.board_layout.addWidget(column_widget)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    board = CourseBoardWidget(facade=None)
    board.setWindowTitle("Week 2：课程看板独立调试")
    board.resize(900, 500)
    board.show()
    sys.exit(app.exec())