import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QDateTimeEdit, QSpinBox, QDialogButtonBox, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QDateTime
from app.managers.app_facade import AppFacade

class TaskEditorDialog(QDialog):
    def __init__(self, parent = None, task_data = None, facade = None): 
        super().__init__(parent)
        self.task_data = task_data
        self.facade = facade
        self.db_courses = []
        if self.task_data: 
            self.setWindowTitle("编辑任务")
        else: 
            self.setWindowTitle("新建任务")
        
        self.resize(400, 300)
        self.init_ui()

        self.load_courses_from_backend()

        if self.task_data: 
            self.load_task_data()
    
    def init_ui(self): 
        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(12)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请输入任务标题(例如：完成第七周高数作业)")
        form_layout.addRow("任务标题:", self.title_input)

        self.course_combo = QComboBox()
        form_layout.addRow("所属课程:", self.course_combo)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("请输入任务描述(选填)")
        form_layout.addRow("任务描述:", self.description_input)

        self.due_time_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.due_time_input.setCalendarPopup(True)
        self.due_time_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("截止时间:", self.due_time_input)

        self.estimated_hours_input = QSpinBox()
        self.estimated_hours_input.setRange(0, 1000)
        self.estimated_hours_input.setSuffix(" 小时")
        form_layout.addRow("预计耗时:", self.estimated_hours_input)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["低(蓝色)", "中(黄色)", "高(红色)"])
        form_layout.addRow("优先级:", self.priority_combo)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.valid_accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)

    def load_courses_from_backend(self): 
        self.course_combo.clear()
        self.course_combo.addItem("通用任务", userData = None)
        try: 
            self.db_courses = self.facade.list_courses()
            for course in self.db_courses: 
                c_id = course.get("id") if isinstance(course, dict) else getattr(course, "id", None)
                c_name = course.get("name") if isinstance(course, dict) else getattr(course, "name", "未知课程")
                self.course_combo.addItem(c_name, c_id)
        except Exception as e:
            print(f"[GUI] 获取课程失败: {e}")
    
    def _get_field(self, obj, key, default = " "):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def load_task_data(self):
        self.title_input.setText(self._get_field(self.task_data, "title", ""))
        self.description_input.setText(self._get_field(self.task_data, "description", ""))

        target_course_id = self._get_field(self.task_data, "course_id", None)
        index = self.course_combo.findData(target_course_id)
        if index != -1:
            self.course_combo.setCurrentIndex(index)
        
        dt = self._get_field(self.task_data, "due_time", None)
        if dt:
            self.due_time_input.setDateTime(QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0))
        
        self.estimated_hours_input.setValue(int(self._get_field(self.task_data, "estimated_hours", 2)))

        p_val = self._get_field(self.task_data, "priority", 2)
        p_map = {1: "高(红色)", 2: "中(黄色)", 3: "低(蓝色)"}
        p_text = p_map.get(p_val, "中(黄色)")
        p_index = self.priority_combo.findText(p_text)
        if p_index != -1:
            self.priority_combo.setCurrentIndex(p_index)
    
    def valid_accept(self): 
        title = self.title_input.text().strip()
        if not title: 
            QMessageBox.warning(self, "输入错误", "任务标题不能为空！")
            self.title_input.setFocus()
            return
        
        self.accept()
    
    def get_task_data(self): 
        return {
            "title": self.title_input.text().strip(),
            "course_id": self.course_combo.currentData(),
            "description": self.description_input.text().strip(),
            "due_time": self.due_time_input.dateTime().toPython(),
            "estimated_hours": self.estimated_hours_input.value(),
            "priority": 3 - self.priority_combo.currentIndex()
        }