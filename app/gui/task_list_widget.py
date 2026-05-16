import sys
from PySide6.QtWidgets import (QScrollArea, QVBoxLayout, QWidget, QHBoxLayout, 
<<<<<<< HEAD
                             QPushButton, QCheckBox, QLabel, QFrame, QApplication, QDialog)
from PySide6.QtCore import Qt
from datetime import datetime
from app.gui.task_editor_dialog import TaskEditorDialog
=======
                             QPushButton, QCheckBox, QLabel, QFrame, QApplication)
from PySide6.QtCore import Qt
from datetime import datetime
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51

class TaskCardWidget(QFrame): 
    def __init__(self, task_data) -> None:
        super().__init__()
        self.data = task_data
        self.setObjectName("TaskCard")
        
        # 优先级颜色：1 高(红)，2 中(橙)，3 低(蓝)
<<<<<<< HEAD
        
=======
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51
        priority_colors = {1: "#FF4D4F", 2: "#FFA940", 3: "#1890FF"}
        p_color = priority_colors.get(self.data.get("priority", 2), "#BFBFBF")
        
        self.setStyleSheet(f"""
            #TaskCard {{
                background-color: white; 
                border-left: 5px solid {p_color};
                border-top: 1px solid #E8E8E8; 
                border-bottom: 1px solid #E8E8E8;
                border-right: 1px solid #E8E8E8;
                border-radius: 4px;
            }}
            #TaskCard:hover {{
                background-color: #F9F9F9;
            }}
        """)
        layout = QHBoxLayout(self)

        # 状态勾选
        self.cb_status = QCheckBox()
        self.cb_status.setChecked(self.data.get('status') == 'done')
        layout.addWidget(self.cb_status)

        # 核心信息区 (包含 Title, Course, Description)
        info_layout = QVBoxLayout()
        
        # 标题
        title = self.data.get('title', '未命名任务')
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        if self.data.get('status') == 'done':
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray;")
        
        
        desc = self.data.get('description', '')
        self.lbl_desc = QLabel(desc if desc else "暂无详细描述")
        self.lbl_desc.setStyleSheet("color: #666; font-size: 12px;")
        self.lbl_desc.setWordWrap(True) 

        # 课程信息
        course_text = f"📖 课程ID: {self.data.get('course_id')}" if self.data.get('course_id') else "📅 通用任务"
        self.lbl_course = QLabel(course_text)
        self.lbl_course.setStyleSheet("color: #0078D4; font-size: 11px; font-weight: 500;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_desc)
        info_layout.addWidget(self.lbl_course)
        
        layout.addLayout(info_layout, stretch=1)

        # 时间与预估时长区
        time_layout = QVBoxLayout()
        time_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)

        dt = self.data.get('due_time')
        dt_str = dt.strftime("%m-%d %H:%M") if isinstance(dt, datetime) else "无截止时间"
        
        self.lbl_deadline = QLabel(f"⏰ {dt_str}")
        self.lbl_deadline.setStyleSheet("color: #D83B01; font-weight: bold; font-size: 12px;")
        
        hours = self.data.get('estimated_hours', 0)
        self.lbl_hours = QLabel(f"⏳ 预计 {hours}h")
        self.lbl_hours.setStyleSheet("color: #888; font-size: 11px;")

        time_layout.addWidget(self.lbl_deadline)
        time_layout.addWidget(self.lbl_hours)
        layout.addLayout(time_layout)

<<<<<<< HEAD
        self.cb_status.stateChanged.connect(self.on_status_changed)

    def on_status_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        self.data['status'] = 'done' if is_checked else 'to do'
        self.update_title_style(is_checked)
    
    def update_title_style(self, is_done):
        if is_done:
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; text-decoration: line-through; color: gray;")
        else:
            self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")

=======
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51
class TaskListWidget(QWidget): 
    def __init__(self, facade=None) -> None:
        super().__init__()
        self.facade = facade
