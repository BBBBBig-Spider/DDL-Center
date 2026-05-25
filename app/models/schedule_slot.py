from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from app.models.task import Task


__all__ = ["ScheduleSlot"]


_WEEKDAY_LABELS = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}


@dataclass
class ScheduleSlot:
    title: str                       # 时间段标题，如"高数讲授课"
    weekday: int                    # 星期几，1–7
    start_time: time                # 开始时间
    end_time: time                  # 结束时间
    location: str                   # 上课 / 活动地点
    slot_type: str                  # lecture / lab / tutorial / custom / free
    start_week: int                 # 起始周
    end_week: int                   # 结束周（含）
    id: int | None = None           # 本地数据库 ID
    course_id: int | None = None    # 关联课程；非课程占用可为 None
    week_type: str = "all"          # all / odd / even
    source: str = "manual"          # manual / sync
    external_id: str | None = None  # 外部来源 ID

    def duration_hours(self) -> float:
        today = date.today()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        return (end_dt - start_dt).total_seconds() / 3600.0

    def occurs_in_week(self, week: int) -> bool:
        if not isinstance(week, int) or isinstance(week, bool):
            raise TypeError("week must be int")
        if week < self.start_week or week > self.end_week:
            return False
        if self.week_type == "all":
            return True
        if self.week_type == "odd":
            return week % 2 == 1
        if self.week_type == "even":
            return week % 2 == 0
        return False

    def overlaps_with(self, other: ScheduleSlot) -> bool:
        if not isinstance(other, ScheduleSlot):
            raise TypeError("other must be a ScheduleSlot")
        if self.weekday != other.weekday:
            return False
        week_overlap_start = max(self.start_week, other.start_week)
        week_overlap_end = min(self.end_week, other.end_week)
        if week_overlap_start > week_overlap_end:
            return False
        share_week = False
        for week in range(week_overlap_start, week_overlap_end + 1):
            if self.occurs_in_week(week) and other.occurs_in_week(week):
                share_week = True
                break
        if not share_week:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time

    def can_hold_task(self, task: Task) -> bool:
        if not isinstance(task, Task):
            raise TypeError("task must be a Task")
        if self.slot_type != "free":
            return False
        return self.duration_hours() >= task.estimated_hours

    def display_time(self) -> str:
        label = _WEEKDAY_LABELS.get(self.weekday, str(self.weekday))
        return f"{label} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


if __name__ == "__main__":
    s = ScheduleSlot(title="Test class", weekday=1,
                    start_time=time(0, 0), end_time=time(1, 0),
                    location="理教", slot_type="lecture",
                    start_week=1, end_week=1)
    print(s)
