from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
)

from app.gui.theme import BORDER, INK, PKU_RED_LIGHT, TEXT, form_control_style, primary_button_style


def get_field(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class TaskEditorDialog(QDialog):
    def __init__(self, parent=None, task_data=None, facade=None):
        super().__init__(parent)
        self.task_data = task_data
        self.facade = facade
        self.ai_subtasks: list[dict] = []

        self.setWindowTitle("编辑任务" if task_data else "新建任务")
        self.resize(520, 460)
        self.setStyleSheet(form_control_style())
        self._init_ui()
        self._load_courses()
        if self.task_data:
            self._load_task_data()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("任务信息")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("例如：完成第七周高数作业")
        form.addRow("任务标题:", self.title_input)

        self.course_combo = QComboBox()
        form.addRow("所属课程:", self.course_combo)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("补充任务要求、提交格式或参考资料")
        self.description_input.setFixedHeight(86)
        form.addRow("任务描述:", self.description_input)

        self.due_time_input = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.due_time_input.setCalendarPopup(True)
        self.due_time_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("截止时间:", self.due_time_input)

        self.estimated_hours_input = QSpinBox()
        self.estimated_hours_input.setRange(1, 1000)
        self.estimated_hours_input.setSuffix(" 小时")
        self.estimated_hours_input.setValue(2)
        form.addRow("预计耗时:", self.estimated_hours_input)

        self.priority_combo = QComboBox()
        self.priority_combo.addItem("高", 1)
        self.priority_combo.addItem("中", 2)
        self.priority_combo.addItem("低", 3)
        self.priority_combo.setCurrentIndex(1)
        form.addRow("优先级:", self.priority_combo)

        layout.addLayout(form)

        ai_row = QHBoxLayout()
        self.ai_button = QPushButton("AI 帮我拆解")
        self.ai_button.setStyleSheet(primary_button_style())
        self.ai_button.clicked.connect(self._decompose_with_ai)
        ai_row.addStretch()
        ai_row.addWidget(self.ai_button)
        layout.addLayout(ai_row)

        self.ai_result_label = QLabel("")
        self.ai_result_label.setWordWrap(True)
        self.ai_result_label.setStyleSheet(
            f"background-color: {PKU_RED_LIGHT}; color: {TEXT}; border: 1px solid {BORDER}; "
            "border-radius: 6px; padding: 8px; font-size: 12px;"
        )
        self.ai_result_label.hide()
        layout.addWidget(self.ai_result_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._validate_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _load_courses(self) -> None:
        courses = []
        if self.facade and hasattr(self.facade, "list_courses"):
            try:
                courses = self.facade.list_courses()
            except NotImplementedError:
                courses = []
            except Exception as exc:
                print(f"[GUI] failed to load courses: {exc}")

        self.course_combo.clear()
        self.course_combo.addItem("不关联课程", None)
        for course in courses:
            self.course_combo.addItem(str(get_field(course, "name", "未命名课程")), get_field(course, "id"))

    def _load_task_data(self) -> None:
        self.title_input.setText(str(get_field(self.task_data, "title", "") or ""))
        self.description_input.setPlainText(str(get_field(self.task_data, "description", "") or ""))

        course_index = self.course_combo.findData(get_field(self.task_data, "course_id"))
        if course_index >= 0:
            self.course_combo.setCurrentIndex(course_index)

        due_time = get_field(self.task_data, "due_time")
        if isinstance(due_time, str):
            try:
                due_time = datetime.fromisoformat(due_time)
            except ValueError:
                due_time = None
        if isinstance(due_time, datetime):
            self.due_time_input.setDateTime(
                QDateTime(due_time.year, due_time.month, due_time.day, due_time.hour, due_time.minute)
            )

        self.estimated_hours_input.setValue(int(float(get_field(self.task_data, "estimated_hours", 2) or 2)))
        priority_index = self.priority_combo.findData(get_field(self.task_data, "priority", 2))
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

    def _decompose_with_ai(self) -> None:
        title = self.title_input.text().strip()
        description = self.description_input.toPlainText().strip() or title
        due_time = self.due_time_input.dateTime().toPython()
        if not title and not description:
            QMessageBox.warning(self, "输入不足", "请先填写任务标题或描述。")
            return

        if not self.facade or not hasattr(self.facade, "ai_decompose_task"):
            QMessageBox.information(self, "AI 不可用", "当前 facade 未提供任务拆解接口。")
            return

        try:
            if hasattr(self.facade, "ai_is_available") and not self.facade.ai_is_available():
                QMessageBox.information(self, "AI 不可用", "请先在设置中配置可用的 API Key。")
                return
            subtasks = self.facade.ai_decompose_task(description, due_time)
        except NotImplementedError:
            QMessageBox.information(self, "AI 不可用", "后端暂未实现任务拆解接口。")
            return
        except Exception as exc:
            QMessageBox.critical(self, "AI 调用失败", str(exc))
            return

        self.ai_subtasks = list(subtasks or [])
        if not self.ai_subtasks:
            QMessageBox.information(self, "AI 拆解", "没有生成可用子任务。")
            return

        lines = ["AI 建议拆解："]
        total_hours = 0.0
        for index, item in enumerate(self.ai_subtasks, start=1):
            sub_title = get_field(item, "title", f"子任务 {index}")
            hours = float(get_field(item, "estimated_hours", 1.0) or 1.0)
            total_hours += hours
            suggested_date = get_field(item, "suggested_date")
            date_text = f" · 建议 {suggested_date.strftime('%m-%d')}" if isinstance(suggested_date, datetime) else ""
            lines.append(f"{index}. {sub_title}（{hours:g}h{date_text}）")

        if total_hours > 0:
            self.estimated_hours_input.setValue(max(1, int(round(total_hours))))
        self.ai_result_label.setText("\n".join(lines))
        self.ai_result_label.show()

    def _validate_accept(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "输入错误", "任务标题不能为空。")
            self.title_input.setFocus()
            return
        self.accept()

    def get_task_data(self) -> dict:
        return {
            "title": self.title_input.text().strip(),
            "course_id": self.course_combo.currentData(),
            "description": self.description_input.toPlainText().strip(),
            "due_time": self.due_time_input.dateTime().toPython(),
            "estimated_hours": float(self.estimated_hours_input.value()),
            "priority": self.priority_combo.currentData(),
            "status": get_field(self.task_data, "status", "todo") if self.task_data else "todo",
        }


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = TaskEditorDialog()
    dialog.show()
    sys.exit(app.exec())
