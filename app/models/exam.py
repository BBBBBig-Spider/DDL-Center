from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


__all__ = ["Exam"]


_EXAM_TYPE_LABELS = {
    "midterm": "期中",
    "final": "期末",
    "quiz": "小测",
    "other": "考试",
}


@dataclass
class Exam:
    course_id: int                  # 所属课程
    name: str                       # 考试名称
    start_time: datetime            # 考试开始时间
    end_time: datetime              # 考试结束时间
    location: str                   # 考试地点
    id: int | None = None           # 本地数据库 ID
    exam_type: str = "other"        # midterm / final / quiz / other
    source: str = "manual"          # manual / sync
    external_id: str | None = None  # 教学网考试 ID
    raw_payload: str = ""           # 原始同步内容，调试用

    def duration_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600.0

    def is_finished(self, now: datetime) -> bool:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        return now > self.end_time

    def is_upcoming(self, now: datetime) -> bool:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        return self.start_time > now

    def days_left(self, now: datetime) -> int:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        return (self.start_time - now).days

    def display_name(self) -> str:
        label = _EXAM_TYPE_LABELS.get(self.exam_type, self.exam_type)
        return f"{self.name}（{label}）"


if __name__ == "__main__":
    e = Exam(course_id=1, name="Test exam", start_time=datetime.now(),
             end_time=datetime.now(), location="理教")
    print(e)
