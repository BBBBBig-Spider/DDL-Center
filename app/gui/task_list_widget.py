import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from app.gui.task_editor_dialog import TaskEditorDialog
from app.gui.theme import BORDER, INK, PKU_RED, PKU_RED_DARK, PKU_RED_LIGHT, TEXT


def get_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class TaskCardWidget(QFrame):
    def __init__(self, task_model, list_widget_parent) -> None:
        super().__init__()
        self.task = task_model
        self.parent_widget = list_widget_parent
        self.is_selected = False
        self.card_id = f"TaskCard_{id(self)}"
        self.setObjectName(self.card_id)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.status_val = self._get_field("status", "todo")
        self.init_ui()
        self.update_card_style()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.cb_status = QCheckBox()
        self.cb_status.setChecked(self.status_val == "done")
        layout.addWidget(self.cb_status)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.lbl_title = QLabel(str(self._get_field("title", "未命名任务")))
        self._apply_title_style()

        desc = self._get_field("description", "")
        self.lbl_desc = QLabel(str(desc) if desc else "暂无描述")
        self.lbl_desc.setStyleSheet(f"color: {TEXT}; font-size: 12px; background-color: transparent;")
        self.lbl_desc.setWordWrap(True)

        course_id = self._get_field("course_id")
        course_name = self._get_field("course_name")
        course_text = str(course_name) if course_name else (f"课程 ID：{course_id}" if course_id else "通用任务")
        self.lbl_course = QLabel(course_text)
        self.lbl_course.setStyleSheet(f"color: {PKU_RED}; font-size: 11px; font-weight: 500; background-color: transparent;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_desc)
        info_layout.addWidget(self.lbl_course)
        layout.addLayout(info_layout, stretch=1)

        self.time_widget = QWidget()
        self.time_widget.setObjectName("TaskTimeBox")
        self.time_widget.setStyleSheet("#TaskTimeBox { background-color: transparent; }")
        self.time_widget.setFixedWidth(92)
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        due_time = self._coerce_datetime(self._get_field("due_time"))
        due_text = due_time.strftime("%m-%d %H:%M") if due_time else "无截止时间"
        self.lbl_deadline = QLabel(due_text)
        self.lbl_deadline.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_deadline.setStyleSheet(f"color: {PKU_RED}; font-weight: bold; font-size: 12px; background-color: transparent;")
        hours = self._get_field("estimated_hours", 0)
        self.lbl_hours = QLabel(f"预计 {hours} 小时")
        self.lbl_hours.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_hours.setStyleSheet("color: #8A7A7A; font-size: 11px; background-color: transparent; border: none;")
        time_layout.addWidget(self.lbl_deadline)
        time_layout.addWidget(self.lbl_hours)
        layout.addWidget(self.time_widget)

        self.confirm_widget = QWidget()
        self.confirm_widget.setObjectName("TaskConfirmBox")
        self.confirm_widget.setStyleSheet("#TaskConfirmBox { background-color: transparent; }")
        confirm_layout = QVBoxLayout(self.confirm_widget)
        confirm_layout.setContentsMargins(0, 0, 0, 0)
        confirm_layout.setSpacing(4)
        self.btn_confirm_done = QPushButton("标记完成")
        self.btn_confirm_done.setStyleSheet("QPushButton { background-color: #6B7D3A; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold;} QPushButton:hover { background-color: #56652E; }")
        self.btn_confirm_delete = QPushButton("完成并删除")
        self.btn_confirm_delete.setStyleSheet(f"QPushButton {{ background-color: {PKU_RED}; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold;}} QPushButton:hover {{ background-color: {PKU_RED_DARK}; }}")
        confirm_layout.addWidget(self.btn_confirm_done)
        confirm_layout.addWidget(self.btn_confirm_delete)
        layout.addWidget(self.confirm_widget)
        self.confirm_widget.hide()

        self.cb_status.stateChanged.connect(self.on_checkbox_changed)
        self.btn_confirm_done.clicked.connect(self.on_confirm_done)
        self.btn_confirm_delete.clicked.connect(self.on_confirm_delete)

    def _get_field(self, key, default=None):
        return get_field(self.task, key, default)

    @staticmethod
    def _coerce_datetime(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _apply_title_style(self):
        if self.status_val == "done":
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray; background-color: transparent;")
        else:
            self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {INK}; background-color: transparent;")

    def update_card_style(self):
        try:
            priority = int(self._get_field("priority", 2))
        except (TypeError, ValueError):
            priority = 2
        p_color = {1: PKU_RED, 2: "#B8860B", 3: "#6B7D3A"}.get(priority, "#BFBFBF")
        bg_color = PKU_RED_LIGHT if self.is_selected else "#FFFFFF"
        border_color = PKU_RED if self.is_selected else "#E8E8E8"
        hover_bg = PKU_RED_LIGHT if self.is_selected else "#F9F9F9"
        self.setStyleSheet(
            f"""
            #{self.card_id} {{
                background-color: {bg_color};
                border-left: 5px solid {p_color};
                border-top: 1px solid {border_color};
                border-bottom: 1px solid {border_color};
                border-right: 1px solid {border_color};
                border-radius: 4px;
            }}
            #{self.card_id}:hover {{ background-color: {hover_bg}; }}
            #{self.card_id} QLabel {{
                background-color: transparent;
            }}
            #{self.card_id} QCheckBox {{
                background-color: transparent;
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self.parent_widget, "on_task_card_selected"):
            self.parent_widget.on_task_card_selected(self)
        super().mousePressEvent(event)

    def on_checkbox_changed(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        if self.status_val == "done" and not is_checked:
            self.on_confirm_todo()
            return
        self.time_widget.setVisible(not is_checked)
        self.confirm_widget.setVisible(is_checked)
        if is_checked:
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray; background-color: transparent;")
        else:
            self._apply_title_style()

    def on_confirm_done(self):
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.mark_task_done(task_id)
                self._refresh_parent()
                return
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"标记任务完成失败：{exc}")
        self._update_mock_task(task_id, {"status": "done"})
        self._refresh_parent()

    def on_confirm_delete(self):
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.delete_task(task_id)
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"删除任务失败：{exc}")
        else:
            self._delete_mock_task(task_id)
        self._refresh_parent()

    def on_confirm_todo(self):
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.update_task(task_id, {"status": "todo"})
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"恢复任务失败：{exc}")
        else:
            self._update_mock_task(task_id, {"status": "todo"})
        self.status_val = "todo"
        self._refresh_parent()

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        context_menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #FFFFFF;
                color: {INK};
                border: 1px solid {BORDER};
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 6px 22px 6px 12px;
            }}
            QMenu::item:selected {{
                background-color: {PKU_RED_LIGHT};
                color: {PKU_RED};
            }}
            """
        )
        edit_action = QAction("编辑任务", self)
        delete_action = QAction("删除任务", self)
        edit_action.triggered.connect(self.on_edit_triggered)
        delete_action.triggered.connect(self.on_delete_triggered)
        context_menu.addAction(edit_action)
        context_menu.addAction(delete_action)
        context_menu.exec(self.mapToGlobal(pos))

    def on_edit_triggered(self):
        dialog = TaskEditorDialog(self, task_data=self.task, facade=getattr(self.parent_widget, "facade", None))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            payload = dialog.get_task_data()
            task_id = self._get_field("id")
            if task_id is not None and getattr(self.parent_widget, "facade", None):
                try:
                    self.parent_widget.facade.update_task(task_id, payload)
                except Exception as exc:
                    QMessageBox.critical(self, "后端错误", f"更新任务失败：{exc}")
            elif isinstance(self.task, dict):
                self.task.update(payload)
        self._refresh_parent()

    def on_delete_triggered(self):
        title = self._get_field("title", "该任务")
        reply = QMessageBox.question(self, "删除任务", f"确定删除“{title}”吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.delete_task(task_id)
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"删除任务失败：{exc}")
        else:
            self._delete_mock_task(task_id)
        self._refresh_parent()

    def _update_mock_task(self, task_id, payload):
        tasks = getattr(self.parent_widget, "all_mock_tasks", None)
        if tasks is None:
            return
        for task in tasks:
            if task.get("id") == task_id:
                task.update(payload)
                break

    def _delete_mock_task(self, task_id):
        tasks = getattr(self.parent_widget, "all_mock_tasks", None)
        if tasks is not None:
            self.parent_widget.all_mock_tasks = [task for task in tasks if task.get("id") != task_id]

    def _refresh_parent(self):
        if hasattr(self.parent_widget, "refresh_current_view"):
            self.parent_widget.refresh_current_view()
        elif hasattr(self.parent_widget, "refresh_display"):
            self.parent_widget.refresh_display()


class TaskListWidget(QWidget):
    def __init__(self, facade=None) -> None:
        super().__init__()
        self.facade = facade
        self.task_manager = getattr(facade, "task_manager", facade)
        self.selected_task_id = None
        self.all_mock_tasks = [
            {"id": 1, "title": "高数习题整理", "course_id": 101, "description": "演示任务", "due_time": datetime(2026, 6, 8, 18, 30), "estimated_hours": 2, "status": "todo", "priority": 1},
            {"id": 2, "title": "程序设计项目", "course_id": 202, "description": "演示项目", "due_time": datetime(2026, 6, 10, 23, 59), "estimated_hours": 8, "status": "done", "priority": 2},
        ]
        self.init_ui()
        self.refresh_display()

    def init_ui(self):
        self.setObjectName("TaskListWidget")
        self.setStyleSheet(
            f"""
            QWidget#TaskListWidget {{
                background-color: transparent;
                color: {INK};
            }}
            QWidget#TaskListWidget QLabel {{
                background-color: transparent;
            }}
            """
        )
        self.main_container_layout = QHBoxLayout(self)
        self.main_container_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout = QVBoxLayout()
        self.main_container_layout.addLayout(self.main_layout, stretch=1)

        self.top_layout = QHBoxLayout()
        self.btn_add_task = QPushButton("新增任务")
        self.btn_add_task.setStyleSheet(f"QPushButton {{ background-color: {PKU_RED}; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 13px; }} QPushButton:hover {{background-color: {PKU_RED_DARK};}} QPushButton:pressed {{background-color: #4A0B0B;}}")
        self.btn_add_task.clicked.connect(self.show_add_task_dialog)
        self.top_layout.addWidget(self.btn_add_task)

        self.filter_label = QLabel("状态：")
        self.filter_label.setStyleSheet(f"margin-left: 15px; font-size: 13px; color: {TEXT}; background-color: transparent;")
        self.top_layout.addWidget(self.filter_label)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部任务", None)
        self.status_combo.addItem("未完成", "todo")
        self.status_combo.addItem("已完成", "done")
        self.status_combo.setStyleSheet(
            f"""
            QComboBox {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
                background-color: #FFFFFF;
                color: {INK};
            }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                color: {INK};
                selection-background-color: {PKU_RED_LIGHT};
                selection-color: {INK};
            }}
            """
        )
        self.status_combo.currentIndexChanged.connect(self.refresh_current_view)
        self.top_layout.addWidget(self.status_combo)
        self.top_layout.addStretch()
        self.main_layout.addLayout(self.top_layout)

        from app.gui.course_board_widget import CourseBoardWidget
        from app.gui.time_line_widget import TimelineWidget

        self.view_tab_bar = QTabBar()
        self.view_tab_bar.addTab("常规排序")
        self.view_tab_bar.addTab("课程分类")
        self.view_tab_bar.addTab("时间轴")
        self.view_tab_bar.setStyleSheet(
            f"""
            QTabBar::tab {{
                background-color: #FFFFFF;
                color: {TEXT};
                padding: 7px 16px;
                border: 1px solid {BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 3px;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background-color: {PKU_RED_LIGHT};
                font-weight: 700;
                color: {PKU_RED};
                border-color: #E7B8B8;
            }}
            QTabBar::tab:hover {{
                background-color: #F8F2F2;
            }}
            """
        )
        self.main_layout.addWidget(self.view_tab_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget()
        self.container.setObjectName("TaskContainer")
        self.container.setStyleSheet("#TaskContainer { background-color: transparent; }")
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(12)
        self.scroll_area.setWidget(self.container)

        self.view_board = CourseBoardWidget(facade=self.facade)
        self.view_timeline = TimelineWidget(facade=self.facade)
        self.stacked_views = QStackedWidget()
        self.stacked_views.addWidget(self.scroll_area)
        self.stacked_views.addWidget(self.view_board)
        self.stacked_views.addWidget(self.view_timeline)
        self.main_layout.addWidget(self.stacked_views)
        self.view_tab_bar.currentChanged.connect(self.on_view_changed)

        self.right_sidebar_layout = QVBoxLayout()
        self.right_sidebar_layout.setSpacing(12)
        self.right_sidebar_layout.setContentsMargins(0, 0, 0, 0)

        from app.gui.widgets.alert_panel import AlertPanel
        from app.gui.widgets.recommendation_panel import RecommendationPanel

        self.right_alert_panel = AlertPanel(facade=self.facade)
        self.right_sidebar_layout.addWidget(self.right_alert_panel, stretch=1)
        self.recommend_panel = RecommendationPanel(facade=self.facade)
        self.right_sidebar_layout.addWidget(self.recommend_panel, stretch=1)
        self.main_container_layout.addLayout(self.right_sidebar_layout)

    def on_task_card_selected(self, selected_card):
        for index in range(self.list_layout.count()):
            item = self.list_layout.itemAt(index)
            widget = item.widget() if item else None
            if isinstance(widget, TaskCardWidget):
                widget.is_selected = False
                widget.update_card_style()

        selected_card.is_selected = True
        selected_card.update_card_style()
        task_id = selected_card._get_field("id")
        task_title = selected_card._get_field("title", "未命名任务")
        self.selected_task_id = task_id
        if hasattr(self, "recommend_panel"):
            self.recommend_panel.set_task(task_id, task_title)

    def refresh_display(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = self._load_tasks(self.current_filters())
        if not tasks:
            self._sync_recommendation_selection([])
            empty_label = QLabel("暂无任务")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 13px; padding: 24px; background-color: transparent;")
            self.list_layout.addWidget(empty_label)
            self.list_layout.addStretch()
            self._refresh_side_panels()
            return

        for task in tasks:
            card = TaskCardWidget(task, self)
            if self.selected_task_id is not None and card._get_field("id") == self.selected_task_id:
                card.is_selected = True
                card.update_card_style()
            self.list_layout.addWidget(card)

        self._sync_recommendation_selection(tasks)
        self.list_layout.addStretch()
        self._refresh_side_panels()

    def _load_tasks(self, filters):
        if self.facade:
            try:
                return self.facade.list_tasks(filters)
            except Exception as exc:
                print(f"[GUI] Facade.list_tasks failed, using mock data: {exc}")
        selected_status = filters.get("status") if filters else None
        if selected_status:
            return [task for task in self.all_mock_tasks if task.get("status") == selected_status]
        return self.all_mock_tasks

    def current_filters(self):
        selected_status = self.status_combo.currentData()
        return {"status": selected_status} if selected_status else {}

    def _sync_recommendation_selection(self, tasks):
        if self.selected_task_id is None:
            return
        visible_ids = {self._get_task_id(task) for task in tasks}
        if self.selected_task_id in visible_ids:
            return
        self.selected_task_id = None
        if hasattr(self, "recommend_panel"):
            if hasattr(self.recommend_panel, "clear_task"):
                self.recommend_panel.clear_task()
            else:
                self.recommend_panel.current_task_id = None
                self.recommend_panel.current_task_title = ""
                self.recommend_panel.refresh_panel()

    @staticmethod
    def _get_task_id(task):
        return get_field(task, "id")

    def _refresh_side_panels(self):
        if hasattr(self, "right_alert_panel"):
            self.right_alert_panel.refresh_display()

    def refresh_current_view(self):
        active_widget = self.stacked_views.currentWidget()
        if active_widget == self.scroll_area:
            self.refresh_display()
        elif active_widget and hasattr(active_widget, "refresh_display"):
            active_widget.refresh_display(self.current_filters())
            self._refresh_side_panels()

    def show_add_task_dialog(self):
        dialog = TaskEditorDialog(self, facade=self.facade)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.get_task_data()
        if self.facade:
            try:
                self.facade.create_task(payload)
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"创建任务失败：{exc}")
                return
        else:
            next_id = max((task.get("id", 0) for task in self.all_mock_tasks), default=0) + 1
            payload["id"] = next_id
            payload.setdefault("status", "todo")
            self.all_mock_tasks.append(payload)
        self.refresh_current_view()

    def on_view_changed(self, index):
        self.stacked_views.setCurrentIndex(index)
        active_widget = self.stacked_views.currentWidget()
        if active_widget == self.scroll_area:
            self.refresh_display()
        elif active_widget and hasattr(active_widget, "refresh_display"):
            active_widget.refresh_display(self.current_filters())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = TaskListWidget(facade=None)
    test_widget.setWindowTitle("Task Center Debug")
    test_widget.resize(900, 600)
    test_widget.show()
    sys.exit(app.exec())
