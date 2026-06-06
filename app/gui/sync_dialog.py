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
        success = get_field(result, "success", True)
        message = get_field(result, "message", "同步完成。")
        created = get_field(result, "created", 0)
        updated = get_field(result, "updated", 0)
        skipped = get_field(result, "skipped", 0)
        status = "成功" if success else "失败"
        return (
            f"同步状态：{status}\n"
            f"结果说明：{message}\n"
            f"新增：{created}\n"
            f"更新：{updated}\n"
            f"跳过：{skipped}"
        )

    def _summarize(self, text: str) -> str:
        if not self.facade or not hasattr(self.facade, "ai_summarize_ddl"):
            return ""
        try:
            return str(self.facade.ai_summarize_ddl(text) or "").strip()
        except Exception:
            return ""
