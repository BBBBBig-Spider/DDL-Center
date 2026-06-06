from __future__ import annotations

import sys
from datetime import date, datetime, time

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.gui.add_schedule_dialog import AddCourseDialog
from app.gui.import_schedule_dialog import ImportScheduleDialog
from app.gui.theme import BORDER, INK, PKU_GOLD, PKU_RED, PKU_RED_DARK, PKU_RED_LIGHT, TEXT, secondary_button_style
from app.config import SEMESTER_START


def get_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class DDLMarkerWidget(QFrame):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.expanded = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("ddlMarker")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(12)
        self.setStyleSheet(
            f"""
            QFrame#ddlMarker {{
                background-color: #FCE8E8;
                border-left: 4px solid {PKU_RED};
                border-radius: 4px;
            }}
            QFrame#ddlMarker QLabel {{
                background-color: transparent;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        self.title = QLabel("DDL")
        self.title.setStyleSheet(f"color: {PKU_RED_DARK}; font-size: 10px; font-weight: 700;")
        self.title.setVisible(False)
        layout.addWidget(self.title)

    def enterEvent(self, event) -> None:
        task_title = str(get_field(self.task, "title", "未命名任务"))
        due_time = get_field(self.task, "due_time")
        due_text = due_time.strftime("%H:%M") if hasattr(due_time, "strftime") else str(due_time)[11:16]
        self.title.setText(f"DDL {due_text} · {task_title}")
        self.title.setVisible(True)
        self.setFixedHeight(46)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.title.setVisible(False)
        self.setFixedHeight(12)
        super().leaveEvent(event)


class ScheduleWidget(QWidget):
    PERIODS = [
        ("第1节\n08:00-08:50", time(8, 0), time(8, 50)),
        ("第2节\n09:00-09:50", time(9, 0), time(9, 50)),
        ("第3节\n10:10-11:00", time(10, 10), time(11, 0)),
        ("第4节\n11:10-12:00", time(11, 10), time(12, 0)),
        ("第5节\n13:00-13:50", time(13, 0), time(13, 50)),
        ("第6节\n14:00-14:50", time(14, 0), time(14, 50)),
        ("第7节\n15:10-16:00", time(15, 10), time(16, 0)),
        ("第8节\n16:10-17:00", time(16, 10), time(17, 0)),
        ("第9节\n17:10-18:00", time(17, 10), time(18, 0)),
        ("第10节\n18:40-19:30", time(18, 40), time(19, 30)),
        ("第11节\n19:40-20:30", time(19, 40), time(20, 30)),
        ("第12节\n20:40-21:30", time(20, 40), time(21, 30)),
    ]

    def __init__(self, facade=None):
        super().__init__()
        self.facade = facade
        self.current_week = self._current_semester_week()
        self.custom_slots = []
        self.gui_task_arrangements = []
        self._next_local_slot_id = 1
        self._course_color_cache: dict[int, str] = {}  # course_id -> hex color
        self._init_ui()
        self.refresh_schedule()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        self._setup_top_bar()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        grid_container = QWidget()
        grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(8)
        self._setup_grid_frame()

        scroll_area.setWidget(grid_container)
        self.main_layout.addWidget(scroll_area, stretch=1)

    def _setup_top_bar(self) -> None:
        top_bar = QHBoxLayout()
        title = QLabel("课程表")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {INK}; background-color: transparent;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.show_arrangements_checkbox = QCheckBox("显示 DDL 任务安排")
        self.show_arrangements_checkbox.setChecked(True)
        self.show_arrangements_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_arrangements_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {TEXT};
                background-color: transparent;
                font-size: 13px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {PKU_RED};
                border: 1px solid {PKU_RED};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {BORDER};
                background-color: #FFFFFF;
            }}
            """
        )
        self.show_arrangements_checkbox.stateChanged.connect(self.refresh_schedule)
        top_bar.addWidget(self.show_arrangements_checkbox)

        add_button = QPushButton("添加课程")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.setStyleSheet(secondary_button_style())
        add_button.clicked.connect(self.on_add_course_clicked)
        top_bar.addWidget(add_button)

        import_button = QPushButton("导入课表")
        import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        import_button.setStyleSheet(secondary_button_style())
        import_button.clicked.connect(self.on_import_schedule_clicked)
        top_bar.addWidget(import_button)

        week_label = QLabel("选择周次:")
        week_label.setStyleSheet(f"font-size: 13px; color: {TEXT}; background-color: transparent;")
        top_bar.addWidget(week_label)

        self.week_combo = QComboBox()
        for week in range(1, 17):
            self.week_combo.addItem(f"第 {week} 周", week)
        self.week_combo.setStyleSheet(
            f"""
            QComboBox {{
                padding: 5px 12px;
                border: 1px solid {BORDER};
                border-radius: 4px;
                background-color: #FFFFFF;
                color: {INK};
                min-width: 100px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                color: {INK};
                selection-background-color: {PKU_RED_LIGHT};
                selection-color: {INK};
            }}
            """
        )
        self.week_combo.currentIndexChanged.connect(self.on_week_changed)
        top_bar.addWidget(self.week_combo)

        self.week_type_badge = QLabel("")
        self.week_type_badge.setStyleSheet(self._badge_style(PKU_RED))
        top_bar.addWidget(self.week_type_badge)
        self.main_layout.addLayout(top_bar)
        self.week_combo.blockSignals(True)
        self.week_combo.setCurrentIndex(min(max(self.current_week, 1), 16) - 1)
        self.week_combo.blockSignals(False)
        self._update_week_badge()

    def _setup_grid_frame(self) -> None:
        self._day_header_badges: dict[int, QLabel] = {}  # col -> badge label
        days = ["时间", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for col, day_name in enumerate(days):
            if col == 0:
                header = QLabel(day_name)
                header.setAlignment(Qt.AlignmentFlag.AlignCenter)
                header.setStyleSheet(
                    f"background-color: {PKU_RED_DARK}; color: white; padding: 9px; "
                    "font-weight: 700; border-radius: 4px;"
                )
                self.grid_layout.addWidget(header, 0, col)
            else:
                container = QFrame()
                container.setStyleSheet(
                    f"QFrame {{ background-color: {PKU_RED}; border-radius: 4px; }}"
                    "QFrame QLabel { background-color: transparent; }"
                )
                vbox = QVBoxLayout(container)
                vbox.setContentsMargins(4, 5, 4, 4)
                vbox.setSpacing(2)
                day_label = QLabel(day_name)
                day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                day_label.setStyleSheet("color: white; font-weight: 700; font-size: 13px;")
                vbox.addWidget(day_label)
                badge = QLabel("")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setWordWrap(True)
                badge.setStyleSheet("color: #FFE0E0; font-size: 9px;")
                badge.setVisible(False)
                vbox.addWidget(badge)
                self._day_header_badges[col] = badge
                self.grid_layout.addWidget(container, 0, col)

        for row, (text, _start, _end) in enumerate(self.PERIODS, start=1):
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(
                f"background-color: #F6EEEE; color: {INK}; border: 1px solid {BORDER}; "
                "border-radius: 4px; font-size: 11px; font-weight: 700; min-height: 80px;"
            )
            self.grid_layout.addWidget(label, row, 0)

    def on_week_changed(self, index):
        self.current_week = self.week_combo.itemData(index) or index + 1
        self._update_week_badge()
        self.refresh_schedule()

    def _update_week_badge(self) -> None:
        if self.current_week % 2 == 0:
            self.week_type_badge.setText("双周")
            self.week_type_badge.setStyleSheet(self._badge_style(PKU_GOLD))
        else:
            self.week_type_badge.setText("单周")
            self.week_type_badge.setStyleSheet(self._badge_style(PKU_RED))

    def on_add_course_clicked(self):
        dialog = AddCourseDialog(self)
        if dialog.exec() == AddCourseDialog.Accepted:
            new_slot = dialog.get_course_data()
            new_slot["_local_id"] = self._next_local_slot_id
            self._next_local_slot_id += 1
            saved_to_facade = False
            if self.facade and hasattr(self.facade, "create_schedule_slot"):
                try:
                    slot_id = self.facade.create_schedule_slot(new_slot)
                    if slot_id is not None:
                        new_slot["id"] = slot_id
                    saved_to_facade = True
                except Exception as exc:
                    print(f"[GUI] facade schedule create failed: {exc}")
            if not saved_to_facade:
                self.custom_slots.append(new_slot)
            self.refresh_schedule()

    def on_import_schedule_clicked(self):
        dialog = ImportScheduleDialog(facade=self.facade, parent=self)
        if dialog.exec() == ImportScheduleDialog.DialogCode.Accepted:
            self.refresh_schedule()

    def set_gui_task_arrangements(self, arrangements) -> None:
        self.gui_task_arrangements = list(arrangements or [])
        self.refresh_schedule()

    def refresh_schedule(self):
        self._refresh_course_color_cache()
        self._clear_schedule_cards()
        for slot in self._load_schedule_slots():
            if not self._slot_occurs_this_week(slot):
                continue
            self._add_card_to_grid(slot, self._build_slot_card(slot))

        week_tasks = self._load_week_tasks()
        self._update_ddl_header_badges(week_tasks)

        if self.show_arrangements_checkbox.isChecked():
            for arrangement in self._load_task_arrangements():
                if not self._arrangement_occurs_this_week(arrangement):
                    continue
                self._add_card_to_grid(arrangement, self._build_task_arrangement_card(arrangement))

    def _update_ddl_header_badges(self, tasks) -> None:
        """Show DDL task info in day column headers (avoids grid cell conflicts)."""
        by_day: dict[int, list] = {}
        for task in tasks:
            due = get_field(task, "due_time")
            if not hasattr(due, "weekday"):
                continue
            weekday = due.weekday() + 1  # Mon=1 … Sun=7
            by_day.setdefault(weekday, []).append(task)

        for col, badge in self._day_header_badges.items():
            tasks_for_day = by_day.get(col, [])
            if not tasks_for_day:
                badge.setVisible(False)
                badge.setToolTip("")
            else:
                lines = []
                tooltip_lines = []
                for task in tasks_for_day:
                    due = get_field(task, "due_time")
                    time_str = due.strftime("%H:%M") if hasattr(due, "strftime") else ""
                    title = str(get_field(task, "title", "DDL"))
                    lines.append(f"⏰ {time_str}")
                    tooltip_lines.append(f"{time_str}  {title}")
                badge.setText("\n".join(lines))
                badge.setToolTip("\n".join(tooltip_lines))
                badge.setVisible(True)

    def _add_card_to_grid(self, slot, card) -> None:
        col = get_field(slot, "weekday", 1)
        row, row_span = self._slot_to_grid_position(slot)
        if isinstance(col, int) and 1 <= col <= 7 and row >= 1:
            self.grid_layout.addWidget(card, row, col, row_span, 1)

    def _load_schedule_slots(self):
        base_slots = []
        if self.facade and hasattr(self.facade, "list_schedule"):
            try:
                for weekday in range(1, 8):
                    base_slots.extend(self.facade.list_schedule(weekday, self.current_week))
            except Exception as exc:
                print(f"[GUI] error fetching schedule from Facade: {exc}")
        return base_slots + self.custom_slots

    def _load_task_arrangements(self):
        arrangements = list(self.gui_task_arrangements)
        if self.facade and hasattr(self.facade, "list_task_arrangements"):
            try:
                arrangements.extend(self.facade.list_task_arrangements(self.current_week))
            except TypeError:
                arrangements.extend(self.facade.list_task_arrangements())
            except Exception as exc:
                print(f"[GUI] failed to load task arrangements: {exc}")
        deduped = {}
        for item in arrangements:
            task_id = get_field(item, "task_id")
            key = task_id if task_id is not None else id(item)
            deduped[key] = item
        return list(deduped.values())

    def _load_week_tasks(self):
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return []
        try:
            tasks = self.facade.list_tasks(None)
        except Exception as exc:
            print(f"[GUI] failed to load tasks for DDL markers: {exc}")
            return []
        return [task for task in tasks if self._task_due_in_current_week(task)]

    def _refresh_course_color_cache(self) -> None:
        if not self.facade or not hasattr(self.facade, "list_courses"):
            return
        try:
            self._course_color_cache = {
                c.id: c.color for c in self.facade.list_courses() if c.id is not None
            }
        except Exception:
            pass

    def _slot_color(self, course_id) -> tuple[str, str]:
        """Return (bg_color, border_color) for a slot, using the course's stored color."""
        _FALLBACK_COLORS = [
            ("#F8EAEA", "#8C1515"),
            ("#FFF7E0", "#B8860B"),
            ("#F1F3E8", "#6B7D3A"),
            ("#F6EEEE", "#5F0F0F"),
            ("#EAF0F8", "#1A5276"),
            ("#F3EAF8", "#6C3483"),
        ]
        if course_id is not None and course_id in self._course_color_cache:
            hex_color = self._course_color_cache[course_id]
            return self._lighten(hex_color), hex_color
        if course_id is not None:
            return _FALLBACK_COLORS[course_id % len(_FALLBACK_COLORS)]
        return ("#F4EEEE", "#8C1515")

    @staticmethod
    def _lighten(hex_color: str) -> str:
        """Return a light tint of the given hex color for use as card background."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "#F4EEEE"
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = r + (255 - r) * 85 // 100
        g = g + (255 - g) * 85 // 100
        b = b + (255 - b) * 85 // 100
        return f"#{r:02X}{g:02X}{b:02X}"

    def _clear_schedule_cards(self):
        for index in range(self.grid_layout.count() - 1, -1, -1):
            item = self.grid_layout.itemAt(index)
            row, col, _row_span, _col_span = self.grid_layout.getItemPosition(index)
            if row > 0 and col > 0:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def _slot_occurs_this_week(self, slot):
        occurs_in_week = getattr(slot, "occurs_in_week", None)
        if callable(occurs_in_week):
            return occurs_in_week(self.current_week)
        start_week = int(get_field(slot, "start_week", 1) or 1)
        end_week = int(get_field(slot, "end_week", 16) or 16)
        week_type = get_field(slot, "week_type", "all")
        if not (start_week <= self.current_week <= end_week):
            return False
        if week_type == "odd" and self.current_week % 2 == 0:
            return False
        if week_type == "even" and self.current_week % 2 != 0:
            return False
        return True

    def _arrangement_occurs_this_week(self, arrangement) -> bool:
        week = get_field(arrangement, "week")
        return week in (None, self.current_week)

    def _slot_to_grid_position(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))
        start_row = None
        end_row = None
        for index, (_label, period_start, period_end) in enumerate(self.PERIODS, start=1):
            if start_time < period_end and end_time > period_start:
                start_row = index if start_row is None else start_row
                end_row = index
        if start_row is None:
            return 1, 1
        return start_row, max(1, (end_row or start_row) - start_row + 1)

    @staticmethod
    def _coerce_time(value):
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            text = value.strip()
            if len(text.split(":")[0]) == 1:
                text = "0" + text
            return time.fromisoformat(text[:5])
        if hasattr(value, "strftime"):
            return time.fromisoformat(value.strftime("%H:%M"))
        return time(8, 0)

    def _build_slot_card(self, slot):
        course_id = get_field(slot, "course_id")
        card_color, border_color = self._slot_color(course_id)
        card = QFrame()
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, s=slot, w=card: self._show_slot_menu(s, w, pos))
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {card_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QFrame QLabel {{
                background-color: transparent;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        if not self._is_exact_period_slot(slot):
            time_label = QLabel(self._slot_time_text(slot))
            time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_label.setStyleSheet(f"color: {PKU_RED_DARK}; font-size: 9px; font-weight: 700;")
            layout.addWidget(time_label)

        title = QLabel(str(get_field(slot, "title", "未命名课程")))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-weight: 700; color: {INK}; font-size: 11px;")
        location = QLabel(str(get_field(slot, "location", "") or ""))
        location.setWordWrap(True)
        location.setAlignment(Qt.AlignmentFlag.AlignCenter)
        location.setStyleSheet(f"color: {TEXT}; font-size: 9px;")
        layout.addWidget(title)
        if location.text():
            layout.addWidget(location)
        return card

    def _build_task_arrangement_card(self, arrangement):
        card = QFrame()
        card.setObjectName("taskArrangementCard")
        card.setStyleSheet(
            f"""
            QFrame#taskArrangementCard {{
                background-color: #FFF8E6;
                border: 1px dashed {PKU_GOLD};
                border-radius: 6px;
            }}
            QFrame#taskArrangementCard QLabel {{
                background-color: transparent;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        time_label = QLabel(self._slot_time_text(arrangement))
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet(f"color: #8A5A00; font-size: 9px; font-weight: 700;")
        title = QLabel(str(get_field(arrangement, "task_title", get_field(arrangement, "title", "DDL 任务"))))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {INK}; font-size: 11px; font-weight: 700;")
        layout.addWidget(time_label)
        layout.addWidget(title)
        return card

    def _build_ddl_marker(self, task):
        due_time = get_field(task, "due_time")
        if not hasattr(due_time, "date") or not hasattr(due_time, "time"):
            return None
        weekday = due_time.weekday() + 1
        if not 1 <= weekday <= 7:
            return None
        row = self._time_to_grid_row(due_time.time())
        return row, weekday

    def _time_to_grid_row(self, t: time) -> int:
        """Return the 1-based grid row for a clock time, snapping to the nearest period."""
        for index, (_label, period_start, period_end) in enumerate(self.PERIODS, start=1):
            if period_start <= t <= period_end:
                return index
        # Between periods or outside: find the last period whose start <= t
        best = 1
        for index, (_label, period_start, _period_end) in enumerate(self.PERIODS, start=1):
            if period_start <= t:
                best = index
        return best

    def _is_exact_period_slot(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))
        return start_time in {p[1] for p in self.PERIODS} and end_time in {p[2] for p in self.PERIODS}

    def _slot_time_text(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))
        return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"

    def _show_slot_menu(self, slot, widget, pos):
        menu = QMenu(widget)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #FFFFFF;
                color: {INK};
                border: 1px solid {BORDER};
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {INK};
                padding: 6px 22px 6px 12px;
            }}
            QMenu::item:selected {{
                background-color: {PKU_RED_LIGHT};
                color: {PKU_RED};
            }}
            """
        )
        edit_action = QAction("编辑课程", widget)
        delete_action = QAction("删除课程", widget)
        edit_action.triggered.connect(lambda: self._edit_slot(slot))
        delete_action.triggered.connect(lambda: self._delete_slot(slot))
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.exec(widget.mapToGlobal(pos))

    def _edit_slot(self, slot):
        dialog = AddCourseDialog(self, course_data=slot)
        if dialog.exec() != AddCourseDialog.DialogCode.Accepted:
            return
        updated = dialog.get_course_data()
        if self._is_custom_slot(slot):
            self._replace_custom_slot(slot, updated)
        elif self._try_update_backend_slot(slot, updated):
            pass
        else:
            QMessageBox.information(self, "暂不可编辑", "该课程来自后端，当前 Facade 还没有暴露课表更新接口。")
            return
        self.refresh_schedule()

    def _delete_slot(self, slot):
        title = get_field(slot, "title", "该课程")
        reply = QMessageBox.question(self, "删除课程", f"确定删除“{title}”吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._is_custom_slot(slot):
            self._remove_custom_slot(slot)
        elif self._try_delete_backend_slot(slot):
            pass
        else:
            QMessageBox.information(self, "暂不可删除", "该课程来自后端，当前 Facade 还没有暴露课表删除接口。")
            return
        self.refresh_schedule()

    def _is_custom_slot(self, slot):
        return get_field(slot, "_local_id") is not None

    def _replace_custom_slot(self, old_slot, new_slot):
        old_id = get_field(old_slot, "_local_id")
        for index, slot in enumerate(self.custom_slots):
            if get_field(slot, "_local_id") == old_id:
                new_slot["_local_id"] = old_id
                self.custom_slots[index] = new_slot
                return

    def _remove_custom_slot(self, old_slot):
        old_id = get_field(old_slot, "_local_id")
        self.custom_slots = [slot for slot in self.custom_slots if get_field(slot, "_local_id") != old_id]

    def _try_update_backend_slot(self, old_slot, updated):
        if not self.facade or not hasattr(self.facade, "update_schedule_slot"):
            return False
        slot_id = get_field(old_slot, "id")
        if slot_id is None:
            return False
        self.facade.update_schedule_slot(slot_id, updated)
        return True

    def _try_delete_backend_slot(self, slot):
        if not self.facade or not hasattr(self.facade, "delete_schedule_slot"):
            return False
        slot_id = get_field(slot, "id")
        if slot_id is None:
            return False
        self.facade.delete_schedule_slot(slot_id)
        return True

    def _task_due_in_current_week(self, task) -> bool:
        due_time = get_field(task, "due_time")
        if not hasattr(due_time, "date"):
            return False
        days = (due_time.date() - SEMESTER_START).days
        if days < 0:
            return False
        return days // 7 + 1 == self.current_week

    @staticmethod
    def _current_semester_week() -> int:
        days = (date.today() - SEMESTER_START).days
        if days < 0:
            return 1
        return max(1, min(16, days // 7 + 1))

    @staticmethod
    def _badge_style(color):
        return f"background-color: {color}; color: #FFFFFF; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-weight: 700; min-width: 44px;"


if __name__ == "__main__":
    from app.main import build_facade

    app = QApplication(sys.argv)
    window = ScheduleWidget(facade=build_facade())
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec())
