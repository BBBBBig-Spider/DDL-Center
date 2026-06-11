import sys
from datetime import datetime

from PySide6.QtCore import Qt, QThread
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
from app.gui.theme import BORDER, INK, ACCENT, PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, TEXT
from app.gui._helpers import get_field


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

        # Batch-mode checkbox (hidden until batch mode is active)
        self.batch_select_cb = QCheckBox()
        self.batch_select_cb.setVisible(False)
        self.batch_select_cb.setFixedWidth(18)
        self.batch_select_cb.stateChanged.connect(self._on_batch_check_changed)
        layout.addWidget(self.batch_select_cb)

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
        self.lbl_course.setStyleSheet(f"color: {PRIMARY}; font-size: 11px; font-weight: 500; background-color: transparent;")

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
        due_text, due_color, due_bold = self._deadline_display(due_time, self.status_val)
        self.lbl_deadline = QLabel(due_text)
        self.lbl_deadline.setAlignment(Qt.AlignmentFlag.AlignRight)
        weight = "bold" if due_bold else "normal"
        self.lbl_deadline.setStyleSheet(
            f"color: {due_color}; font-weight: {weight}; font-size: 12px; background-color: transparent;"
        )
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
        self.btn_confirm_delete.setStyleSheet(f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold;}} QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}")
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

    @staticmethod
    def _deadline_display(due_time, status: str) -> tuple[str, str, bool]:
        """Return (display_text, color_hex, bold) for a deadline label."""
        from datetime import timedelta
        if due_time is None:
            return "无截止时间", "#9B9B9B", False
        if status == "done":
            return due_time.strftime("%m-%d %H:%M"), "#9B9B9B", False
        now = datetime.now()
        if due_time < now:
            return f"已逾期 {due_time.strftime('%m-%d %H:%M')}", "#C0392B", True
        if due_time <= now + timedelta(hours=24):
            return f"紧急 {due_time.strftime('%m-%d %H:%M')}", "#C0392B", True
        if due_time <= now + timedelta(days=3):
            return due_time.strftime("%m-%d %H:%M"), "#B8860B", True
        return due_time.strftime("%m-%d %H:%M"), "#555555", False

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
        p_color = {1: PRIMARY, 2: "#B8860B", 3: "#6B7D3A"}.get(priority, "#BFBFBF")
        bg_color = PRIMARY_LIGHT if self.is_selected else "#FFFFFF"
        border_color = PRIMARY if self.is_selected else "#E8E8E8"
        hover_bg = PRIMARY_LIGHT if self.is_selected else "#F9F9F9"
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
        if event.button() == Qt.MouseButton.LeftButton:
            pw = self.parent_widget
            if getattr(pw, "batch_mode", False):
                self.batch_select_cb.setChecked(not self.batch_select_cb.isChecked())
            elif hasattr(pw, "on_task_card_selected"):
                pw.on_task_card_selected(self)
        super().mousePressEvent(event)

    def set_batch_mode(self, enabled: bool, selected_ids: set | None = None) -> None:
        self.batch_select_cb.setVisible(enabled)
        if enabled:
            task_id = self._get_field("id")
            checked = task_id in (selected_ids or set())
            self.batch_select_cb.blockSignals(True)
            self.batch_select_cb.setChecked(checked)
            self.batch_select_cb.blockSignals(False)
        self.update_card_style()

    def _on_batch_check_changed(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        task_id = self._get_field("id")
        if hasattr(self.parent_widget, "on_batch_card_check_changed"):
            self.parent_widget.on_batch_card_check_changed(task_id, is_checked)

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
        self._refresh_parent()

    def on_confirm_delete(self):
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.delete_task(task_id)
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"删除任务失败：{exc}")
        self._refresh_parent()

    def on_confirm_todo(self):
        task_id = self._get_field("id")
        if task_id is not None and getattr(self.parent_widget, "facade", None):
            try:
                self.parent_widget.facade.update_task(task_id, {"status": "todo"})
            except Exception as exc:
                QMessageBox.critical(self, "后端错误", f"恢复任务失败：{exc}")
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
                background-color: {PRIMARY_LIGHT};
                color: {PRIMARY};
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
        self._refresh_parent()

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
        self.batch_mode = False
        self.batch_selected: set = set()
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
        self.btn_add_task.setStyleSheet(f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 13px; }} QPushButton:hover {{background-color: {PRIMARY_DARK};}} QPushButton:pressed {{background-color: #4A0B0B;}}")
        self.btn_add_task.clicked.connect(self.show_add_task_dialog)
        self.top_layout.addWidget(self.btn_add_task)

        self.btn_sync = QPushButton("🔄 同步教学网")
        self.btn_sync.setStyleSheet(
            f"QPushButton {{ background-color: #FFFFFF; color: {PRIMARY}; border: 1px solid {PRIMARY}; "
            f"border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {PRIMARY_LIGHT}; }}"
            f"QPushButton:disabled {{ color: #999999; border-color: #CCCCCC; }}"
        )
        self.btn_sync.clicked.connect(self._trigger_sync)
        self.top_layout.addWidget(self.btn_sync)
        self._sync_thread: QThread | None = None
        self._sync_worker = None

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
                selection-background-color: {PRIMARY_LIGHT};
                selection-color: {INK};
            }}
            """
        )
        self.status_combo.currentIndexChanged.connect(self.refresh_current_view)
        self.top_layout.addWidget(self.status_combo)

        self.top_layout.addStretch()

        self.btn_purge = QPushButton("清理逾期")
        self.btn_purge.setStyleSheet(
            f"QPushButton {{ background-color: #FFFFFF; color: #B8860B; border: 1px solid #B8860B; "
            f"border-radius: 4px; padding: 6px 12px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #FFF8E6; }}"
        )
        self.btn_purge.clicked.connect(self._purge_overdue)
        self.top_layout.addWidget(self.btn_purge)

        self.btn_batch = QPushButton("批量操作")
        self.btn_batch.setStyleSheet(
            f"QPushButton {{ background-color: #FFFFFF; color: {TEXT}; border: 1px solid {BORDER}; "
            f"border-radius: 4px; padding: 6px 12px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #F0F0F0; }}"
            f"QPushButton:checked {{ background-color: {ACCENT}; color: #FFFFFF; border-color: {ACCENT}; }}"
        )
        self.btn_batch.setCheckable(True)
        self.btn_batch.clicked.connect(self.toggle_batch_mode)
        self.top_layout.addWidget(self.btn_batch)

        self.main_layout.addLayout(self.top_layout)

        # Batch toolbar (hidden until batch mode is active)
        self.batch_toolbar = QFrame()
        self.batch_toolbar.setObjectName("BatchToolbar")
        self.batch_toolbar.setStyleSheet(
            f"QFrame#BatchToolbar {{ background-color: #FFF8E6; border: 1px solid {ACCENT}; "
            f"border-radius: 6px; padding: 2px; }}"
            f"QFrame#BatchToolbar QLabel {{ background-color: transparent; color: {INK}; }}"
            f"QFrame#BatchToolbar QCheckBox {{ background-color: transparent; color: {INK}; }}"
        )
        batch_row = QHBoxLayout(self.batch_toolbar)
        batch_row.setContentsMargins(12, 6, 12, 6)
        batch_row.setSpacing(10)

        self.batch_select_all_cb = QCheckBox("全选")
        self.batch_select_all_cb.setTristate(True)
        self.batch_select_all_cb.setStyleSheet(f"font-size: 13px; color: {INK};")
        self.batch_select_all_cb.stateChanged.connect(self._on_select_all_changed)
        batch_row.addWidget(self.batch_select_all_cb)

        batch_row.addStretch()

        self.batch_count_label = QLabel("已选 0 项")
        self.batch_count_label.setStyleSheet(f"font-size: 12px; color: #8A5A00;")
        batch_row.addWidget(self.batch_count_label)

        self.btn_batch_done = QPushButton("标记完成")
        self.btn_batch_done.setStyleSheet(
            "QPushButton { background-color: #6B7D3A; color: white; border: none; border-radius: 4px; "
            "padding: 5px 14px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: #56652E; }"
            "QPushButton:disabled { background-color: #C0C0C0; }"
        )
        self.btn_batch_done.clicked.connect(self._batch_mark_done)
        batch_row.addWidget(self.btn_batch_done)

        self.btn_batch_delete = QPushButton("删除")
        self.btn_batch_delete.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; border-radius: 4px; "
            f"padding: 5px 14px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}"
            "QPushButton:disabled { background-color: #C0C0C0; }"
        )
        self.btn_batch_delete.clicked.connect(self._batch_delete)
        batch_row.addWidget(self.btn_batch_delete)

        btn_exit_batch = QPushButton("退出批量")
        btn_exit_batch.setStyleSheet(
            f"QPushButton {{ background-color: #FFFFFF; color: {TEXT}; border: 1px solid {BORDER}; "
            "border-radius: 4px; padding: 5px 12px; font-size: 12px; }"
            "QPushButton:hover { background-color: #F0F0F0; }"
        )
        btn_exit_batch.clicked.connect(self.toggle_batch_mode)
        batch_row.addWidget(btn_exit_batch)

        self.batch_toolbar.hide()
        self.main_layout.addWidget(self.batch_toolbar)

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
                background-color: {PRIMARY_LIGHT};
                font-weight: 700;
                color: {PRIMARY};
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

    def _purge_overdue(self) -> None:
        if not self.facade or not hasattr(self.facade, "purge_overdue_tasks"):
            QMessageBox.warning(self, "清理逾期", "当前 Facade 不支持清理逾期功能。")
            return
        reply = QMessageBox.question(
            self, "清理逾期任务",
            "将清理所有未完成且已超过截止时间的任务。\n"
            "同步任务将隐藏（不再显示但保留记录），手动任务将永久删除。\n\n"
            "确认继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            count = self.facade.purge_overdue_tasks()
            if count == 0:
                QMessageBox.information(self, "清理完成", "当前没有需要清理的逾期任务。")
            else:
                QMessageBox.information(self, "清理完成", f"已清理 {count} 项逾期任务。")
        except Exception as exc:
            QMessageBox.critical(self, "清理失败", str(exc))
        self.refresh_current_view()

    def _trigger_sync(self) -> None:
        if self._sync_thread is not None and self._sync_thread.isRunning():
            return
        if not self.facade or not hasattr(self.facade, "sync_from_teaching_site"):
            QMessageBox.warning(self, "无法同步", "当前 Facade 不支持教学网同步。")
            return

        from app.services import credentials_store
        if not credentials_store.is_logged_in():
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
            if not LoginDialog.run(self, auth_client):
                return

        username, password = credentials_store.load()
        from app.gui.sync_worker import SyncWorker

        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("同步中…")

        thread = QThread(self)
        worker = SyncWorker(self.facade, username, password)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_sync_finished)
        worker.failed.connect(self._on_sync_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_sync_thread)
        self._sync_thread = thread
        self._sync_worker = worker
        thread.start()

    def _on_sync_finished(self, result) -> None:
        self._restore_sync_button()
        QMessageBox.information(self, "同步完成", self._format_sync_result(result))
        self.refresh_current_view()

    def _on_sync_failed(self, message: str) -> None:
        self._restore_sync_button()
        QMessageBox.warning(self, "同步失败", message)

    def _restore_sync_button(self) -> None:
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 同步教学网")

    def _clear_sync_thread(self) -> None:
        if self._sync_thread is not None:
            self._sync_thread.deleteLater()
        self._sync_thread = None
        self._sync_worker = None

    @staticmethod
    def _format_sync_result(result) -> str:
        source = get_field(result, "source", "network")
        errors = get_field(result, "errors", []) or []
        tasks_new = get_field(result, "tasks_new", 0)
        tasks_unchanged = get_field(result, "tasks_unchanged", 0)
        tasks_dropped_overdue = get_field(result, "tasks_dropped_overdue", 0)
        ai_recovered = get_field(result, "ai_recovered", 0)
        ai_drop_overdue = get_field(result, "ai_drop_overdue", 0)
        ai_drop_non_task = get_field(result, "ai_drop_non_task", 0)
        ai_drop_no_ai = get_field(result, "ai_drop_no_ai", 0)

        lines = [f"同步完成（来源：{source}）"]
        lines.append(f"任务：新增 {tasks_new}，未变 {tasks_unchanged}")
        if tasks_dropped_overdue:
            lines.append(f"丢弃逾期：{tasks_dropped_overdue} 条")
        if ai_recovered:
            lines.append(f"AI 兜底成功：{ai_recovered} 条（无结束时间）")
        ai_drop_total = ai_drop_overdue + ai_drop_non_task + ai_drop_no_ai
        if ai_drop_total:
            lines.append(
                f"AI 兜底丢弃：逾期 {ai_drop_overdue}，非任务 {ai_drop_non_task}，"
                f"无 AI {ai_drop_no_ai}"
            )
        if errors:
            lines.append("")
            lines.append("部分模块失败：")
            for err in errors:
                lines.append(f"  - {err}")
        return "\n".join(lines)

    def toggle_batch_mode(self) -> None:
        self.batch_mode = not self.batch_mode
        self.batch_selected.clear()
        self.btn_batch.setChecked(self.batch_mode)
        self.batch_toolbar.setVisible(self.batch_mode)
        # Reset select-all checkbox without triggering its signal
        self.batch_select_all_cb.blockSignals(True)
        self.batch_select_all_cb.setChecked(False)
        self.batch_select_all_cb.blockSignals(False)
        self._update_batch_toolbar()
        # Apply batch mode to all currently displayed cards
        for index in range(self.list_layout.count()):
            item = self.list_layout.itemAt(index)
            widget = item.widget() if item else None
            if isinstance(widget, TaskCardWidget):
                widget.set_batch_mode(self.batch_mode, self.batch_selected)

    def _update_batch_toolbar(self) -> None:
        n = len(self.batch_selected)
        self.batch_count_label.setText(f"已选 {n} 项")
        has_selection = n > 0
        self.btn_batch_done.setEnabled(has_selection)
        self.btn_batch_delete.setEnabled(has_selection)
        # Update select-all state without triggering signal
        tasks = self._load_tasks(self.current_filters())
        total = len(tasks)
        self.batch_select_all_cb.blockSignals(True)
        if total > 0 and n == total:
            self.batch_select_all_cb.setCheckState(Qt.CheckState.Checked)
        elif n > 0:
            self.batch_select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.batch_select_all_cb.setCheckState(Qt.CheckState.Unchecked)
        self.batch_select_all_cb.blockSignals(False)

    def _on_select_all_changed(self, state) -> None:
        # Partial → treat as "select all" so the user can click once to select all
        select_all = state != Qt.CheckState.Unchecked.value
        tasks = self._load_tasks(self.current_filters())
        self.batch_selected.clear()
        if select_all:
            for task in tasks:
                tid = self._get_task_id(task)
                if tid is not None:
                    self.batch_selected.add(tid)
        for index in range(self.list_layout.count()):
            item = self.list_layout.itemAt(index)
            widget = item.widget() if item else None
            if isinstance(widget, TaskCardWidget):
                widget.set_batch_mode(True, self.batch_selected)
        self._update_batch_toolbar()

    def on_batch_card_check_changed(self, task_id, checked: bool) -> None:
        if task_id is None:
            return
        if checked:
            self.batch_selected.add(task_id)
        else:
            self.batch_selected.discard(task_id)
        self._update_batch_toolbar()

    def _batch_mark_done(self) -> None:
        if not self.batch_selected:
            return
        ids = list(self.batch_selected)
        count = len(ids)
        reply = QMessageBox.question(
            self, "批量标记完成",
            f"确定将选中的 {count} 项任务标记为已完成吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for task_id in ids:
            try:
                self.facade.mark_task_done(task_id)
            except Exception as exc:
                errors.append(str(exc))
        self.batch_selected.clear()
        if errors:
            QMessageBox.warning(self, "部分失败", f"以下错误发生：\n" + "\n".join(errors[:5]))
        self.toggle_batch_mode()

    def _batch_delete(self) -> None:
        if not self.batch_selected:
            return
        ids = list(self.batch_selected)
        count = len(ids)
        reply = QMessageBox.question(
            self, "批量删除",
            f"确定删除选中的 {count} 项任务吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for task_id in ids:
            try:
                self.facade.delete_task(task_id)
            except Exception as exc:
                errors.append(str(exc))
        self.batch_selected.clear()
        if errors:
            QMessageBox.warning(self, "部分失败", f"以下错误发生：\n" + "\n".join(errors[:5]))
        self.toggle_batch_mode()

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
            if self.batch_mode:
                card.set_batch_mode(True, self.batch_selected)
            self.list_layout.addWidget(card)

        self._sync_recommendation_selection(tasks)
        self.list_layout.addStretch()
        self._refresh_side_panels()

    def _load_tasks(self, filters):
        if self.facade:
            try:
                return self.facade.list_tasks(filters)
            except Exception as exc:
                print(f"[GUI] Facade.list_tasks failed: {exc}")
        return []

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
            QMessageBox.critical(self, "后端错误", "当前没有连接真实 Facade，无法创建任务。")
            return
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
