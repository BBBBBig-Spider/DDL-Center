import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.gui.task_list_widget import TaskCardWidget


def get_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class CourseColumnWidget(QFrame):
    def __init__(self, course_id: int | None, course_name: str, tasks: list, facade, parent_board):
        super().__init__()
        self.course_id = course_id
        self.course_name = course_name
        self.facade = facade
        self.parent_board = parent_board
        self.init_ui(tasks)

    def init_ui(self, tasks):
        self.setFixedWidth(250)
        self.setStyleSheet(
            """
            CourseColumnWidget {
                background-color: #F4F5F7;
                border-radius: 6px;
            }
            """
        )
        column_layout = QVBoxLayout(self)
        column_layout.setContentsMargins(8, 8, 8, 8)
        column_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.course_name)
        lbl_title.setStyleSheet("color: #4D4D4D; font-weight: bold; font-size: 16px;")

        lbl_count = QLabel(f"{len(tasks)} tasks")
        lbl_count.setStyleSheet(
            """
            background-color: #E2E4E6; color: #4D4D4D;
            padding: 2px 6px; border-radius: 10px; font-size: 11px; font-weight: bold;
            """
        )

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(lbl_count)
        column_layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        list_layout = QVBoxLayout(container)
        list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        list_layout.setSpacing(12)
        list_layout.setContentsMargins(0, 0, 0, 0)

        for task in tasks:
            list_layout.addWidget(TaskCardWidget(task, self.parent_board))

        list_layout.addStretch()
        scroll.setWidget(container)
        column_layout.addWidget(scroll)


class CourseBoardWidget(QWidget):
    def __init__(self, facade=None):
        super().__init__()
        self.facade = facade
        self.task_manager = getattr(facade, "task_manager", None)
        self.status_combo = None
        self.current_filters = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel("按课程分类")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.board_container = QWidget()
        self.board_layout = QHBoxLayout(self.board_container)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(16)
        self.board_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.board_container)
        main_layout.addWidget(self.scroll_area)

    def refresh_display(self, filters=None):
        if filters is None:
            filters = self.current_filters
        else:
            self.current_filters = filters

        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_tasks = self._load_tasks(filters)
        courses = self._load_courses(all_tasks)

        if self.facade is None and not all_tasks and not courses:
            all_tasks = self._fallback_tasks(filters)
            courses = self._derive_courses_from_tasks(all_tasks)

        if any(get_field(task, "course_id") is None for task in all_tasks):
            courses = list(courses)
            courses.append({"id": None, "name": "通用任务"})

        for course in courses:
            c_id = get_field(course, "id")
            c_name = get_field(course, "name", "未知课程")
            course_tasks = [task for task in all_tasks if get_field(task, "course_id") == c_id]
            self.board_layout.addWidget(CourseColumnWidget(c_id, c_name, course_tasks, self.facade, self))

        self.board_layout.addStretch()

    def _load_tasks(self, filters):
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return []
        try:
            return self.facade.list_tasks(filters)
        except Exception as exc:
            print(f"Error fetching tasks from Facade: {exc}")
            return []

    def _load_courses(self, tasks):
        courses = []
        if self.facade and hasattr(self.facade, "list_courses"):
            try:
                courses = self.facade.list_courses()
            except NotImplementedError:
                courses = []
            except Exception as exc:
                print(f"Error fetching courses from Facade: {exc}")
        elif self.task_manager and hasattr(self.task_manager, "list_courses"):
            try:
                courses = self.task_manager.list_courses()
            except NotImplementedError:
                courses = []
            except Exception as exc:
                print(f"Error fetching courses from TaskManager: {exc}")

        return courses or self._derive_courses_from_tasks(tasks)

    @staticmethod
    def _derive_courses_from_tasks(tasks):
        courses = []
        seen = set()
        for task in tasks:
            c_id = get_field(task, "course_id")
            c_name = get_field(task, "course_name")
            if c_id is None or c_id in seen:
                continue
            seen.add(c_id)
            courses.append({"id": c_id, "name": c_name or f"Course {c_id}"})
        return courses

    @staticmethod
    def _fallback_tasks(filters=None):
        tasks = [
            {
                "id": 1,
                "title": "Math problem set",
                "course_id": 101,
                "course_name": "Advanced Mathematics",
                "description": "Practice problems",
                "due_time": datetime(2026, 6, 1, 23, 59),
                "estimated_hours": 2,
                "status": "todo",
                "priority": 1,
            },
            {
                "id": 2,
                "title": "Programming project",
                "course_id": 202,
                "course_name": "Programming Practice",
                "description": "First milestone",
                "due_time": datetime(2026, 6, 3, 12, 0),
                "estimated_hours": 8,
                "status": "todo",
                "priority": 2,
            },
            {
                "id": 3,
                "title": "Physics lab report",
                "course_id": 303,
                "course_name": "College Physics",
                "description": "Measurement analysis",
                "due_time": datetime(2026, 6, 5, 18, 0),
                "estimated_hours": 3,
                "status": "done",
                "priority": 3,
            },
        ]
        status = (filters or {}).get("status")
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        return tasks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    board = CourseBoardWidget(facade=None)
    board.setWindowTitle("Course Board Debug")
    board.resize(900, 500)
    board.show()
    sys.exit(app.exec())
