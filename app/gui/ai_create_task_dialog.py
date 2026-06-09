"""AI 智能创建对话框：粘贴一段描述，AI 解析为任务/课程/考试。"""
from __future__ import annotations

from datetime import date, datetime, time

from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import (
    BORDER,
    INK,
    PKU_GOLD,
    PKU_RED,
    form_control_style,
    primary_button_style,
    secondary_button_style,
)


_TYPE_OPTIONS = [
    ("task", "📝 任务"),
    ("class", "📅 课程"),
    ("exam", "📋 考试"),
]


class AICreateDialog(QDialog):
    """One dialog for parsing → previewing → creating tasks/classes/exams."""

    def __init__(self, facade, parent=None) -> None:
        super().__init__(parent)
        self.facade = facade
        self._parsed: dict | None = None
        self._current_type = "task"
        self.setWindowTitle("✨ AI 智能创建")
        self.resize(560, 640)
        self.setStyleSheet(form_control_style())
        self._init_ui()

    # ── UI ────────────────────────────────────────────────────────────
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("✨ AI 智能创建")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        hint = QLabel(
            "粘贴一段描述，AI 会自动识别是任务、课程还是考试。\n"
            "示例：\n"
            "  · 提交研究报告，6月10号晚上9点截止\n"
            "  · 每周三晚 7-9 点高数课，理教 303，1-16 周\n"
            "  · 高数期末，6月20日 9:00-11:00，理教 303"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "font-size: 12px; color: #6B7280; background-color: transparent;"
        )
        layout.addWidget(hint)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "例如：每周三晚 7-9 点高数课，理教 303，1-16 周"
        )
        self.input_edit.setMinimumHeight(96)
        layout.addWidget(self.input_edit)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet(secondary_button_style())
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.parse_button = QPushButton("✨ 解析")
        self.parse_button.setStyleSheet(primary_button_style())
        self.parse_button.clicked.connect(self._on_parse_clicked)
        button_row.addWidget(self.parse_button)
        layout.addLayout(button_row)

        self.preview_frame = self._build_preview_frame()
        self.preview_frame.setVisible(False)
        layout.addWidget(self.preview_frame, stretch=1)

    def _build_preview_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: #FFFFFF; border: 1px solid {BORDER}; "
            f"border-radius: 6px; }}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        header_row = QHBoxLayout()
        header = QLabel("解析结果")
        header.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {INK}; background-color: transparent;"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        self.type_chip = QLabel("📝 任务")
        self.type_chip.setStyleSheet(
            f"background-color: {PKU_GOLD}; color: white; padding: 2px 10px; "
            f"border-radius: 10px; font-size: 12px; font-weight: 600;"
        )
        header_row.addWidget(self.type_chip)
        v.addLayout(header_row)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("类型："))
        self.type_combo = QComboBox()
        for value, label in _TYPE_OPTIONS:
            self.type_combo.addItem(label, value)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self.type_combo, stretch=1)
        v.addLayout(type_row)

        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self._build_task_form())
        self.preview_stack.addWidget(self._build_class_form())
        self.preview_stack.addWidget(self._build_exam_form())
        v.addWidget(self.preview_stack, stretch=1)

        confirm_row = QHBoxLayout()
        confirm_row.addStretch()
        self.confirm_button = QPushButton("确认创建")
        self.confirm_button.setStyleSheet(primary_button_style())
        self.confirm_button.clicked.connect(self._on_confirm_clicked)
        confirm_row.addWidget(self.confirm_button)
        v.addLayout(confirm_row)
        return frame

    def _build_task_form(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.task_title = QLineEdit()
        self.task_due = QDateTimeEdit()
        self.task_due.setCalendarPopup(True)
        self.task_due.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.task_desc = QTextEdit()
        self.task_desc.setMaximumHeight(72)
        self.task_hours = QSpinBox()
        self.task_hours.setRange(0, 999)
        self.task_hours.setValue(2)
        form.addRow("标题：", self.task_title)
        form.addRow("截止时间：", self.task_due)
        form.addRow("详情：", self.task_desc)
        form.addRow("预计耗时(小时)：", self.task_hours)
        return w

    def _build_class_form(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.class_title = QLineEdit()
        self.class_weekday = QComboBox()
        for i, name in enumerate(
            ["周一", "周二", "周三", "周四", "周五", "周六", "周日"], start=1
        ):
            self.class_weekday.addItem(name, i)
        self.class_start = QTimeEdit()
        self.class_start.setDisplayFormat("HH:mm")
        self.class_end = QTimeEdit()
        self.class_end.setDisplayFormat("HH:mm")
        self.class_location = QLineEdit()
        self.class_start_week = QSpinBox()
        self.class_start_week.setRange(1, 30)
        self.class_start_week.setValue(1)
        self.class_end_week = QSpinBox()
        self.class_end_week.setRange(1, 30)
        self.class_end_week.setValue(16)
        self.class_week_type = QComboBox()
        self.class_week_type.addItem("每周", "all")
        self.class_week_type.addItem("单周", "odd")
        self.class_week_type.addItem("双周", "even")

        week_row = QWidget()
        week_layout = QHBoxLayout(week_row)
        week_layout.setContentsMargins(0, 0, 0, 0)
        week_layout.addWidget(self.class_start_week)
        week_layout.addWidget(QLabel("—"))
        week_layout.addWidget(self.class_end_week)
        week_layout.addWidget(QLabel("周"))

        form.addRow("课程标题：", self.class_title)
        form.addRow("星期：", self.class_weekday)
        form.addRow("开始时间：", self.class_start)
        form.addRow("结束时间：", self.class_end)
        form.addRow("地点：", self.class_location)
        form.addRow("起止周：", week_row)
        form.addRow("单双周：", self.class_week_type)
        return w

    def _build_exam_form(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.exam_name = QLineEdit()
        self.exam_start = QDateTimeEdit()
        self.exam_start.setCalendarPopup(True)
        self.exam_start.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.exam_end = QDateTimeEdit()
        self.exam_end.setCalendarPopup(True)
        self.exam_end.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.exam_location = QLineEdit()
        self.exam_type = QComboBox()
        self.exam_type.addItem("期末", "final")
        self.exam_type.addItem("期中", "midterm")
        self.exam_type.addItem("小测", "quiz")
        self.exam_type.addItem("其他", "other")
        form.addRow("考试名：", self.exam_name)
        form.addRow("开始时间：", self.exam_start)
        form.addRow("结束时间：", self.exam_end)
        form.addRow("地点：", self.exam_location)
        form.addRow("类型：", self.exam_type)
        return w

    # ── 解析 ──────────────────────────────────────────────────────────
    def _on_parse_clicked(self) -> None:
        text = self.input_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "无法解析", "请先输入描述。")
            return

        original_label = self.parse_button.text()
        self.parse_button.setEnabled(False)
        self.parse_button.setText("解析中...")
        self.cancel_button.setEnabled(False)
        try:
            parsed = self.facade.ai_parse_item_from_text(text)
        except ValueError as exc:
            QMessageBox.warning(self, "解析失败", str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.warning(self, "解析失败", str(exc))
            return
        finally:
            self.parse_button.setEnabled(True)
            self.parse_button.setText(original_label)
            self.cancel_button.setEnabled(True)

        self._parsed = parsed
        item_type = parsed.get("type", "task")
        payload = parsed.get("payload", {})
        self._set_type(item_type, payload=payload)
        self.preview_frame.setVisible(True)

    # ── 类型切换 ──────────────────────────────────────────────────────
    def _set_type(self, item_type: str, *, payload: dict | None = None) -> None:
        if item_type not in {"task", "class", "exam"}:
            item_type = "task"
        self._current_type = item_type
        index = next(
            (i for i, (v, _) in enumerate(_TYPE_OPTIONS) if v == item_type), 0
        )
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(index)
        self.type_combo.blockSignals(False)
        self.type_chip.setText(_TYPE_OPTIONS[index][1])
        self.preview_stack.setCurrentIndex(index)
        if payload is not None:
            self._fill_form(item_type, payload)

    def _on_type_changed(self, index: int) -> None:
        new_type = self.type_combo.itemData(index)
        if new_type == self._current_type:
            return
        # Carry forward fields the user already filled in.
        carried = self._collect_carry_payload()
        self._current_type = new_type
        self.type_chip.setText(_TYPE_OPTIONS[index][1])
        self.preview_stack.setCurrentIndex(index)
        self._fill_form(new_type, carried)

    def _collect_carry_payload(self) -> dict:
        """Pull a best-effort 'shared' payload off the currently visible form."""
        carried: dict = {}
        if self._current_type == "task":
            carried["title"] = self.task_title.text().strip()
            dt = self.task_due.dateTime().toPython()
            if isinstance(dt, datetime):
                carried["start_time"] = dt
                carried["end_time"] = dt
                carried["due_time"] = dt
            carried["description"] = self.task_desc.toPlainText().strip()
        elif self._current_type == "class":
            carried["title"] = self.class_title.text().strip()
            carried["location"] = self.class_location.text().strip()
            carried["start_time_t"] = self.class_start.time().toPython()
            carried["end_time_t"] = self.class_end.time().toPython()
        elif self._current_type == "exam":
            carried["title"] = self.exam_name.text().strip()
            carried["location"] = self.exam_location.text().strip()
            sdt = self.exam_start.dateTime().toPython()
            edt = self.exam_end.dateTime().toPython()
            if isinstance(sdt, datetime):
                carried["start_time"] = sdt
                carried["due_time"] = sdt
            if isinstance(edt, datetime):
                carried["end_time"] = edt
        return carried

    # ── 填充表单 ──────────────────────────────────────────────────────
    def _fill_form(self, item_type: str, payload: dict) -> None:
        if item_type == "task":
            self._fill_task_form(payload)
        elif item_type == "class":
            self._fill_class_form(payload)
        elif item_type == "exam":
            self._fill_exam_form(payload)

    def _fill_task_form(self, payload: dict) -> None:
        self.task_title.setText(str(payload.get("title", "")))
        due = payload.get("due_time") or payload.get("start_time")
        if isinstance(due, datetime):
            self.task_due.setDateTime(QDateTime(due))
        else:
            self.task_due.setDateTime(QDateTime(datetime.now()))
        self.task_desc.setPlainText(str(payload.get("description", "")))
        try:
            hours = int(float(payload.get("estimated_hours", 2)))
        except (TypeError, ValueError):
            hours = 2
        self.task_hours.setValue(max(0, hours))

    def _fill_class_form(self, payload: dict) -> None:
        self.class_title.setText(str(payload.get("title", "")))
        weekday = payload.get("weekday")
        if isinstance(weekday, int) and 1 <= weekday <= 7:
            self.class_weekday.setCurrentIndex(weekday - 1)
        st = payload.get("start_time") or payload.get("start_time_t")
        et = payload.get("end_time") or payload.get("end_time_t")
        if isinstance(st, time):
            self.class_start.setTime(QTime(st.hour, st.minute))
        elif isinstance(st, datetime):
            self.class_start.setTime(QTime(st.hour, st.minute))
        if isinstance(et, time):
            self.class_end.setTime(QTime(et.hour, et.minute))
        elif isinstance(et, datetime):
            self.class_end.setTime(QTime(et.hour, et.minute))
        self.class_location.setText(str(payload.get("location", "")))
        self.class_start_week.setValue(int(payload.get("start_week", 1) or 1))
        self.class_end_week.setValue(int(payload.get("end_week", 16) or 16))
        wt = payload.get("week_type", "all")
        idx = {"all": 0, "odd": 1, "even": 2}.get(wt, 0)
        self.class_week_type.setCurrentIndex(idx)

    def _fill_exam_form(self, payload: dict) -> None:
        self.exam_name.setText(str(payload.get("name", "") or payload.get("title", "")))
        st = payload.get("start_time") or payload.get("due_time")
        et = payload.get("end_time")
        if isinstance(st, datetime):
            self.exam_start.setDateTime(QDateTime(st))
        else:
            self.exam_start.setDateTime(QDateTime(datetime.now()))
        if isinstance(et, datetime):
            self.exam_end.setDateTime(QDateTime(et))
        elif isinstance(st, datetime):
            self.exam_end.setDateTime(QDateTime(st))
        self.exam_location.setText(str(payload.get("location", "")))
        et_value = payload.get("exam_type", "final")
        idx = {"final": 0, "midterm": 1, "quiz": 2, "other": 3}.get(et_value, 0)
        self.exam_type.setCurrentIndex(idx)

    # ── 创建 ──────────────────────────────────────────────────────────
    def _on_confirm_clicked(self) -> None:
        try:
            if self._current_type == "task":
                self._create_task()
            elif self._current_type == "class":
                self._create_class()
            elif self._current_type == "exam":
                self._create_exam()
            else:
                QMessageBox.warning(self, "无法创建", "未知的类型。")
                return
        except ValueError as exc:
            QMessageBox.warning(self, "无法创建", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "创建失败", str(exc))
            return
        self.accept()

    def _create_task(self) -> None:
        title = self.task_title.text().strip()
        if not title:
            raise ValueError("请填写标题。")
        due = self.task_due.dateTime().toPython()
        if not isinstance(due, datetime):
            raise ValueError("请填写截止时间。")
        payload = {
            "title": title,
            "due_time": due,
            "description": self.task_desc.toPlainText().strip(),
            "estimated_hours": float(self.task_hours.value() or 0),
            "priority": 2,
            "status": "todo",
        }
        self.facade.create_task(payload)

    def _create_class(self) -> None:
        title = self.class_title.text().strip()
        if not title:
            raise ValueError("请填写课程标题。")
        weekday = self.class_weekday.currentData()
        if not isinstance(weekday, int) or not 1 <= weekday <= 7:
            raise ValueError("请选择星期。")
        st = self.class_start.time().toPython()
        et = self.class_end.time().toPython()
        if not isinstance(st, time) or not isinstance(et, time):
            raise ValueError("请填写上下课时间。")
        start_week = int(self.class_start_week.value())
        end_week = int(self.class_end_week.value())
        if end_week < start_week:
            end_week = start_week
        payload = {
            "title": title,
            "weekday": weekday,
            "start_time": st,
            "end_time": et,
            "location": self.class_location.text().strip(),
            "slot_type": "lecture",
            "start_week": start_week,
            "end_week": end_week,
            "week_type": self.class_week_type.currentData() or "all",
        }
        self.facade.create_schedule_slot(payload)

    def _create_exam(self) -> None:
        name = self.exam_name.text().strip()
        if not name:
            raise ValueError("请填写考试名。")
        st = self.exam_start.dateTime().toPython()
        et = self.exam_end.dateTime().toPython()
        if not isinstance(st, datetime) or not isinstance(et, datetime):
            raise ValueError("请填写考试时间。")
        payload = {
            "name": name,
            "start_time": st,
            "end_time": et,
            "location": self.exam_location.text().strip(),
            "exam_type": self.exam_type.currentData() or "final",
            "seat": "",
        }
        self.facade.create_exam(payload)


# Backward-compatible alias — older imports still work.
AICreateTaskDialog = AICreateDialog
