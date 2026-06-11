from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.gui.task_list_widget import TaskCardWidget
from app.gui.theme import BORDER, INK, PRIMARY, PRIMARY_LIGHT
from app.gui._helpers import get_field


class CourseColumnWidget(QFrame):
    def __init__(self, course_id: int | None, course_name: str, tasks: list, facade, parent_board):
        super().__init__()
        self.course_id = course_id
        self.course_name = course_name
        self.facade = facade
        self.parent_board = parent_board
        self._init_ui(tasks)

    def _init_ui(self, tasks: list) -> None:
        self.setFixedWidth(260)
        self.setStyleSheet(
            f"""
            CourseColumnWidget {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            CourseColumnWidget QLabel {{
                background-color: transparent;
            }}
            """
        )

        column_layout = QVBoxLayout(self)
        column_layout.setContentsMargins(10, 10, 10, 10)
        column_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title = QLabel(self.course_name)
        title.setStyleSheet(f"color: {INK}; font-weight: 700; font-size: 15px;")
        count = QLabel(f"{len(tasks)} 项")
        count.setStyleSheet(
            f"background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; "
            "padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 700;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(count)
        column_layout.addLayout(header_layout)

        scroll = QScrollArea()
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
        list_layout = QVBoxLayout(container)
        list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        list_layout.setSpacing(10)
        list_layout.setContentsMargins(0, 0, 0, 0)

        if tasks:
            for task in tasks:
                list_layout.addWidget(TaskCardWidget(task, self.parent_board))
        else:
            empty = QLabel("暂无任务")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #9CA3AF; font-size: 12px; padding: 24px; background-color: transparent;")
            list_layout.addWidget(empty)

        list_layout.addStretch()
        scroll.setWidget(container)
        column_layout.addWidget(scroll, stretch=1)


class CourseBoardWidget(QWidget):
    def __init__(self, facade=None):
        super().__init__()
        self.facade = facade
        self.current_filters = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        title = QLabel("按课程分类")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK}; background-color: transparent;")
        main_layout.addWidget(title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
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

        self.board_container = QWidget()
        self.board_container.setStyleSheet("background-color: transparent;")
        self.board_layout = QHBoxLayout(self.board_container)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(16)
        self.board_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.board_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def refresh_display(self, filters=None) -> None:
        if filters is None:
            filters = self.current_filters
        else:
            self.current_filters = filters

        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        tasks = self._load_tasks(filters)
        courses = self._load_courses(tasks)

        if any(get_field(task, "course_id") is None for task in tasks):
            courses = list(courses)
            courses.append({"id": None, "name": "通用任务"})

        if not courses:
            empty = QLabel("暂无课程任务")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 32px; background-color: transparent;")
            self.board_layout.addWidget(empty)
            self.board_layout.addStretch()
            return

        for course in courses:
            course_id = get_field(course, "id")
            course_name = get_field(course, "name", "未命名课程")
            course_tasks = [task for task in tasks if get_field(task, "course_id") == course_id]
            self.board_layout.addWidget(CourseColumnWidget(course_id, course_name, course_tasks, self.facade, self))

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
        if self.facade and hasattr(self.facade, "list_courses"):
            try:
                courses = self.facade.list_courses()
                if courses:
                    return courses
            except NotImplementedError:
                pass
            except Exception as exc:
                print(f"Error fetching courses from Facade: {exc}")
        return self._derive_courses_from_tasks(tasks)

    @staticmethod
    def _derive_courses_from_tasks(tasks):
        courses = []
        seen = set()
        for task in tasks:
            course_id = get_field(task, "course_id")
            course_name = get_field(task, "course_name")
            if course_id is None or course_id in seen:
                continue
            seen.add(course_id)
            courses.append({"id": course_id, "name": course_name or f"课程 {course_id}"})
        return courses


if __name__ == "__main__":
    app = QApplication(sys.argv)
    board = CourseBoardWidget(facade=None)
    board.resize(900, 500)
    board.show()
    sys.exit(app.exec())