<<<<<<< HEAD
        self.local_tasks = []
        self.init_mock_data()
        self.init_ui()
    
    def init_mock_data(self):
        self.local_tasks = [
            {
                "id": 1,
                "title": "高等数学A课后作业",
                "course_id": 101,
                "description": "作业真多啊啊啊啊啊",
                "due_time": datetime(2026, 5, 13, 18, 30),
                "estimated_hours": 2.5,
                "status": "done",
                "priority": 1
            },
            {
                "id": 2,
                "title": "程序设计实习大作业",
                "course_id": 202,
                "description": "完成魔兽世界大作业终极版！我需要一个很长很长的描述来测试它能不能换行诶现在好像已经很长了",
                "due_time": datetime(2026, 5, 14, 23, 59),
                "estimated_hours": 8.0,
                "status": "doing",
                "priority": 2
            },
            {
                "id": 3,
                "title": "AI引lab",
                "course_id": 305,
                "description": "完成AI引lab2：机器学习",
                "due_time": datetime(2026, 5, 26, 12, 0),
                "estimated_hours": 4.5,
                "status": "to do",
                "priority": 3
            }, 
            
            {
                "id": 4,
                "title": "程序设计实习小组作业",
                "course_id": 202,
                "description": "完成程序设计实习小组作业DDL-Center(套娃hhhh)",
                "due_time": datetime(2026, 6, 6, 23, 59),
                "estimated_hours": 2333,
                "status": "doing",
                "priority": 2
            }
        ]
=======
        self.init_ui()
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
<<<<<<< HEAD

        #创建新任务
        self.top_layout = QHBoxLayout()
        self.btn_add_task = QPushButton("➕ 添加新任务")
        self.btn_add_task.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold; 
                font-size: 13px;
            }
            QPushButton:hover {background-color: #005A9E;}
            QPushButton:pressed {background-color: #004578;}
        """)
        self.btn_add_task.clicked.connect(self.show_add_task_dialog)
        self.top_layout.addWidget(self.btn_add_task)
        self.top_layout.addStretch()
        self.main_layout.addLayout(self.top_layout)
=======
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("TaskContainer")
        self.container.setStyleSheet("#TaskContainer { background-color: transparent; }")

        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(12)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        self.refresh_display()

    def refresh_display(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        
        tasks = []
        if self.facade:
            try:
                tasks = self.facade.get_all_tasks()
            except:
                pass
        
        if not tasks:
<<<<<<< HEAD
            tasks = self.local_tasks
=======
            tasks = [
                {
                    "id": 1,
                    "title": "高等数学A课后作业",
                    "course_id": 101,
                    "description": "作业真多啊啊啊啊啊",
                    "due_time": datetime(2026, 5, 13, 18, 30),
                    "estimated_hours": 2.5,
                    "status": "done",
                    "priority": 1
                },
                {
                    "id": 2,
                    "title": "程序设计实习大作业",
                    "course_id": 202,
                    "description": "完成魔兽世界大作业终极版！我需要一个很长很长的描述来测试它能不能换行诶现在好像已经很长了",
                    "due_time": datetime(2026, 5, 14, 23, 59),
                    "estimated_hours": 8.0,
                    "status": "doing",
                    "priority": 2
                },
                {
                    "id": 3,
                    "title": "AI引lab",
                    "course_id": 305,
                    "description": "完成AI引lab2：机器学习",
                    "due_time": datetime(2026, 5, 26, 12, 0),
                    "estimated_hours": 4.5,
                    "status": "to do",
                    "priority": 3
                }, 
                
                {
                    "id": 4,
                    "title": "程序设计实习小组作业",
                    "course_id": 202,
                    "description": "完成程序设计实习小组作业DDL-Center(套娃hhhh)",
                    "due_time": datetime(2026, 6, 6, 23, 59),
                    "estimated_hours": 2333,
                    "status": "doing",
                    "priority": 2
                }
            ]
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51

        for task in tasks:
            card = TaskCardWidget(task)
            self.list_layout.addWidget(card)
            
        self.list_layout.addStretch()
<<<<<<< HEAD
    
    def show_add_task_dialog(self): 
        dialog = TaskEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_data = dialog.get_task_data()

            py_datetime = raw_data.get("due_time")

            course_map = {"高等数学A": 101, "程序设计实习": 202, "AI引论": 303}
            c_id = course_map.get(raw_data.get("course_name"), None)

            p_text = raw_data["priority"]
            if isinstance(p_text, int):
                p_val = p_text
            else:
                p_val = 1 if "高" in str(p_text) else (2 if "中" in str(p_text) else 3)

            new_task = {
                "id": len(self.local_tasks) + 1,
                "title": raw_data["title"],
                "course_id": c_id,
                "description": raw_data["description"],
                "due_time": py_datetime,
                "estimated_hours": float(raw_data["estimated_hours"]),
                "status": "to do",
                "priority": p_val
            }
            self.local_tasks.append(new_task)
            self.refresh_display()
=======
>>>>>>> af3ee684ab51ba9d036ed59f9c5ddedfd797ca51


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = TaskListWidget(facade=None)
    test_widget.setWindowTitle("任务中心独立调试")
    test_widget.resize(600, 500)
    test_widget.show()
    sys.exit(app.exec())