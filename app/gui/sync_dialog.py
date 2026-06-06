from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.gui.theme import BORDER, INK, form_control_style, primary_button_style


def get_field(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class SyncDialog(QDialog):
    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.setWindowTitle("同步教学网")
        self.resize(560, 420)
        self.setStyleSheet(form_control_style())
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("教学网同步")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("学号")
        form.addRow("账号:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("密码")
        form.addRow("密码:", self.password_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.sync_button = QPushButton("开始同步")
        self.sync_button.setStyleSheet(primary_button_style())
        self.sync_button.clicked.connect(self._sync)
        button_row.addWidget(self.sync_button)
        layout.addLayout(button_row)

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("同步结果会显示在这里。")
        self.result_output.setStyleSheet(
            f"QTextEdit {{ background: #FFFFFF; color: {INK}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; }}"
        )
        layout.addWidget(self.result_output, stretch=1)

    def _sync(self) -> None:
        if not self.facade or not hasattr(self.facade, "sync_from_teaching_site"):
            QMessageBox.warning(self, "无法同步", "当前 Facade 没有提供教学网同步接口。")
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        self._set_busy(True, "正在同步教学网...")

        try:
            result = self.facade.sync_from_teaching_site(username, password)
        except NotImplementedError:
            self.result_output.setPlainText("后端暂未实现教学网同步接口。")
            self._set_busy(False)
            return
        except Exception as exc:
            self.result_output.setPlainText(f"同步失败：{exc}")
            self._set_busy(False)
            return

        self._show_result(result)
        self._set_busy(False)

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self.sync_button.setEnabled(not busy)
        if message is not None:
            self.result_output.setPlainText(message)

    def _show_result(self, result) -> None:
        message = self._format_result(result)
        summary = self._summarize(message)
        if summary:
            message = f"AI 摘要：{summary}\n\n{message}"
        self.result_output.setPlainText(message)

    def _format_result(self, result) -> str:
        source = get_field(result, "source", "network")
        used_mock = get_field(result, "used_mock", False)
        errors = get_field(result, "errors", [])

        tasks_new = get_field(result, "tasks_new", 0)
        tasks_updated = get_field(result, "tasks_updated", 0)
        tasks_unchanged = get_field(result, "tasks_unchanged", 0)
        schedule_new = get_field(result, "schedule_new", 0)
        schedule_updated = get_field(result, "schedule_updated", 0)
        exams_new = get_field(result, "exams_new", 0)
        exams_updated = get_field(result, "exams_updated", 0)
        courses_new = get_field(result, "courses_new", 0)

        source_label = "模拟数据" if used_mock else ("网络" if source == "network" else source)
        lines = [f"同步完成（来源：{source_label}）"]
        lines.append(f"任务：新增 {tasks_new}，更新 {tasks_updated}，未变 {tasks_unchanged}")
        lines.append(f"课表：新增 {schedule_new}，更新 {schedule_updated}")
        lines.append(f"考试：新增 {exams_new}，更新 {exams_updated}")
        if courses_new:
            lines.append(f"课程：新增 {courses_new}")
        if errors:
            lines.append("")
            lines.append("警告：")
            for err in errors:
                lines.append(f"  • {err}")
        return "\n".join(lines)

    def _summarize(self, text: str) -> str:
        if not self.facade or not hasattr(self.facade, "ai_summarize_ddl"):
            return ""
        try:
            return str(self.facade.ai_summarize_ddl(text) or "").strip()
        except Exception:
            return ""
