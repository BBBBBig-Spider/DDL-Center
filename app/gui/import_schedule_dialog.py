"""Import schedule slots from a JSON file or pasted JSON text."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.gui.theme import BORDER, INK, PKU_RED, form_control_style, primary_button_style, secondary_button_style

_EXAMPLE = """\
[
  {
    "title": "高等数学",
    "weekday": 1,
    "start_time": "08:00",
    "end_time": "09:50",
    "location": "理教303",
    "slot_type": "lecture",
    "start_week": 1,
    "end_week": 16,
    "week_type": "all"
  }
]"""


class ImportScheduleDialog(QDialog):
    """Paste or load a JSON course-table and bulk-import into the schedule."""

    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.setWindowTitle("导入课表")
        self.resize(560, 480)
        self.setStyleSheet(form_control_style())
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("批量导入课表")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        hint = QLabel(
            "支持 JSON 格式。每条记录至少需要：title、weekday (1-7)、"
            "start_time、end_time、start_week、end_week。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #6B7280;")
        layout.addWidget(hint)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(_EXAMPLE)
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background:#FFFFFF; color:{INK}; border:1px solid {BORDER}; "
            "border-radius:4px; padding:8px; font-family:monospace; font-size:12px; }}"
        )
        layout.addWidget(self.text_edit, stretch=1)

        file_row = QHBoxLayout()
        load_btn = QPushButton("从文件加载")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setStyleSheet(secondary_button_style())
        load_btn.clicked.connect(self._load_file)
        file_row.addWidget(load_btn)
        file_row.addStretch()
        layout.addLayout(file_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(secondary_button_style())
        cancel_btn.clicked.connect(self.reject)
        import_btn = QPushButton("导入")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(primary_button_style())
        import_btn.clicked.connect(self._do_import)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(import_btn)
        layout.addLayout(btn_row)

    def _load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择课表 JSON 文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        self.text_edit.setPlainText(text)

    def _do_import(self) -> None:
        raw = self.text_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "内容为空", "请粘贴或加载课表 JSON 内容。")
            return

        # Parse JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "JSON 解析失败", f"格式错误：{exc}")
            return

        if not isinstance(data, list):
            QMessageBox.critical(self, "格式错误", "顶层结构必须是 JSON 数组 [ … ]。")
            return

        if not self.facade or not hasattr(self.facade, "create_schedule_slot"):
            QMessageBox.critical(self, "无法导入", "当前 Facade 没有提供课表写入接口。")
            return

        ok = 0
        errors: list[str] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"第 {i+1} 条：不是对象，已跳过")
                continue
            try:
                self.facade.create_schedule_slot(item)
                ok += 1
            except Exception as exc:
                title = item.get("title", f"第{i+1}条")
                errors.append(f"{title}：{exc}")

        msg = f"成功导入 {ok} 条课表记录。"
        if errors:
            detail = "\n".join(errors[:10])
            if len(errors) > 10:
                detail += f"\n……（共 {len(errors)} 条失败）"
            QMessageBox.warning(self, "部分导入失败", f"{msg}\n\n以下条目导入失败：\n{detail}")
        else:
            QMessageBox.information(self, "导入完成", msg)

        if ok > 0:
            self.accept()
        # if all failed, keep dialog open so user can fix
