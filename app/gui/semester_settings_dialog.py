"""学期设置对话框：开始日期 + 总周数。"""
from __future__ import annotations

from datetime import date
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QMessageBox, QSpinBox, QVBoxLayout,
)
from app.gui.theme import INK, form_control_style


class SemesterSettingsDialog(QDialog):
    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.setWindowTitle("学期设置")
        self.resize(360, 200)
        self.setStyleSheet(form_control_style())
        self._init_ui()
        self._load_current()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("学期设置")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {INK};")
        layout.addWidget(title)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.start_input = QDateEdit()
        self.start_input.setCalendarPopup(True)
        self.start_input.setDisplayFormat("yyyy-MM-dd")
        form.addRow("学期开始（周一）:", self.start_input)
        self.weeks_input = QSpinBox()
        self.weeks_input.setRange(1, 30)
        self.weeks_input.setSuffix(" 周")
        form.addRow("总周数:", self.weeks_input)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_current(self):
        if not self.facade or not hasattr(self.facade, "get_semester_settings"):
            self.start_input.setDate(QDate.currentDate())
            self.weeks_input.setValue(20)
            return
        try:
            s = self.facade.get_semester_settings()
            d = date.fromisoformat(s.get("start", ""))
            self.start_input.setDate(QDate(d.year, d.month, d.day))
            self.weeks_input.setValue(int(s.get("total_weeks") or 20))
        except Exception:
            self.start_input.setDate(QDate.currentDate())
            self.weeks_input.setValue(20)

    def _save(self):
        qd = self.start_input.date()
        start_iso = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        try:
            self.facade.set_semester_settings(
                start=start_iso, total_weeks=self.weeks_input.value()
            )
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self.accept()
