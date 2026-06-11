from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from app.gui.theme import BORDER, INK, PRIMARY, primary_button_style, secondary_button_style


class AIChatPanel(QWidget):
    """Embedded AI chat panel backed by AppFacade.ai_chat."""

    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.conversation_id: int | None = None
        self._init_ui()
        self._append_assistant("你好，我是 DDL 指挥中心的 AI 助手。你可以直接询问任务拆解、学习安排或课程问题。")

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QFrame()
        header.setStyleSheet(
            f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QFrame QLabel {{
                background-color: transparent;
            }}
            """
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("AI 学习助手")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {INK};")
        subtitle = QLabel("当前页面调用真实 AI 接口；请先在 AI 设置中配置 DeepSeek API Key。")
        subtitle.setStyleSheet("font-size: 12px; color: #6B7280;")
        subtitle.setWordWrap(True)
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch()
        self.new_chat_button = QPushButton("新对话")
        self.new_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_button.setStyleSheet(secondary_button_style())
        self.new_chat_button.clicked.connect(self.restart_conversation)
        title_row.addWidget(self.new_chat_button)
        header_layout.addLayout(title_row)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(True)
        self.chat_view.setStyleSheet(
            f"""
            QTextBrowser {{
                background-color: #FFFFFF;
                color: {INK};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }}
            """
        )
        layout.addWidget(self.chat_view, stretch=1)

        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入问题，例如：帮我安排高数作业的完成计划")
        self.input_edit.returnPressed.connect(self._send)
        self.input_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: #FFFFFF;
                color: {INK};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {PRIMARY};
            }}
            """
        )
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
            self._append_assistant("当前没有连接真实 AI 接口。")
            return
        try:
            if hasattr(self.facade, "ai_is_available") and not self.facade.ai_is_available():
                self._append_assistant("AI 暂不可用，请先在 AI 设置里配置 DeepSeek API Key。")
                return
            self.conversation_id, reply = self.facade.ai_chat(self.conversation_id, user_msg)
        except NotImplementedError:
            self._append_assistant("后端暂未实现 AI 对话接口。")
            return
        except Exception as exc:
            QMessageBox.critical(self, "AI 调用失败", str(exc))
            return
        self._append_assistant(str(reply))

    def restart_conversation(self) -> None:
        if self.facade and hasattr(self.facade, "ai_reset_conversation"):
            try:
                self.facade.ai_reset_conversation(self.conversation_id)
            except Exception:
                pass
        self.conversation_id = None
        self.chat_view.clear()
        self._append_assistant("已开始新对话。你可以重新描述当前任务、课程或计划需求。")

    def _append_user(self, text: str) -> None:
        self.chat_view.append(f"<p><b style='color:{PRIMARY}'>你：</b>{self._escape(text)}</p>")

    def _append_assistant(self, text: str) -> None:
        self.chat_view.append(f"<p><b style='color:#7A4F00'>AI：</b>{self._escape(text)}</p>")

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
