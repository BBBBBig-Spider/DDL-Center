"""Import schedule slots and optional exam data from JSON or PKU Portal HTML."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
)

from app.gui.theme import BORDER, INK, form_control_style, primary_button_style, secondary_button_style

_EXAMPLE = """\
{
  "exam_week_start": "2026-06-15",
  "exam_week_end": "2026-06-28",
  "slots": [
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
  ],
  "exams": [
    {
      "name": "高等数学考试",
      "start_time": "2026-06-20 09:00",
      "end_time": "2026-06-20 11:00",
      "location": "理教303",
      "exam_type": "final"
    }
  ]
}"""


class ImportScheduleDialog(QDialog):
    """Paste or load a JSON/Portal course table and import schedule plus exams."""

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
            "支持 JSON 格式或北京大学门户课表 HTML。JSON 可以是旧的课表数组，"
            "也可以是包含 slots、exams、exam_week_start、exam_week_end 的对象。"
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

        # Import mode: overwrite (default) clears existing schedule + exam
        # rows before importing; merge upserts on external_id only. Default
        # to overwrite so a user re-running the import doesn't end up with
        # stale slots from a previous semester sitting alongside the new ones.
        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        mode_label = QLabel("导入方式：")
        mode_label.setStyleSheet(f"color: {INK}; font-weight: 700;")
        mode_row.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        self.overwrite_radio = QRadioButton("覆盖（清空原有课表与考试，再导入）")
        self.merge_radio = QRadioButton("合并（保留原有，新条目按 external_id 去重更新）")
        self.overwrite_radio.setChecked(True)
        self.mode_group.addButton(self.overwrite_radio)
        self.mode_group.addButton(self.merge_radio)
        mode_row.addWidget(self.overwrite_radio)
        mode_row.addWidget(self.merge_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

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
            self,
            "选择课表文件",
            "",
            "课表文件 (*.json *.html *.htm);;所有文件 (*)",
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
            QMessageBox.warning(self, "内容为空", "请粘贴或加载课表内容。")
            return
        if not self.facade or not hasattr(self.facade, "create_schedule_slot"):
            QMessageBox.critical(self, "无法导入", "当前 Facade 没有提供课表写入接口。")
            return

        parsed = self._parse_html(raw) if raw.lstrip().startswith("<") else self._parse_json(raw)
        if parsed is None:
            return

        # Overwrite mode wipes the existing schedule + exam tables first so
        # the import lands on a clean slate. Merge mode skips this — upsert
        # on external_id (handled in the manager layer) keeps it idempotent.
        if self.overwrite_radio.isChecked():
            if hasattr(self.facade, "clear_all_schedule_and_exams"):
                try:
                    counts = self.facade.clear_all_schedule_and_exams()
                    print(f"[IMPORT] overwrite cleared: {counts}")
                except Exception as exc:
                    QMessageBox.critical(self, "清空失败", str(exc))
                    return

        ok, exam_ok, errors = self._import_parsed(parsed)
        msg = f"成功导入 {ok} 条课表记录。"
        if exam_ok:
            msg += f"\n成功导入 {exam_ok} 条考试信息。"
        exam_week_start = parsed.get("exam_week_start")
        exam_week_end = parsed.get("exam_week_end")
        if exam_week_start or exam_week_end:
            msg += f"\n考试周：{exam_week_start or '未知'} 至 {exam_week_end or '未知'}。"

        if errors:
            detail = "\n".join(errors[:10])
            if len(errors) > 10:
                detail += f"\n……（共 {len(errors)} 条失败）"
            QMessageBox.warning(self, "部分导入失败", f"{msg}\n\n以下条目导入失败：\n{detail}")
        else:
            QMessageBox.information(self, "导入完成", msg)

        if ok > 0 or exam_ok > 0:
            self.accept()

    def _import_parsed(self, parsed: dict) -> tuple[int, int, list[str]]:
        ok = 0
        exam_ok = 0
        errors: list[str] = []
        for index, item in enumerate(parsed.get("slots", []), start=1):
            if not isinstance(item, dict):
                errors.append(f"课表第 {index} 条：不是对象，已跳过")
                continue
            try:
                self.facade.create_schedule_slot(item)
                ok += 1
            except Exception as exc:
                errors.append(f"{item.get('title', f'课表第 {index} 条')}：{exc}")

        exams = parsed.get("exams", [])
        if exams and not hasattr(self.facade, "create_exam"):
            errors.append("已解析到考试信息，但当前 Facade 没有提供考试写入接口。")
        for index, item in enumerate(exams, start=1):
            if not isinstance(item, dict):
                errors.append(f"考试第 {index} 条：不是对象，已跳过")
                continue
            try:
                self.facade.create_exam(item)
                exam_ok += 1
            except Exception as exc:
                errors.append(f"{item.get('name', f'考试第 {index} 条')}：{exc}")

        if hasattr(self.facade, "set_exam_week_range"):
            try:
                self.facade.set_exam_week_range(parsed.get("exam_week_start"), parsed.get("exam_week_end"))
            except Exception as exc:
                errors.append(f"考试周范围保存失败：{exc}")
        return ok, exam_ok, errors

    def _parse_json(self, raw: str) -> dict | None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "JSON 解析失败", f"格式错误：{exc}")
            return None
        if isinstance(data, list):
            return {"slots": data, "exams": [], "exam_week_start": None, "exam_week_end": None}
        if not isinstance(data, dict):
            QMessageBox.critical(self, "格式错误", "JSON 顶层结构必须是课表数组，或包含 slots/exams 的对象。")
            return None
        slots = data.get("slots") or data.get("schedule") or []
        exams = data.get("exams") or []
        if not isinstance(slots, list) or not isinstance(exams, list):
            QMessageBox.critical(self, "格式错误", "slots 和 exams 必须是数组。")
            return None
        return {
            "slots": slots,
            "exams": exams,
            "exam_week_start": data.get("exam_week_start"),
            "exam_week_end": data.get("exam_week_end"),
        }

    def _parse_html(self, raw: str) -> dict | None:
        try:
            from app.parsers.portal_schedule_parser import parse_portal_import

            parsed = parse_portal_import(raw)
        except Exception as exc:
            QMessageBox.critical(self, "HTML 解析失败", f"无法解析课表 HTML：{exc}")
            return None
        if not parsed.get("slots"):
            QMessageBox.warning(self, "未识别课表", "未从 HTML 中解析出任何课程，请确认文件来自北大门户课表页面。")
            return None

        self._attach_course_ids(parsed)
        return parsed

    def _attach_course_ids(self, parsed: dict) -> None:
        if not self.facade or not hasattr(self.facade, "find_or_create_course_by_name"):
            return
        course_id_map: dict[str, int] = {}
        for slot in parsed.get("slots", []):
            name = slot.get("title", "").strip() if isinstance(slot, dict) else ""
            if name and name not in course_id_map:
                course_id = self.facade.find_or_create_course_by_name(name)
                if course_id is not None:
                    course_id_map[name] = course_id
        for slot in parsed.get("slots", []):
            if isinstance(slot, dict) and slot.get("title", "").strip() in course_id_map:
                slot["course_id"] = course_id_map[slot["title"].strip()]
        for exam in parsed.get("exams", []):
            if isinstance(exam, dict) and exam.get("course_name", "").strip() in course_id_map:
                exam["course_id"] = course_id_map[exam["course_name"].strip()]
