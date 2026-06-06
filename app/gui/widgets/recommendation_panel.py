from __future__ import annotations

import sys
from datetime import datetime, time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import BORDER, INK, MUTED, PKU_RED, PKU_RED_DARK, PKU_RED_LIGHT, TEXT, secondary_button_style


def get_field(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def format_time_field(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:5]
    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)[:5]


def duration_hours(slot_obj) -> float | None:
    start = format_time_field(get_field(slot_obj, "start_time"))
    end = format_time_field(get_field(slot_obj, "end_time"))
    try:
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
    except ValueError:
        return None
    return max(0.0, (end_dt - start_dt).total_seconds() / 3600)


def arrangement_from_slot(task_id: int, task_title: str, slot_obj, week: int | None = None) -> dict:
    return {
        "task_id": task_id,
        "task_title": task_title,
        "title": task_title,
        "weekday": get_field(slot_obj, "weekday", 1),
        "start_time": format_time_field(get_field(slot_obj, "start_time", "09:00")),
        "end_time": format_time_field(get_field(slot_obj, "end_time", "11:00")),
        "location": get_field(slot_obj, "location", "") or "任务安排",
        "week": week,
        "source": "gui",
    }


class RecommendationItemWidget(QFrame):
    adopt_clicked = Signal(object)

    def __init__(self, slot_obj, parent=None):
        super().__init__(parent)
        self.slot_obj = slot_obj
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("recommendationItem")
        self.setMinimumHeight(78)
        self.setStyleSheet(
            f"""
            QFrame#recommendationItem {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QFrame#recommendationItem:hover {{
                border-color: {PKU_RED};
                background-color: {PKU_RED_LIGHT};
            }}
            QFrame#recommendationItem QLabel {{
                background-color: transparent;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        weekday_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        weekday = get_field(self.slot_obj, "weekday", 1)
        start_time = format_time_field(get_field(self.slot_obj, "start_time", "09:00"))
        end_time = format_time_field(get_field(self.slot_obj, "end_time", "11:00"))
        location = get_field(self.slot_obj, "location", "") or "自习区"
        hours = duration_hours(self.slot_obj)
        hours_text = f" · {hours:.1f}h" if hours is not None else ""

        time_label = QLabel(f"{weekday_map.get(weekday, '周一')}  {start_time}-{end_time}{hours_text}")
        time_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {INK};")

        reason = get_field(self.slot_obj, "title", "") or "推荐空闲时间段"
        reason_label = QLabel(reason)
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet(f"font-size: 12px; color: {TEXT};")

        location_label = QLabel(location)
        location_label.setStyleSheet(f"font-size: 11px; color: {MUTED};")

        info_layout.addWidget(time_label)
        info_layout.addWidget(reason_label)
        info_layout.addWidget(location_label)
        layout.addLayout(info_layout, stretch=1)

        adopt_button = QPushButton("采用")
        adopt_button.setCursor(Qt.CursorShape.PointingHandCursor)
        adopt_button.setFixedWidth(58)
        adopt_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {PKU_RED};
                border: 1px solid {PKU_RED};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {PKU_RED_LIGHT};
                border-color: {PKU_RED_DARK};
            }}
            """
        )
        adopt_button.clicked.connect(lambda: self.adopt_clicked.emit(self.slot_obj))
        layout.addWidget(adopt_button, alignment=Qt.AlignmentFlag.AlignVCenter)


