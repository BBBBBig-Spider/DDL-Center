from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from task import Task


__all__ = ["ScheduleSlot"]


@dataclass
class ScheduleSlot:
    title: str                       # 时间段标题，如“高数讲授课”
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
        raise NotImplementedError
    def occurs_in_week(self, week: int) -> bool:
        raise NotImplementedError
    def overlaps_with(self, other: ScheduleSlot) -> bool:
        raise NotImplementedError
    def can_hold_task(self, task: Task) -> bool:
        raise NotImplementedError
    def display_time(self) -> str:
        raise NotImplementedError
    

if __name__ == "__main__":
    s = ScheduleSlot(title="Test class", weekday=1,
                    start_time=time(0, 0), end_time=time(1, 0),
                    location="理教", slot_type="lecture",
                    start_week=1, end_week=1)
    print(s)