import sys
from PySide6.QtWidgets import (QScrollArea, QVBoxLayout, QWidget, QHBoxLayout, QMenu, QComboBox,
                               QPushButton, QCheckBox, QLabel, QFrame, QApplication, QDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from datetime import datetime

from app.gui.task_editor_dialog import TaskEditorDialog

class TaskCardWidget(QFrame): 
    def __init__(self, task_model, list_widget_parent) -> None:
        
        super().__init__()
        self.task = task_model
        self.parent_widget = list_widget_parent
        
        self.card_id = f"TaskCard_{id(self)}"
        self.setObjectName(self.card_id)
        
        p_val = int(self._get_field("priority", 2))
        priority_colors = {1: "#FF4D4F", 2: "#FFA940", 3: "#1890FF"}
        p_color = priority_colors.get(p_val, "#BFBFBF")
        
        self.setStyleSheet(f"""
            #{self.card_id} {{
                background-color: white; 
                border-left: 5px solid {p_color};
                border-top: 1px solid #E8E8E8; border-bottom: 1px solid #E8E8E8; border-right: 1px solid #E8E8E8;
                border-radius: 4px;
            }}
            #{self.card_id}:hover {{ background-color: #F9F9F9; }}
        """)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        layout = QHBoxLayout(self)

        # 状态复选框
        self.cb_status = QCheckBox()
        self.status_val = self._get_field("status", "to do")
        self.cb_status.setChecked(self.status_val == "done")
        layout.addWidget(self.cb_status)

        info_layout = QVBoxLayout()
        
        title = self._get_field("title", "未命名任务")
        self.lbl_title = QLabel(title)
        if self.status_val == 'done':
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray;")
        else:
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        
        desc = self._get_field("description", "")
        self.lbl_desc = QLabel(desc if desc else "暂无详细描述")
        self.lbl_desc.setStyleSheet("color: #666; font-size: 12px;")
        self.lbl_desc.setWordWrap(True) 


        # 课程显示
        c_id = self._get_field("course_id", None)
        c_name = self._get_field("course_name", None) 
        course_text = f"📖 {c_name}" if c_name else (f"📖 课程ID: {c_id}" if c_id else "📅 通用任务")
            

        self.lbl_course = QLabel(course_text)
        self.lbl_course.setStyleSheet("color: #0078D4; font-size: 11px; font-weight: 500;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_desc)
        info_layout.addWidget(self.lbl_course)

        layout.addLayout(info_layout, stretch=1)

        # 时间与耗时区
        self.time_widget = QWidget()
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        dt = self._get_field("due_time", None)
        if isinstance(dt, str):
            try: dt = datetime.fromisoformat(dt)
            except: pass
            
        dt_str = dt.strftime("%m-%d %H:%M") if isinstance(dt, datetime) else "无截止时间"
        
        self.lbl_deadline = QLabel(f"⏰ {dt_str}")
        self.lbl_deadline.setStyleSheet("color: #D83B01; font-weight: bold; font-size: 12px;")
        
        hours = self._get_field("estimated_hours", 0)
        self.lbl_hours = QLabel(f"⏳ 预计 {hours}h")
        self.lbl_hours.setStyleSheet("color: #888; font-size: 11px;")

        time_layout.addWidget(self.lbl_deadline)
        time_layout.addWidget(self.lbl_hours)
        layout.addLayout(time_layout)


        self.confirm_widget = QWidget()
        confirm_layout = QVBoxLayout(self.confirm_widget)
        confirm_layout.setContentsMargins(0, 0, 0, 0)
        confirm_layout.setSpacing(4)

        self.btn_confirm_done = QPushButton("完成任务")
        self.btn_confirm_done.setStyleSheet("""
            QPushButton { background-color: #28A745; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold;}
            QPushButton:hover { background-color: #218838; }
        """)
        
        self.btn_confirm_delete = QPushButton("完成并删除任务")
        self.btn_confirm_delete.setStyleSheet("""
            QPushButton { background-color: #DC3545; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold;}
            QPushButton:hover { background-color: #C82333; }
        """)

        confirm_layout.addWidget(self.btn_confirm_done)
        confirm_layout.addWidget(self.btn_confirm_delete)
        layout.addWidget(self.confirm_widget)

        self.confirm_widget.hide()

        self.cb_status.stateChanged.connect(self.on_checkbox_changed)
        self.btn_confirm_done.clicked.connect(self.on_confirm_done)
        self.btn_confirm_delete.clicked.connect(self.on_confirm_delete)

    def _get_field(self, key, default=""):
        if isinstance(self.task, dict):
            return self.task.get(key, default)
        return getattr(self.task, key, default)

    def on_checkbox_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        if self.status_val == "done" and not is_checked:
            self.on_confirm_todo()
            return
        
        if is_checked: 
            self.time_widget.hide()
            self.confirm_widget.show()
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray;")
        else:
            self.time_widget.show()
            self.confirm_widget.hide()
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")


    def on_confirm_done(self):
        task_id = self._get_field("id", None)
        if task_id is not None and self.parent_widget.task_manager:
            try:
                self.parent_widget.task_manager.mark_done(task_id)
            except Exception as e:
                QMessageBox.critical(self, "持久化错误", f"TaskManager 标记完成失败: {e}")
        else:
           if hasattr(self.parent_widget, "all_mock_tasks"):
                for t in self.parent_widget.all_mock_tasks:
                    if t["id"] == task_id:
                        t["status"] = "done"

                        break
        
        self.status_val = "done"
        self.confirm_widget.hide()
        self.time_widget.show()
        
        self.parent_widget.refresh_display()

    def on_confirm_delete(self): 
        task_id = self._get_field("id", None)
        if task_id is not None and self.parent_widget.task_manager:
            try:
                self.parent_widget.task_manager.delete_task(task_id)
            except Exception as e:
                QMessageBox.critical(self, "持久化错误", f"TaskManager 删除任务失败: {e}")
        else:
           if hasattr(self.parent_widget, "all_mock_tasks"):
                self.parent_widget.all_mock_tasks = [t for t in self.parent_widget.all_mock_tasks if t["id"] != task_id]
                
        self.parent_widget.refresh_display()

    def on_confirm_todo(self): 
        task_id = self._get_field("id", None)
        if task_id is not None and self.parent_widget.task_manager:
            try:
                self.parent_widget.task_manager.update_task(task_id, {"status": "to do"})
            except Exception as e:
                QMessageBox.critical(self, "持久化错误", f"TaskManager 更新任务状态失败: {e}")
        else:
           if hasattr(self.parent_widget, "all_mock_tasks"):
                for t in self.parent_widget.all_mock_tasks:
                    if t["id"] == task_id:
                        t["status"] = "to do"
                        break
        
        self.status_val = "to do"
        self.parent_widget.refresh_display()
    
    def show_context_menu(self, pos):
        context_menu = QMenu(self)

        edit_action = QAction("✏️编辑任务", self)
        delete_action = QAction("🗑️删除任务", self)

        edit_action.triggered.connect(self.on_edit_triggered)
        delete_action.triggered.connect(self.on_delete_triggered)

        context_menu.addAction(edit_action)
        context_menu.addAction(delete_action)
        context_menu.exec(self.mapToGlobal(pos))
    
    def on_edit_triggered(self):
        dialog = TaskEditorDialog(self, task_data=self.task, facade=self.parent_widget.facade)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_payload = dialog.get_task_data()
            task_id = self._get_field("id", None)

            if task_id is not None and self.parent_widget.task_manager:
                try:
                    self.parent_widget.task_manager.update_task(task_id, new_payload)
                except Exception as e:
                    QMessageBox.critical(self, "持久化错误", f"TaskManager 更新任务失败: {e}")
            
            else: 
                if isinstance(self.task, dict):
                    self.task.update(new_payload)
                    print(f"[GUI Mock Mode] 模拟更新任务ID {task_id} 数据: {new_payload}")
            
        self.parent_widget.refresh_display()
    
    def on_delete_triggered(self): 
        title = self._get_field("title", "此任务")
        reply = QMessageBox.question(self, "确认删除", f"确定要删除任务 '{title}' 吗？此操作无法撤销。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            task_id = self._get_field("id", None)
            if task_id is not None and self.parent_widget.task_manager:
                try:
                    self.parent_widget.task_manager.delete_task(task_id)
                except Exception as e:
                    QMessageBox.critical(self, "持久化错误", f"TaskManager 删除任务失败: {e}")
            else:
                print(f"[GUI Mock Mode] 模拟删除任务ID {task_id}")
            
            self.parent_widget.refresh_display()


class TaskListWidget(QWidget): 
    def __init__(self, facade=None) -> None:
        super().__init__()
        self.facade = facade

        self.task_manager = getattr(facade, "task_manager", facade)
        
        self.all_mock_tasks = [
            {"id": 1, "title": "高等数学A课后作业", "course_id": 101, "description": "标准接口Mock测试", "due_time": datetime(2026, 5, 18, 18, 30), "estimated_hours": 2, "status": "to do", "priority": 1},
            {"id": 2, "title": "程序设计实习大作业", "course_id": 202, "description": "完成魔兽大作业", "due_time": datetime(2026, 5, 20, 23, 59), "estimated_hours": 8, "status": "done", "priority": 2}
        ]

        self.init_ui()
        self.refresh_display()
    
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        #创建新任务
        self.top_layout = QHBoxLayout()
        self.btn_add_task = QPushButton("➕ 添加新任务")
        self.btn_add_task.setStyleSheet("""
            QPushButton {
                background-color: #0078D4; color: white; border: none;
                border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover {background-color: #005A9E;}
            QPushButton:pressed {background-color: #004578;}
        """)
        self.btn_add_task.clicked.connect(self.show_add_task_dialog)
        self.top_layout.addWidget(self.btn_add_task)
        self.filter_label = QLabel("状态筛选：")
        self.filter_label.setStyleSheet("margin-left: 15px; font-size: 13px; color: rgba(0, 0, 0, 0.45);")
        self.top_layout.addWidget(self.filter_label)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部任务", None)
        self.status_combo.addItem("未完成 (To Do)", "to do")
        self.status_combo.addItem("已完成 (Done)", "done")
        self.status_combo.setStyleSheet("""
            QComboBox { border: 1px solid #CCC; border-radius: 4px; padding: 4px 8px; min-width: 120px; }
        """)
        
        self.status_combo.currentIndexChanged.connect(self.refresh_display)
        self.top_layout.addWidget(self.status_combo)

        self.top_layout.addStretch()
        self.main_layout.addLayout(self.top_layout)

        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("TaskContainer")
        self.container.setStyleSheet("#TaskContainer { background-color: transparent; }")

        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(12)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

    def refresh_display(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        selected_status = self.status_combo.currentData()

        tasks = []
        if self.task_manager and hasattr(self.task_manager, "list_tasks"):
            try:
                if selected_status: 
                    if hasattr(self.task_manager, "list_by_status"):
                        tasks = self.task_manager.list_by_status(selected_status)
                    else: 
                        tasks = self.task_manager.list_tasks(filters={"status": selected_status})
                else:
                    tasks = self.task_manager.list_tasks() 
                
                if selected_status and tasks:
                    first = tasks[0]
                    if isinstance(first, dict):
                        tasks = [t for t in tasks if str(t.get("status", "")).strip() == selected_status]
                    else:
                        tasks = [t for t in tasks if str(getattr(t, "status", "")).strip() == selected_status]
            except Exception as e:
                print(f"[GUI Error] TaskManager.list_tasks 执行失败: {e}")
                tasks = []
        else:
            if selected_status:
                tasks = [t for t in self.all_mock_tasks if t["status"] == selected_status]
            else:
                tasks = self.all_mock_tasks


        for task in tasks:
            card = TaskCardWidget(task, self)
            self.list_layout.addWidget(card)
            
        self.list_layout.addStretch()
    
    def show_add_task_dialog(self): 
        dialog = TaskEditorDialog(self, facade=self.facade)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            payload = dialog.get_task_data()

            if self.task_manager and hasattr(self.task_manager, "create_task"):
                try:
                    self.task_manager.create_task(payload) 
                except Exception as e:
                    QMessageBox.critical(self, "持久化错误", f"TaskManager 创建任务失败: {e}")
            else:
                print(f"[GUI Mock Mode] 捕获弹窗数据: {payload}")
            
            self.refresh_display()
        
        tasks = []
        if self.facade:
            try:
                tasks = self.facade.get_all_tasks()
            except:
                pass
        
        if not tasks:
            tasks = self.local_tasks

        for task in tasks:
            card = TaskCardWidget(task)
            self.list_layout.addWidget(card)
            
        self.list_layout.addStretch()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = TaskListWidget(facade=None)
    test_widget.setWindowTitle("任务中心独立调试（参数报错已修复）")
    test_widget.resize(600, 500)
    test_widget.show()
    sys.exit(app.exec())