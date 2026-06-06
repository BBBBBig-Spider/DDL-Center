from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.gui.theme import BORDER, INK, PKU_RED, form_control_style, primary_button_style


class AIChatDialog(QDialog):
    def __init__(self, facade=None, context_task_id: int | None = None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.context_task_id = context_task_id
        self.conversation_id: int | None = None
        self.setWindowTitle("AI 学习助手")
        self.resize(620, 520)
        self.setStyleSheet(form_control_style())
        self._init_ui()
        self._append_assistant("你好，我可以帮你拆解任务、规划学习节奏，或解释课程问题。")

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("AI 学习助手")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(True)
        self.chat_view.setStyleSheet(
            f"""
            QTextBrowser {{
                background-color: #FFFFFF;
                color: {INK};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
            """
        )
        layout.addWidget(self.chat_view, stretch=1)

        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入问题或学习计划需求...")
        self.input_edit.returnPressed.connect(self._send)
        input_row.addWidget(self.input_edit, stretch=1)

        self.send_button = QPushButton("发送")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setStyleSheet(primary_button_style())
        self.send_button.clicked.connect(self._send)
        input_row.addWidget(self.send_button)
        layout.addLayout(input_row)

    def _send(self) -> None:
        user_msg = self.input_edit.text().strip()
        if not user_msg:
            return
        self.input_edit.clear()
        self._append_user(user_msg)

        if not self.facade or not hasattr(self.facade, "ai_chat"):
            self._append_assistant("当前 AI 接口未接入。")
            return

        try:
            if hasattr(self.facade, "ai_is_available") and not self.facade.ai_is_available():
                self._append_assistant("AI 暂不可用，请先在设置中配置 API Key。")
                return
            self.conversation_id, reply = self.facade.ai_chat(
                self.conversation_id,
                user_msg,
                context_task_id=self.context_task_id,
            )
        except NotImplementedError:
            self._append_assistant("后端暂未实现 AI 对话接口。")
            return
        except Exception as exc:
            QMessageBox.critical(self, "AI 调用失败", str(exc))
            return
        self._append_assistant(str(reply))

    def _append_user(self, text: str) -> None:
        self.chat_view.append(f"<p><b style='color:{PKU_RED}'>你：</b>{self._escape(text)}</p>")

    def _append_assistant(self, text: str) -> None:
        self.chat_view.append(f"<p><b style='color:#7A4F00'>AI：</b>{self._escape(text)}</p>")

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
