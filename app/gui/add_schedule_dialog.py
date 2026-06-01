import sys

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class AddCourseDialog(QDialog):
    PERIOD_TIMES = [
        ("08:00", "08:50"),
        ("09:00", "09:50"),
        ("10:10", "11:00"),
        ("11:10", "12:00"),
        ("13:00", "13:50"),
        ("14:00", "14:50"),
        ("15:10", "16:00"),
        ("16:10", "17:00"),
        ("17:10", "18:00"),
        ("18:40", "19:30"),
        ("19:40", "20:30"),
        ("20:40", "21:30"),
    ]

    def __init__(self, parent=None, course_data=None):
        super().__init__(parent)
        self.course_data = course_data
        self.setWindowTitle("Edit Course" if course_data else "Add Course")
        self.setFixedWidth(340)
        self.init_ui()
        if course_data is not None:
            self.load_course_data(course_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        input_style = """
            QLineEdit, QComboBox, QSpinBox, QTimeEdit {
                padding: 5px;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #262626;
                selection-background-color: #BAE7FF;
                selection-color: #262626;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #262626;
                selection-background-color: #E6F7FF;
                selection-color: #262626;
                outline: 0;
            }
        """
        label_style = "font-weight: bold; color: #434343; font-size: 12px;"

        lbl_title = QLabel("课程名:")
        lbl_title.setStyleSheet(label_style)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("请输入课程或活动名称")
        self.txt_title.setStyleSheet(input_style)
        layout.addWidget(lbl_title)
        layout.addWidget(self.txt_title)

        lbl_location = QLabel("地点：")
        lbl_location.setStyleSheet(label_style)
        self.txt_location = QLineEdit()
        self.txt_location.setPlaceholderText("请输入活动地点")
        self.txt_location.setStyleSheet(input_style)
        layout.addWidget(lbl_location)
        layout.addWidget(self.txt_location)

        lbl_weekday = QLabel("星期几：")
        lbl_weekday.setStyleSheet(label_style)
        self.cmb_weekday = QComboBox()
        for text, val in [("Mon", 1), ("Tue", 2), ("Wed", 3), ("Thu", 4), ("Fri", 5), ("Sat", 6), ("Sun", 7)]:
            self.cmb_weekday.addItem(text, val)
        self.cmb_weekday.setStyleSheet(input_style)
        layout.addWidget(lbl_weekday)
        layout.addWidget(self.cmb_weekday)

        lbl_time_mode = QLabel("时间：")
        lbl_time_mode.setStyleSheet(label_style)
        self.cmb_time_mode = QComboBox()
        self.cmb_time_mode.addItem("按节次选择", "period")
        self.cmb_time_mode.addItem("按时间选择", "custom")
        self.cmb_time_mode.setStyleSheet(input_style)
        self.cmb_time_mode.currentIndexChanged.connect(self._update_time_mode)
        layout.addWidget(lbl_time_mode)
        layout.addWidget(self.cmb_time_mode)

        lbl_period = QLabel("节次:")
        lbl_period.setStyleSheet(label_style)
        self.period_row = QWidget()
        period_layout = QHBoxLayout(self.period_row)
        period_layout.setContentsMargins(0, 0, 0, 0)
        self.cmb_start_period = QComboBox()
        self.cmb_end_period = QComboBox()
        for i in range(1, 13):
            self.cmb_start_period.addItem(f"第{i}节")
            self.cmb_end_period.addItem(f"第{i}节")
        self.cmb_start_period.setStyleSheet(input_style)
        self.cmb_end_period.setStyleSheet(input_style)
        self.cmb_start_period.currentIndexChanged.connect(self._sync_end_period)
        period_layout.addWidget(self.cmb_start_period)
        lbl_to = QLabel("--")
        lbl_to.setAlignment(Qt.AlignmentFlag.AlignCenter)
        period_layout.addWidget(lbl_to)
        period_layout.addWidget(self.cmb_end_period)
        layout.addWidget(lbl_period)
        layout.addWidget(self.period_row)

        self.custom_time_row = QWidget()
        custom_time_layout = QHBoxLayout(self.custom_time_row)
        custom_time_layout.setContentsMargins(0, 0, 0, 0)
        self.start_time_edit = QTimeEdit(QTime(8, 0))
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setStyleSheet(input_style)
        self.end_time_edit = QTimeEdit(QTime(8, 50))
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit.setStyleSheet(input_style)
        custom_time_layout.addWidget(self.start_time_edit)
        custom_to_label = QLabel("--")
        custom_to_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        custom_time_layout.addWidget(custom_to_label)
        custom_time_layout.addWidget(self.end_time_edit)
        layout.addWidget(self.custom_time_row)
        self._update_time_mode()

        lbl_weeks = QLabel("周次：")
        lbl_weeks.setStyleSheet(label_style)
        weeks_layout = QHBoxLayout()
        self.spn_start_week = QSpinBox()
        self.spn_start_week.setRange(1, 32)
        self.spn_start_week.setValue(1)
        self.spn_start_week.setStyleSheet(input_style)
        self.spn_end_week = QSpinBox()
        self.spn_end_week.setRange(1, 32)
        self.spn_end_week.setValue(16)
        self.spn_end_week.setStyleSheet(input_style)
        weeks_layout.addWidget(self.spn_start_week)
        lbl_week_to = QLabel("--")
        lbl_week_to.setAlignment(Qt.AlignmentFlag.AlignCenter)
        weeks_layout.addWidget(lbl_week_to)
        weeks_layout.addWidget(self.spn_end_week)
        layout.addWidget(lbl_weeks)
        layout.addLayout(weeks_layout)

        lbl_type = QLabel("单双周情况")
        lbl_type.setStyleSheet(label_style)
        self.cmb_week_type = QComboBox()
        self.cmb_week_type.addItem("每周", "all")
        self.cmb_week_type.addItem("单周", "odd")
        self.cmb_week_type.addItem("双周", "even")
        self.cmb_week_type.setStyleSheet(input_style)
        layout.addWidget(lbl_type)
        layout.addWidget(self.cmb_week_type)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("padding: 5px 12px; border: 1px solid #D9D9D9; border-radius: 4px; background: white;")
        btn_cancel.clicked.connect(self.reject)
        btn_confirm = QPushButton("保存" if self.course_data else "添加")
        btn_confirm.setStyleSheet("padding: 5px 12px; border: 1px solid #1890FF; border-radius: 4px; background: #1890FF; color: white; font-weight: bold;")
        btn_confirm.clicked.connect(self.on_confirm_clicked)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def _sync_end_period(self, index):
        if self.cmb_end_period.currentIndex() < index:
            self.cmb_end_period.setCurrentIndex(index)

    def _update_time_mode(self):
        is_custom = self.cmb_time_mode.currentData() == "custom"
        self.period_row.setVisible(not is_custom)
        self.custom_time_row.setVisible(is_custom)

    def load_course_data(self, data):
        self.txt_title.setText(str(self._get_field(data, "title", "")))
        self.txt_location.setText(str(self._get_field(data, "location", "")))

        weekday_index = self.cmb_weekday.findData(self._get_field(data, "weekday", 1))
        if weekday_index != -1:
            self.cmb_weekday.setCurrentIndex(weekday_index)

        start_index = self._period_index_for_time(self._get_field(data, "start_time"), is_start=True)
        end_index = self._period_index_for_time(self._get_field(data, "end_time"), is_start=False)
        self.cmb_start_period.setCurrentIndex(start_index)
        self.cmb_end_period.setCurrentIndex(max(start_index, end_index))

        start_time = self._qtime_from_value(self._get_field(data, "start_time"), QTime(8, 0))
        end_time = self._qtime_from_value(self._get_field(data, "end_time"), QTime(8, 50))
        self.start_time_edit.setTime(start_time)
        self.end_time_edit.setTime(end_time)
        if not self._is_exact_period_range(start_time, end_time):
            self.cmb_time_mode.setCurrentIndex(self.cmb_time_mode.findData("custom"))
        else:
            self.cmb_time_mode.setCurrentIndex(self.cmb_time_mode.findData("period"))
        self._update_time_mode()

        self.spn_start_week.setValue(int(self._get_field(data, "start_week", 1)))
        self.spn_end_week.setValue(int(self._get_field(data, "end_week", 16)))

        week_type_index = self.cmb_week_type.findData(self._get_field(data, "week_type", "all"))
        if week_type_index != -1:
            self.cmb_week_type.setCurrentIndex(week_type_index)

    def on_confirm_clicked(self):
        if not self.txt_title.text().strip():
            QMessageBox.warning(self, "Validation failed", "Course name cannot be empty.")
            return
        if self.cmb_end_period.currentIndex() < self.cmb_start_period.currentIndex():
            QMessageBox.warning(self, "Validation failed", "End period cannot be before start period.")
            return
        if self.cmb_time_mode.currentData() == "custom" and self.end_time_edit.time() <= self.start_time_edit.time():
            QMessageBox.warning(self, "Validation failed", "End time must be after start time.")
            return
        if self.spn_end_week.value() < self.spn_start_week.value():
            QMessageBox.warning(self, "Validation failed", "End week cannot be before start week.")
            return
        self.accept()

    def get_course_data(self):
        start_idx = self.cmb_start_period.currentIndex()
        end_idx = self.cmb_end_period.currentIndex()
        if self.cmb_time_mode.currentData() == "custom":
            start_time = self.start_time_edit.time().toString("HH:mm")
            end_time = self.end_time_edit.time().toString("HH:mm")
        else:
            start_time = self.PERIOD_TIMES[start_idx][0]
            end_time = self.PERIOD_TIMES[end_idx][1]
        payload = {
            "course_id": self._get_field(self.course_data, "course_id", 999),
            "title": self.txt_title.text().strip(),
            "location": self.txt_location.text().strip() or "Unspecified",
            "weekday": self.cmb_weekday.currentData(),
            "start_time": start_time,
            "end_time": end_time,
            "start_week": self.spn_start_week.value(),
            "end_week": self.spn_end_week.value(),
            "week_type": self.cmb_week_type.currentData(),
        }
        for key in ("id", "_local_id"):
            value = self._get_field(self.course_data, key)
            if value is not None:
                payload[key] = value
        return payload

    @classmethod
    def _period_index_for_time(cls, value, *, is_start):
        if hasattr(value, "strftime"):
            text = value.strftime("%H:%M")
        else:
            text = str(value or "")[:5]
        column = 0 if is_start else 1
        for index, period in enumerate(cls.PERIOD_TIMES):
            if period[column] == text:
                return index
        return 0

    @classmethod
    def _is_exact_period_range(cls, start_time, end_time):
        start_text = start_time.toString("HH:mm") if hasattr(start_time, "toString") else str(start_time)[:5]
        end_text = end_time.toString("HH:mm") if hasattr(end_time, "toString") else str(end_time)[:5]
        starts = {period[0] for period in cls.PERIOD_TIMES}
        ends = {period[1] for period in cls.PERIOD_TIMES}
        return start_text in starts and end_text in ends

    @staticmethod
    def _qtime_from_value(value, default):
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return QTime(value.hour, value.minute)
        parsed = QTime.fromString(str(value or "")[:5], "HH:mm")
        return parsed if parsed.isValid() else default

    @staticmethod
    def _get_field(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AddCourseDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print(dialog.get_course_data())
    sys.exit()
