from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.gui.theme import INK, form_control_style, primary_button_style, secondary_button_style
from app.services import credentials_store


class _LoginWorker(QObject):
    succeeded = Signal(str, str)
    failed = Signal(str)

    def __init__(self, auth_client, username: str, password: str) -> None:
        super().__init__()
        self.auth_client = auth_client
        self.username = username
        self.password = password

    def run(self) -> None:
        try:
            self.auth_client.login(self.username, self.password)
        except Exception as exc:
            self.failed.emit(str(exc) or "登录失败")
            return
        self.succeeded.emit(self.username, self.password)


class LoginDialog(QDialog):
    def __init__(self, auth_client, parent=None) -> None:
        super().__init__(parent)
        self.auth_client = auth_client
        self._thread: QThread | None = None
        self._worker: _LoginWorker | None = None
        self.setWindowTitle("登录教学网")
        self.resize(360, 220)
        self.setStyleSheet(form_control_style())
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("登录教学网")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {INK};")
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

        self.remember_cb = QCheckBox("记住我（保存到 .env）")
        self.remember_cb.setChecked(True)
        self.remember_cb.setEnabled(False)
        self.remember_cb.setToolTip("必须勾选才能保存登录")
        layout.addWidget(self.remember_cb)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #C0392B; font-size: 12px; background-color: transparent;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet(secondary_button_style())
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.login_button = QPushButton("登录")
        self.login_button.setStyleSheet(primary_button_style())
        self.login_button.clicked.connect(self._on_login_clicked)
        self.login_button.setDefault(True)
        button_row.addWidget(self.login_button)
        layout.addLayout(button_row)

    def _on_login_clicked(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self._show_error("请输入账号和密码")
            return
        if self.auth_client is None:
            self._show_error("登录服务不可用")
            return
        self._set_busy(True)
        self.error_label.hide()

        thread = QThread(self)
        worker = _LoginWorker(self.auth_client, username, password)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self._on_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_succeeded(self, username: str, password: str) -> None:
        try:
            credentials_store.save(username, password)
        except Exception as exc:
            self._show_error(f"保存凭据失败：{exc}")
            self._set_busy(False)
            return
        self.accept()

    def _on_failed(self, message: str) -> None:
        self._show_error(f"登录失败：{message}")
        self._set_busy(False)

    def _clear_thread(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _set_busy(self, busy: bool) -> None:
        self.login_button.setEnabled(not busy)
        self.username_input.setEnabled(not busy)
        self.password_input.setEnabled(not busy)
        self.login_button.setText("登录中…" if busy else "登录")

    def closeEvent(self, event) -> None:
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(2000)
        super().closeEvent(event)

    @staticmethod
    def run(parent, auth_client) -> bool:
        dialog = LoginDialog(auth_client=auth_client, parent=parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