class CurrentArrangementWidget(QFrame):
    cancel_clicked = Signal()

    def __init__(self, arrangement, parent=None):
        super().__init__(parent)
        self.arrangement = arrangement
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("currentArrangement")
        self.setStyleSheet(
            f"""
            QFrame#currentArrangement {{
                background-color: {PKU_RED_LIGHT};
                border: 1px solid #E7B8B8;
                border-radius: 6px;
            }}
            QFrame#currentArrangement QLabel {{
                background-color: transparent;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        weekday_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        weekday = get_field(self.arrangement, "weekday", 1)
        start_time = format_time_field(get_field(self.arrangement, "start_time", "09:00"))
        end_time = format_time_field(get_field(self.arrangement, "end_time", "11:00"))

        label = QLabel(f"已安排：{weekday_map.get(weekday, '周一')} {start_time}-{end_time}")
        label.setWordWrap(True)
        label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {PKU_RED};")
        layout.addWidget(label, stretch=1)

        cancel_button = QPushButton("取消")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.setStyleSheet(secondary_button_style())
        cancel_button.clicked.connect(self.cancel_clicked.emit)
        layout.addWidget(cancel_button)


class RecommendationPanel(QWidget):
    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.current_task_id: int | None = None
        self.current_task_title = ""
        self._local_arrangements: dict[int, dict] = {}
        self._init_ui()
        self.refresh_panel()

    def _init_ui(self) -> None:
        self.setObjectName("recommendationPanel")
        self.setStyleSheet(
            """
            QWidget#recommendationPanel {
                background-color: transparent;
            }
            QWidget#recommendationPanel QLabel {
                background-color: transparent;
            }
            """
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel("智能排程推荐")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {INK};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        refresh_button = QPushButton("刷新")
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.setStyleSheet(secondary_button_style())
        refresh_button.clicked.connect(self.refresh_panel)
        header_layout.addWidget(refresh_button)
        self.main_layout.addLayout(header_layout)

        self.task_badge = QLabel("请先选择一个任务")
        self.task_badge.setWordWrap(True)
        self.task_badge.setStyleSheet(self._badge_style(active=False))
        self.main_layout.addWidget(self.task_badge)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            """
        )

        list_container = QWidget()
        list_container.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(list_container)
        self.main_layout.addWidget(scroll_area, stretch=1)

    def _badge_style(self, active: bool) -> str:
        if active:
            return (
                f"background-color: {PKU_RED_LIGHT}; color: {PKU_RED}; border-radius: 4px; "
                "padding: 7px 10px; font-size: 12px; font-weight: 700; border: 1px solid #E7B8B8;"
            )
        return (
            "background-color: #FFFFFF; color: #6B7280; border-radius: 4px; "
            f"padding: 7px 10px; font-size: 12px; border: 1px dashed {BORDER};"
        )

    def set_task(self, task_id: int, task_title: str) -> None:
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.task_badge.setText(f"当前任务：{task_title}")
        self.task_badge.setStyleSheet(self._badge_style(active=True))
        self.refresh_panel()

    def clear_task(self) -> None:
        self.current_task_id = None
        self.current_task_title = ""
        self.task_badge.setText("请先选择一个任务")
        self.task_badge.setStyleSheet(self._badge_style(active=False))
        self.refresh_panel()

    def refresh_panel(self) -> None:
        self._clear_items()

        if self.current_task_id is None:
            self._show_empty("暂无推荐\n请先在任务列表中选择一个任务")
            return

        arrangement = self._load_current_arrangement()
        if arrangement is not None:
            current = CurrentArrangementWidget(arrangement)
            current.cancel_clicked.connect(self.cancel_current_arrangement)
            self.list_layout.addWidget(current)

        recommendations = self._load_recommendations()
        if not recommendations:
            if arrangement is None:
                self._show_empty("没有可用时间段\n请检查课表占用或任务预计耗时")
            return

        for slot in recommendations:
            item = RecommendationItemWidget(slot)
            item.adopt_clicked.connect(self.on_adopt_recommendation)
            self.list_layout.addWidget(item)

    def _clear_items(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_empty(self, text: str) -> None:
        empty_label = QLabel(text)
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #9CA3AF; font-size: 12px; padding-top: 40px; background-color: transparent;")
        self.list_layout.addWidget(empty_label)

    def _load_current_arrangement(self):
        if self.current_task_id is None:
            return None
        if self.facade and hasattr(self.facade, "get_task_arrangement"):
            try:
                backend_arrangement = self.facade.get_task_arrangement(self.current_task_id)
                if backend_arrangement is not None:
                    return backend_arrangement
            except Exception as exc:
                print(f"[GUI] failed to load task arrangement: {exc}")
        return self._local_arrangements.get(self.current_task_id)

    def _load_recommendations(self):
        if not self.facade or not hasattr(self.facade, "recommend_for_task"):
            return []
        try:
            return self.facade.recommend_for_task(self.current_task_id)
        except NotImplementedError:
            return []
        except Exception as exc:
            print(f"[GUI] failed to load recommendations: {exc}")
            return []

    def on_adopt_recommendation(self, slot_obj) -> None:
        if self.current_task_id is None:
            return
        try:
            if self.facade and hasattr(self.facade, "arrange_task_at_slot"):
                self.facade.arrange_task_at_slot(self.current_task_id, slot_obj)
            else:
                self._local_arrangements[self.current_task_id] = arrangement_from_slot(
                    self.current_task_id,
                    self.current_task_title,
                    slot_obj,
                    self._current_schedule_week(),
                )
        except Exception as exc:
            QMessageBox.critical(self, "安排失败", str(exc))
            return
        self.refresh_panel()
        self._refresh_schedule_page()

    def cancel_current_arrangement(self) -> None:
        if self.current_task_id is None:
            return
        try:
            if self.facade and hasattr(self.facade, "cancel_task_arrangement"):
                self.facade.cancel_task_arrangement(self.current_task_id)
            self._local_arrangements.pop(self.current_task_id, None)
        except Exception as exc:
            QMessageBox.critical(self, "取消失败", str(exc))
            return
        self.refresh_panel()
        self._refresh_schedule_page()

    def _current_schedule_week(self) -> int | None:
        schedule_page = getattr(self.window(), "schedule_page", None)
        return getattr(schedule_page, "current_week", None)

    def _refresh_schedule_page(self) -> None:
        window = self.window()
        schedule_page = getattr(window, "schedule_page", None)
        if schedule_page and hasattr(schedule_page, "set_gui_task_arrangements"):
            schedule_page.set_gui_task_arrangements(list(self._local_arrangements.values()))
        elif schedule_page and hasattr(schedule_page, "refresh_schedule"):
            schedule_page.refresh_schedule()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = RecommendationPanel()
    panel.resize(360, 520)
    panel.show()
    sys.exit(app.exec())
