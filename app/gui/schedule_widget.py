import sys
from datetime import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QMessageBox, QScrollArea, QVBoxLayout, QWidget, QPushButton

from app.gui.add_schedule_dialog import AddCourseDialog


def get_field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class ScheduleWidget(QWidget):
    """Weekly schedule view backed by AppFacade.list_schedule(weekday, week)."""

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
        self.current_week = 1
        self.custom_slots = []
        self._next_local_slot_id = 1

        self.init_ui()
        self.refresh_schedule()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.setup_top_bar()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(8)

        self.setup_schedule_grid_frame()

        scroll_area.setWidget(grid_container)
        self.main_layout.addWidget(scroll_area)

    def setup_top_bar(self):
        top_bar = QHBoxLayout()

        title_label = QLabel("课程表")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E50;")
        top_bar.addWidget(title_label)
        top_bar.addStretch()

        self.btn_add_course = QPushButton("➕ 添加课程")
        self.btn_add_course.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF; color: #1890FF; border: 1px solid #1890FF;
                border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E6F7FF; color: #40A9FF; border-color: #40A9FF;
            }
            QPushButton:pressed {
                background-color: #BAE7FF;
            }
            """
        )
        self.btn_add_course.clicked.connect(self.on_add_course_clicked)
        top_bar.addWidget(self.btn_add_course)

        week_label = QLabel("选择周次:")
        week_label.setStyleSheet("font-size: 14px; color: #555;")
        top_bar.addWidget(week_label)

        self.week_combo = QComboBox()
        for week in range(1, 17):
            self.week_combo.addItem(f"第 {week} 周", week)
        self.week_combo.setStyleSheet(
            """
            QComboBox {
                padding: 5px 15px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #262626;
                font-size: 14px;
                min-width: 100px;
                selection-background-color: #E6F7FF;
                selection-color: #262626;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #262626;
                selection-background-color: #E6F7FF;
                selection-color: #262626;
                outline: 0;
            }
            """
        )
        self.week_combo.currentIndexChanged.connect(self.on_week_changed)
        top_bar.addWidget(self.week_combo)

        self.week_type_badge = QLabel("(单周)")
        self.week_type_badge.setStyleSheet(self._badge_style("#3498DB"))
        top_bar.addWidget(self.week_type_badge)

        self.main_layout.addLayout(top_bar)

    def on_add_course_clicked(self):
        dialog = AddCourseDialog(self)
        if dialog.exec() == AddCourseDialog.Accepted:
            new_slot = dialog.get_course_data()
            new_slot["_local_id"] = self._next_local_slot_id
            self._next_local_slot_id += 1
            
            # 1. 严格遵守门面隔离原则：如果后端未来实现了课程写入方法，在此对接
            if self.facade and hasattr(self.facade, "create_schedule_slot"):
                try:
                    self.facade.create_schedule_slot(new_slot)
                except Exception as e:
                    print(f"Facade writing failed: {e}")
            
            # 2. 安全同步降级防爆盾：将其推入缓存，确保前端能100%同步渲染出来
            self.custom_slots.append(new_slot)
            
            # 3. 立即重绘视图
            self.refresh_schedule()

    def setup_schedule_grid_frame(self):
        days = ["时间", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        for col, day_name in enumerate(days):
            header = QLabel(day_name)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#34495E" if col == 0 else "#2C3E50"
            header.setStyleSheet(
                f"background-color: {color}; color: white; padding: 10px; "
                "font-weight: bold; border-radius: 4px;"
            )
            self.grid_layout.addWidget(header, 0, col)

        for row, (time_text, _start, _end) in enumerate(self.PERIODS, start=1):
            time_label = QLabel(time_text)
            time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_label.setStyleSheet(
                """
                background-color: #ECF0F1; color: #34495E;
                border: 1px solid #BDC3C7; border-radius: 4px;
                font-size: 11px; font-weight: bold; min-height: 80px;
                """
            )
            self.grid_layout.addWidget(time_label, row, 0)

    def on_week_changed(self, index):
        self.current_week = self.week_combo.itemData(index) or index + 1
        if self.current_week % 2 == 0:
            self.week_type_badge.setText("(双周)")
            self.week_type_badge.setStyleSheet(self._badge_style("#2ECC71"))
        else:
            self.week_type_badge.setText("(单周)")
            self.week_type_badge.setStyleSheet(self._badge_style("#3498DB"))

        self.refresh_schedule()

    def refresh_schedule(self):
        self._clear_schedule_cards()

        for slot in self._load_schedule_slots():
            if not self._slot_occurs_this_week(slot):
                continue

            col = get_field(slot, "weekday", 1)
            row, row_span = self._slot_to_grid_position(slot)
            if not isinstance(col, int) or col < 1 or col > 7 or row < 1 or row > len(self.PERIODS):
                continue

            self.grid_layout.addWidget(self._build_slot_card(slot), row, col, row_span, 1)

    def _load_schedule_slots(self):
        base_slots = []
        if self.facade and hasattr(self.facade, "list_schedule"):
            try:
                for weekday in range(1, 8):
                    base_slots.extend(self.facade.list_schedule(weekday, self.current_week))
            except NotImplementedError:
                base_slots = self._fallback_slots()
            except Exception as exc:
                print(f"Error fetching schedule from Facade: {exc}")
                base_slots = self._fallback_slots()
        else:
            base_slots = self._fallback_slots()

        # ===== ⚠️ 改动位置 5：在返回课程数据源时，将前端手动添加的自定义数据源合并进去同步返回 =====
        return base_slots + self.custom_slots

    def _clear_schedule_cards(self):
        for index in range(self.grid_layout.count() - 1, -1, -1):
            item = self.grid_layout.itemAt(index)
            row, col, _row_span, _col_span = self.grid_layout.getItemPosition(index)
            if row > 0 and col > 0:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def _slot_occurs_this_week(self, slot):
        if hasattr(slot, "occurs_in_week"):
            return slot.occurs_in_week(self.current_week)

        start_week = get_field(slot, "start_week", 1)
        end_week = get_field(slot, "end_week", 16)
        week_type = get_field(slot, "week_type", "all")
        if not (start_week <= self.current_week <= end_week):
            return False
        if week_type == "odd" and self.current_week % 2 == 0:
            return False
        if week_type == "even" and self.current_week % 2 != 0:
            return False
        return True

    def _slot_to_grid_position(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))

        start_row = None
        end_row = None
        for index, (_label, period_start, period_end) in enumerate(self.PERIODS, start=1):
            if start_time < period_end and end_time > period_start:
                if start_row is None:
                    start_row = index
                end_row = index

        if start_row is None:
            start_row = 1
            end_row = 1
        if end_row is None or end_row < start_row:
            end_row = start_row
        return start_row, max(1, end_row - start_row + 1)

    @staticmethod
    def _coerce_time(value):
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            text = value.strip()
            if len(text.split(":")[0]) == 1:
                text = "0" + text
            return time.fromisoformat(text[:5])
        return time(8, 0)

    def _build_slot_card(self, slot):
        course_id = get_field(slot, "course_id")
        colors = {
            101: ("#D5F5E3", "#2ECC71"),
            102: ("#EBF5FB", "#3498DB"),
            103: ("#FEF9E7", "#F1C40F"),
            999: ("#E8F8F5", "#117864")
        }
        card_color, border_color = colors.get(course_id, ("#EBDEF0", "#8E44AD"))

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
            """
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(2)

        if not self._is_exact_period_slot(slot):
            time_text = QLabel(self._slot_time_text(slot))
            time_text.setStyleSheet("color: #117864; font-size: 9px; font-weight: bold;")
            time_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(time_text)

        title = QLabel(get_field(slot, "title", "未知课程"))
        title.setStyleSheet("font-weight: bold; color: #2C3E50; font-size: 11px;")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        location = QLabel(get_field(slot, "location", "未指定地点"))
        location.setStyleSheet("color: #7F8C8D; font-size: 9px;")
        location.setWordWrap(True)
        location.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addWidget(location)
        return card

    def _is_exact_period_slot(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))
        period_starts = {period_start for _label, period_start, _period_end in self.PERIODS}
        period_ends = {period_end for _label, _period_start, period_end in self.PERIODS}
        return start_time in period_starts and end_time in period_ends

    def _slot_time_text(self, slot):
        start_time = self._coerce_time(get_field(slot, "start_time"))
        end_time = self._coerce_time(get_field(slot, "end_time"))
        return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"

    def _show_slot_menu(self, slot, widget, pos):
        menu = QMenu(widget)
        edit_action = QAction("Edit", widget)
        delete_action = QAction("Delete", widget)
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
            self.refresh_schedule()
            return

        if self._try_update_backend_slot(slot, updated):
            self.refresh_schedule()
            return

        QMessageBox.information(self, "Edit unavailable", "This course comes from the backend, but AppFacade has no update_schedule_slot() method yet.")

    def _delete_slot(self, slot):
        title = get_field(slot, "title", "this course")
        reply = QMessageBox.question(
            self,
            "Delete course",
            f"Delete '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self._is_custom_slot(slot):
            self._remove_custom_slot(slot)
            self.refresh_schedule()
            return

        if self._try_delete_backend_slot(slot):
            self.refresh_schedule()
            return

        QMessageBox.information(self, "Delete unavailable", "This course comes from the backend, but AppFacade has no delete_schedule_slot() method yet.")

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

    @staticmethod
    def _badge_style(color):
        return (
            f"background-color: {color}; color: #FFFFFF; border-radius: 4px; "
            "padding: 4px 8px; font-size: 12px; font-weight: bold; min-width: 44px;"
        )

    @staticmethod
    def _fallback_slots():
        return [
            {
                "course_id": 101,
                "title": "算法设计与分析",
                "weekday": 1,
                "start_time": "08:00",
                "end_time": "09:50",
                "location": "教三-301",
                "start_week": 1,
                "end_week": 16,
                "week_type": "all",
            },
            {
                "course_id": 102,
                "title": "编译原理",
                "weekday": 2,
                "start_time": "10:10",
                "end_time": "12:00",
                "location": "实验楼-502",
                "start_week": 1,
                "end_week": 8,
                "week_type": "odd",
            },
            {
                "course_id": 103,
                "title": "计算概论",
                "weekday": 3,
                "start_time": "14:00",
                "end_time": "16:00",
                "location": "理科楼-102",
                "start_week": 2,
                "end_week": 16,
                "week_type": "even",
            },
        ]


if __name__ == "__main__":
    class FakeFacadeForTest:
        def list_schedule(self, weekday, week):
            return [slot for slot in ScheduleWidget._fallback_slots() if slot["weekday"] == weekday]

    app = QApplication(sys.argv)
    test_window = ScheduleWidget(facade=FakeFacadeForTest())
    test_window.setWindowTitle("ScheduleWidget Debug")
    test_window.resize(900, 700)
    test_window.show()
    sys.exit(app.exec())
