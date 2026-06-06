from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.gui.theme import INK, TEXT, form_control_style, primary_button_style


class SettingsDialog(QDialog):
    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.setWindowTitle("设置")
        self.resize(460, 220)
        self.setStyleSheet(form_control_style())
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("DeepSeek API 设置")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        form.addRow("API Key:", self.api_key_input)

        usage_row = QHBoxLayout()
        self.usage_label = QLabel("今日 token 用量：未知")
        self.usage_label.setStyleSheet(f"color: {TEXT};")
        usage_row.addWidget(self.usage_label)
        usage_row.addStretch()
        form.addRow("用量:", usage_row)
        layout.addLayout(form)

        self.test_button = QPushButton("测试 Key")
        self.test_button.setStyleSheet(primary_button_style())
        self.test_button.clicked.connect(self._test_key)
        layout.addWidget(self.test_button, alignment=Qt.AlignmentFlag.AlignRight)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self) -> None:
        if not self.facade:
            return
        try:
            if hasattr(self.facade, "get_deepseek_api_key"):
                key = self.facade.get_deepseek_api_key()
                if key:
                    self.api_key_input.setText(key)
            if hasattr(self.facade, "ai_today_token_usage"):
                self.usage_label.setText(f"今日 token 用量：{self.facade.ai_today_token_usage()}")
        except Exception as exc:
            self.usage_label.setText(f"设置读取失败：{exc}")

    def _test_key(self) -> None:
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "输入错误", "请先输入 API Key。")
            return
        if not self.facade or not hasattr(self.facade, "test_deepseek_api_key"):
            QMessageBox.information(self, "测试结果", "当前 facade 未提供 Key 测试接口。")
            return
        try:
            ok = self.facade.test_deepseek_api_key(key)
        except NotImplementedError:
            QMessageBox.information(self, "测试结果", "后端暂未实现 Key 测试接口。")
            return
        except Exception as exc:
            QMessageBox.critical(self, "测试失败", str(exc))
            return
        QMessageBox.information(self, "测试结果", "Key 可用。" if ok else "Key 不可用。")

    def _save(self) -> None:
        key = self.api_key_input.text().strip()
        if self.facade and hasattr(self.facade, "set_deepseek_api_key"):
            try:
                self.facade.set_deepseek_api_key(key)
            except NotImplementedError:
                QMessageBox.information(self, "保存提示", "后端暂未实现 API Key 保存接口。")
            except Exception as exc:
                QMessageBox.critical(self, "保存失败", str(exc))
                return
        self.accept()
