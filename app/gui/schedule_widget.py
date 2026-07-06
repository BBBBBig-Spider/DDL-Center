from __future__ import annotations

import sys
from datetime import date, datetime, time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
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
from app.gui.theme import BORDER, INK, ACCENT, PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, TEXT, secondary_button_style
from app.gui._helpers import get_field


class ScheduleWidget(QWidget):
    DEFAULT_DISPLAY_WEEKS = 20
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
        self._reload_semester_settings()
        self.current_week = self._current_semester_week()
        self.custom_slots = []
        self.gui_task_arrangements = []
        self._next_local_slot_id = 1
        self._course_color_cache: dict[int, str] = {}  # course_id -> hex color
        self._now_line: QFrame | None = None
        self._now_label: QLabel | None = None
        self._init_ui()
        self.refresh_schedule()
        # Refresh the "current time" indicator every 5 minutes. Stored as an
        # attribute so tests / teardown can inspect it.
        self._now_line_timer = QTimer(self)
        self._now_line_timer.setInterval(5 * 60 * 1000)
        self._now_line_timer.timeout.connect(self._update_now_line)
        self._now_line_timer.start()

    def _reload_semester_settings(self) -> None:
        from app.config import SEMESTER_START
        self._semester_start = SEMESTER_START
        self._total_weeks = self.DEFAULT_DISPLAY_WEEKS
        if self.facade and hasattr(self.facade, "get_semester_settings"):
            try:
                s = self.facade.get_semester_settings()
                stored = s.get("start")
                if stored:
                    self._semester_start = date.fromisoformat(stored[:10])
                self._total_weeks = max(1, min(30, int(s.get("total_weeks") or self.DEFAULT_DISPLAY_WEEKS)))
            except Exception:
                pass

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

        self._ddl_overlay = QWidget(grid_container)
        self._ddl_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._ddl_overlay.setStyleSheet("background: transparent;")
        self._ddl_overlay.raise_()
        self._grid_container = grid_container
        grid_container.installEventFilter(self)

        scroll_area.setWidget(grid_container)
        self.main_layout.addWidget(scroll_area, stretch=1)

    def eventFilter(self, watched, event):
        if watched is getattr(self, "_grid_container", None) and event.type() == event.Type.Resize:
            self._ddl_overlay.setGeometry(0, 0, watched.width(), watched.height())
            self._schedule_ddl_redraw()
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        # The overlay needs an initial geometry sync the first time the page
        # becomes visible — eventFilter only fires on actual resize events.
        self._schedule_ddl_redraw()

    def _schedule_ddl_redraw(self) -> None:
        """Defer the redraw to the next event-loop tick so cellRect is valid.

        Calling _redraw_ddl_lines synchronously after refresh_schedule (which
        adds/removes widgets in the grid) gives empty 0x0 rects from
        grid_layout.cellRect — the layout hasn't actually run yet.
        QTimer.singleShot(0, ...) lets Qt finish the layout pass first.
        """
        QTimer.singleShot(0, self._redraw_ddl_lines)

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
                background-color: {PRIMARY};
                border: 1px solid {PRIMARY};
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

        semester_button = QPushButton("⚙️ 学期设置")
        semester_button.setCursor(Qt.CursorShape.PointingHandCursor)
        semester_button.setStyleSheet(secondary_button_style())
        semester_button.setToolTip("修改学期开始日期与总周数")
        semester_button.clicked.connect(self.on_semester_settings_clicked)
        top_bar.addWidget(semester_button)

        refresh_button = QPushButton("🔄 刷新")
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.setStyleSheet(secondary_button_style())
        refresh_button.setToolTip("重新加载本周课程、考试和 DDL 红线")
        refresh_button.clicked.connect(self.refresh_schedule)
        top_bar.addWidget(refresh_button)

        week_label = QLabel("选择周次:")
        week_label.setStyleSheet(f"font-size: 13px; color: {TEXT}; background-color: transparent;")
        top_bar.addWidget(week_label)

        self.week_combo = QComboBox()
        for week in range(1, self._total_weeks + 1):
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
                selection-background-color: {PRIMARY_LIGHT};
                selection-color: {INK};
            }}
            """
        )
        self.week_combo.currentIndexChanged.connect(self.on_week_changed)

        nav_button_style = f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}
            QPushButton:disabled {{ background-color: #D0D0D0; color: #888; }}
        """
        self.prev_week_button = QPushButton("◀")
        self.prev_week_button.setFixedSize(32, 32)
        self.prev_week_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_week_button.setToolTip("上一周 (Ctrl+Left)")
        self.prev_week_button.setStyleSheet(nav_button_style)
        self.prev_week_button.clicked.connect(
            lambda: self.week_combo.setCurrentIndex(self.week_combo.currentIndex() - 1)
        )
        top_bar.addWidget(self.prev_week_button)

        top_bar.addWidget(self.week_combo)

        self.next_week_button = QPushButton("▶")
        self.next_week_button.setFixedSize(32, 32)
        self.next_week_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_week_button.setToolTip("下一周 (Ctrl+Right)")
        self.next_week_button.setStyleSheet(nav_button_style)
        self.next_week_button.clicked.connect(
            lambda: self.week_combo.setCurrentIndex(self.week_combo.currentIndex() + 1)
        )
        top_bar.addWidget(self.next_week_button)

        self.week_type_badge = QLabel("")
        self.week_type_badge.setStyleSheet(self._badge_style(PRIMARY))
        top_bar.addWidget(self.week_type_badge)
        self.main_layout.addLayout(top_bar)
        self.week_combo.blockSignals(True)
        self.week_combo.setCurrentIndex(min(max(self.current_week, 1), self.week_combo.count()) - 1)
        self.week_combo.blockSignals(False)
        self._update_week_badge()
        self._update_week_nav_buttons()

        prev_shortcut = QShortcut(QKeySequence("Ctrl+Left"), self)
        prev_shortcut.activated.connect(
            lambda: self.prev_week_button.click() if self.prev_week_button.isEnabled() else None
        )
        next_shortcut = QShortcut(QKeySequence("Ctrl+Right"), self)
        next_shortcut.activated.connect(
            lambda: self.next_week_button.click() if self.next_week_button.isEnabled() else None
        )

    def _setup_grid_frame(self) -> None:
        self._day_header_badges: dict[int, QLabel] = {}  # col -> badge label
        days = ["时间", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for col, day_name in enumerate(days):
            if col == 0:
                header = QLabel(day_name)
                header.setAlignment(Qt.AlignmentFlag.AlignCenter)
                header.setStyleSheet(
                    f"background-color: {PRIMARY_DARK}; color: white; padding: 9px; "
                    "font-weight: 700; border-radius: 4px;"
                )
                self.grid_layout.addWidget(header, 0, col)
            else:
                container = QFrame()
                container.setStyleSheet(
                    f"QFrame {{ background-color: {PRIMARY}; border-radius: 4px; }}"
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
        self._update_week_nav_buttons()

    def _update_week_nav_buttons(self) -> None:
        idx = self.week_combo.currentIndex()
        last = self.week_combo.count() - 1
        self.prev_week_button.setEnabled(idx > 0)
        self.next_week_button.setEnabled(idx < last)

    def _update_week_badge(self) -> None:
        if self.current_week % 2 == 0:
            self.week_type_badge.setText("双周")
            self.week_type_badge.setStyleSheet(self._badge_style(ACCENT))
        else:
            self.week_type_badge.setText("单周")
            self.week_type_badge.setStyleSheet(self._badge_style(PRIMARY))

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

    def on_semester_settings_clicked(self):
        from app.gui.semester_settings_dialog import SemesterSettingsDialog
        dialog = SemesterSettingsDialog(self.facade, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload_semester_settings()
            # 重建 week_combo 下拉项
            self.week_combo.blockSignals(True)
            self.week_combo.clear()
            for week in range(1, self._total_weeks + 1):
                self.week_combo.addItem(f"第 {week} 周", week)
            self.current_week = min(self.current_week, self._total_weeks)
            idx = max(0, self.current_week - 1)
            self.week_combo.setCurrentIndex(idx)
            self.week_combo.blockSignals(False)
            self._update_week_nav_buttons()
            self.refresh_schedule()

    def set_gui_task_arrangements(self, arrangements) -> None:
        self.gui_task_arrangements = list(arrangements or [])
        self.refresh_schedule()

    def refresh_schedule(self):
        self._refresh_course_color_cache()
        self._clear_schedule_cards()

        is_exam_week = self._is_current_exam_week()
        if is_exam_week:
            self.week_type_badge.setText("考试周")
            self.week_type_badge.setStyleSheet(self._badge_style(ACCENT))
        else:
            for slot in self._load_schedule_slots():
                if not self._slot_occurs_this_week(slot):
                    continue
                self._add_card_to_grid(slot, self._build_slot_card(slot))

        for exam in self._load_week_exams():
            self._add_card_to_grid(self._exam_to_grid_item(exam), self._build_exam_card(exam))

        week_tasks = self._load_week_tasks()
        self._update_ddl_header_badges(week_tasks)

        if self.show_arrangements_checkbox.isChecked() and not is_exam_week:
            for arrangement in self._load_task_arrangements():
                if not self._arrangement_occurs_this_week(arrangement):
                    continue
                self._add_card_to_grid(arrangement, self._build_task_arrangement_card(arrangement))

        self._schedule_ddl_redraw()

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

    def _load_week_exams(self):
        if not self.facade or not hasattr(self.facade, "list_exams"):
            return []
        week_start, week_end = self._current_week_date_range()
        try:
            exams = self.facade.list_exams()
        except Exception as exc:
            print(f"[GUI] failed to load exams for schedule: {exc}")
            return []
        result = []
        for exam in exams:
            start_time = get_field(exam, "start_time")
            if not hasattr(start_time, "date"):
                continue
            if week_start <= start_time.date() <= week_end:
                result.append(exam)
        return sorted(result, key=lambda exam: get_field(exam, "start_time"))

    def _is_current_exam_week(self) -> bool:
        if not self.facade or not hasattr(self.facade, "get_exam_week_range"):
            return False
        try:
            start_raw, end_raw = self.facade.get_exam_week_range()
        except Exception:
            return False
        start_date = self._coerce_date(start_raw)
        end_date = self._coerce_date(end_raw)
        if start_date is None or end_date is None:
            return False
        week_start, week_end = self._current_week_date_range()
        return week_start <= end_date and start_date <= week_end

    def _current_week_date_range(self) -> tuple[date, date]:
        from datetime import timedelta
        start = self._semester_start + timedelta(days=(self.current_week - 1) * 7)
        return start, start + timedelta(days=6)

    @staticmethod
    def _coerce_date(value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and value.strip():
            try:
                return date.fromisoformat(value.strip()[:10])
            except ValueError:
                return None
        return None

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
        return [
            task for task in tasks
            if str(get_field(task, "status", "todo") or "todo").lower() != "done"
            and self._task_due_in_current_week(task)
        ]

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
            time_label.setStyleSheet(f"color: {PRIMARY_DARK}; font-size: 9px; font-weight: 700;")
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

    def _exam_to_grid_item(self, exam) -> dict:
        start_dt = get_field(exam, "start_time")
        end_dt = get_field(exam, "end_time")
        start_time = start_dt.time() if hasattr(start_dt, "time") else time(9, 0)
        end_time = end_dt.time() if hasattr(end_dt, "time") else time(11, 0)
        weekday = start_dt.weekday() + 1 if hasattr(start_dt, "weekday") else 1
        return {
            "weekday": weekday,
            "start_time": start_time,
            "end_time": end_time,
            "title": get_field(exam, "name", "考试"),
        }

    def _build_exam_card(self, exam):
        card = QFrame()
        card.setObjectName("examCard")
        card.setStyleSheet(
            f"""
            QFrame#examCard {{
                background-color: #FFF8E6;
                border: 2px solid {ACCENT};
                border-radius: 6px;
            }}
            QFrame#examCard QLabel {{
                background-color: transparent;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        start_dt = get_field(exam, "start_time")
        end_dt = get_field(exam, "end_time")
        if hasattr(start_dt, "strftime") and hasattr(end_dt, "strftime"):
            time_text = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
        else:
            time_text = "考试"

        badge = QLabel("考试")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"color: #8A5A00; font-size: 9px; font-weight: 700;")
        time_label = QLabel(time_text)
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet(f"color: #8A5A00; font-size: 9px; font-weight: 700;")
        title = QLabel(str(get_field(exam, "name", "考试")))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {INK}; font-size: 11px; font-weight: 700;")
        location_text = str(get_field(exam, "location", "") or "")
        seat_text = str(get_field(exam, "seat", "") or "")
        detail = " ".join(part for part in (location_text, seat_text) if part)
        detail_label = QLabel(detail)
        detail_label.setWordWrap(True)
        detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_label.setStyleSheet(f"color: {TEXT}; font-size: 9px;")

        layout.addWidget(badge)
        layout.addWidget(time_label)
        layout.addWidget(title)
        if detail:
            layout.addWidget(detail_label)
        return card

    def _build_task_arrangement_card(self, arrangement):
        card = QFrame()
        card.setObjectName("taskArrangementCard")
        card.setStyleSheet(
            f"""
            QFrame#taskArrangementCard {{
                background-color: #FFF8E6;
                border: 1px dashed {ACCENT};
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

    def _time_to_pixel_y(self, t: time) -> int | None:
        """Map a clock time to a pixel y coordinate inside grid_container.

        Out-of-range times are clipped to the grid edges:
          * t earlier than the first period start -> top of row 1
          * t later than the last period end       -> bottom of the last row
        Linear interpolation within a period; for time falling in the gap
        between two periods, interpolates across the gap.
        """
        if t < self.PERIODS[0][1]:
            top_cell = self.grid_layout.cellRect(1, 1)
            if top_cell.height() <= 0:
                return None
            return top_cell.top()
        if t > self.PERIODS[-1][2]:
            bottom_cell = self.grid_layout.cellRect(len(self.PERIODS), 1)
            if bottom_cell.height() <= 0:
                return None
            return bottom_cell.bottom()

        def secs(x: time) -> int:
            return x.hour * 3600 + x.minute * 60 + x.second

        t_secs = secs(t)
        for index, (_label, period_start, period_end) in enumerate(self.PERIODS):
            if period_start <= t <= period_end:
                cell = self.grid_layout.cellRect(index + 1, 1)
                if cell.height() <= 0:
                    return None
                start_secs = secs(period_start)
                end_secs = secs(period_end)
                span = end_secs - start_secs
                if span <= 0:
                    return cell.top()
                ratio = (t_secs - start_secs) / span
                return int(cell.top() + ratio * cell.height())
            # Check gap between this period and the next
            if index + 1 < len(self.PERIODS):
                next_start = self.PERIODS[index + 1][1]
                if period_end < t < next_start:
                    cell_a = self.grid_layout.cellRect(index + 1, 1)
                    cell_b = self.grid_layout.cellRect(index + 2, 1)
                    gap_start_y = cell_a.bottom()
                    gap_end_y = cell_b.top()
                    gap_height = gap_end_y - gap_start_y
                    end_secs = secs(period_end)
                    next_start_secs = secs(next_start)
                    span = next_start_secs - end_secs
                    if span <= 0:
                        return gap_start_y
                    ratio = (t_secs - end_secs) / span
                    return int(gap_start_y + ratio * gap_height)
        return None

    def _redraw_ddl_lines(self) -> None:
        # Wipe DDL markers from a previous render but keep the "current time"
        # indicator widgets intact — they have a longer lifecycle and are
        # repositioned by _update_now_line, not recreated each redraw.
        _NOW_INDICATOR_NAMES = {"scheduleNowLine", "scheduleNowLabel"}
        for child in self._ddl_overlay.findChildren(QWidget):
            if child.objectName() in _NOW_INDICATOR_NAMES:
                continue
            child.setParent(None)
            child.deleteLater()

        # Make sure overlay covers the whole grid container; if eventFilter
        # never fired (e.g. first-show before any resize), it would be 0x0.
        if hasattr(self, "_grid_container"):
            self._ddl_overlay.setGeometry(
                0, 0, self._grid_container.width(), self._grid_container.height()
            )
            # Keep overlay above any course cards re-added by refresh_schedule.
            self._ddl_overlay.raise_()

        week_tasks = self._load_week_tasks()
        print(f"[DDL] week={self.current_week}, tasks_in_week={len(week_tasks)}")

        # Force a layout pass BEFORE we start querying cellRect — the now-line
        # path also depends on this. Without it, _time_to_pixel_y returns None
        # for every clamp branch and the now-line never shows up.
        self.grid_layout.activate()
        drawn = 0

        for task in week_tasks:
            due_time = get_field(task, "due_time")
            if not hasattr(due_time, "weekday"):
                continue
            weekday_col = due_time.weekday() + 1
            if not 1 <= weekday_col <= 7:
                continue
            t = due_time.time()
            y = self._time_to_pixel_y(t)
            if y is None:
                print(f"[DDL] skip {get_field(task, 'title', '')}: cellRect not ready for time {t}")
                continue
            title_str = get_field(task, "title", "")
            if t < self.PERIODS[0][1]:
                print(f"[DDL] {title_str}: clipped to top (time {t} < first period)")
            elif t > self.PERIODS[-1][2]:
                print(f"[DDL] {title_str}: clipped to bottom (time {t} > last period)")
            col_rect = self.grid_layout.cellRect(1, weekday_col)
            if col_rect.width() <= 0:
                print(
                    f"[DDL] skip {title_str}: cellRect not ready "
                    f"(col={weekday_col}, rect={col_rect})"
                )
                continue
            line = QFrame(self._ddl_overlay)
            line.setStyleSheet(f"background-color: {PRIMARY}; border: none;")
            line.setGeometry(col_rect.x(), y - 1, col_rect.width(), 2)
            label_text = f"DDL {due_time.strftime('%H:%M')} · {title_str}"
            label = QLabel(label_text, self._ddl_overlay)
            label.setStyleSheet(
                f"background-color: {PRIMARY}; color: white; padding: 1px 4px; "
                "border-radius: 2px; font-size: 9px; font-weight: 700;"
            )
            label.adjustSize()
            label_x = col_rect.x() + 2
            label_y = y - label.height() - 1
            overlay_h = self._ddl_overlay.height()
            if label_y < 0:
                # Line is at the very top — drop the label below the line.
                label_y = y + 2
            elif y + 2 + label.height() > overlay_h:
                # Line is at the very bottom — keep the label above (default
                # placement already does this, but be explicit so future code
                # changes don't accidentally push it off-screen).
                label_y = max(0, y - label.height() - 1)
            label.move(label_x, label_y)
            line.show()
            label.show()
            drawn += 1
        print(f"[DDL] drawn {drawn} marker(s)")
        # Re-position the "current time" indicator after the DDL pass so it
        # sits on top of any course/DDL widgets that were just inserted.
        self._update_now_line()

    # ------------------------------------------------------------------
    # "Current time" indicator
    # ------------------------------------------------------------------

    NOW_LINE_DEFAULT_COLOR = "#3B82F6"
    NOW_LINE_SETTING_KEY = "now_line_color"

    def _get_now_line_color(self) -> str:
        repo = getattr(self.facade, "setting_repository", None)
        if repo is not None:
            try:
                stored = repo.get(self.NOW_LINE_SETTING_KEY, self.NOW_LINE_DEFAULT_COLOR)
            except Exception:
                stored = self.NOW_LINE_DEFAULT_COLOR
            if isinstance(stored, str) and stored.startswith("#"):
                return stored
        return self.NOW_LINE_DEFAULT_COLOR

    def refresh_now_line(self, *_args) -> None:
        """Public hook: called by MainWindow when GeneralSettingsPage
        broadcasts the user's chosen color. The actual color is read from
        ``setting_repository`` inside ``_update_now_line`` — this method
        is just a "settings changed, please re-render now" signal so the
        change is visible without waiting for the 5-min timer.

        The previous name (``set_now_line_color(hex_color)``) lied about
        its contract: the ``hex_color`` parameter was validated and then
        thrown away. See REVIEW.md severe #3. ``*_args`` swallows the
        signal payload (a hex string) so this still slots into existing
        ``Signal[str].connect(...)`` wiring.
        """
        self._update_now_line()

    def _update_now_line(self) -> None:
        """Render or hide the horizontal line showing where 'now' is.

        Visible only when (a) the user is looking at the real current week and
        (b) the current clock time falls inside the displayed PERIODS window.
        Spans only the "today" column, sits on top of the DDL overlay.
        """
        # No overlay yet → page hasn't fully laid out; bail.
        overlay = getattr(self, "_ddl_overlay", None)
        if overlay is None:
            return

        now = datetime.now()
        in_current_week = self.current_week == self._current_semester_week()
        # weekday(): Mon=0..Sun=6 → grid col 1..7
        today_col = now.weekday() + 1

        # NOTE: do NOT bail out when ``now.time()`` is outside PERIODS — the
        # line should still render, clamped to the top/bottom edge of the
        # grid, exactly like the DDL red lines do for late-night deadlines
        # (e.g. 23:59 falls past the last period at 21:30 but we still want
        # to see it). ``_time_to_pixel_y`` already handles this via its
        # head/tail clamps; we only hide the indicator when the user is
        # browsing a different week.
        if not in_current_week:
            if self._now_line is not None:
                self._now_line.hide()
            if self._now_label is not None:
                self._now_label.hide()
            return

        col_rect = self.grid_layout.cellRect(1, today_col)
        y = self._time_to_pixel_y(now.time())
        if y is None or col_rect.width() <= 0:
            # cellRect not ready yet — force a layout pass and try once more.
            # This matters when we're called from the 5-minute timer (not via
            # _redraw_ddl_lines) and the user hasn't resized the window since
            # the page was first opened.
            self.grid_layout.activate()
            col_rect = self.grid_layout.cellRect(1, today_col)
            y = self._time_to_pixel_y(now.time())
            if y is None or col_rect.width() <= 0:
                return

        color = self._get_now_line_color()

        # Lazily create the two widgets (kept alive across redraws).
        if self._now_line is None:
            self._now_line = QFrame(overlay)
            self._now_line.setObjectName("scheduleNowLine")
        if self._now_label is None:
            self._now_label = QLabel(overlay)
            self._now_label.setObjectName("scheduleNowLabel")

        self._now_line.setStyleSheet(f"background-color: {color}; border: none;")
        self._now_line.setGeometry(col_rect.x(), y - 1, col_rect.width(), 2)

        self._now_label.setText(f"现在 {now.strftime('%H:%M')}")
        self._now_label.setStyleSheet(
            f"background-color: {color}; color: white; padding: 1px 4px; "
            "border-radius: 2px; font-size: 9px; font-weight: 700;"
        )
        self._now_label.adjustSize()
        label_x = col_rect.x() + col_rect.width() - self._now_label.width() - 2
        label_y = y - self._now_label.height() - 1
        if label_y < 0:
            label_y = y + 2
        self._now_label.move(label_x, label_y)

        self._now_line.raise_()
        self._now_label.raise_()
        self._now_line.show()
        self._now_label.show()

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
                background-color: {PRIMARY_LIGHT};
                color: {PRIMARY};
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
        days = (due_time.date() - self._semester_start).days
        if days < 0:
            return False
        return days // 7 + 1 == self.current_week

    def _current_semester_week(self) -> int:
        # Delegate to the shared helper so a user's "semester start" change
        # is reflected consistently across managers and widgets. The widget
        # already resolves its own ``_semester_start`` and ``_total_weeks``
        # from the facade in ``_reload_semester_settings``, so we pass them
        # in as fallbacks rather than re-reading the repo here.
        from app.utils.semester import compute_current_week
        repo = getattr(self.facade, "setting_repository", None) if self.facade else None
        return compute_current_week(
            repo,
            fallback_start=self._semester_start,
            fallback_upper=self._total_weeks,
        )

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
