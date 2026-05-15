from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


__all__ = ["Exam"]


@dataclass
class Exam:
    name: str                       # 考试名称
    start_time: datetime            # 考试开始时间
    end_time: datetime              # 考试结束时间
    location: str                   # 考试地点
    id: int | None = None           # 本地数据库 ID
    course_id: int | None = None   # 所属课程
    exam_type: str = "other"        # midterm / final / quiz / other
    source: str = "manual"          # manual / sync
    external_id: str | None = None  # 教学网考试 ID
    raw_payload: str = ""           # 原始同步内容，调试用

    def duration_hours(self) -> float:
        raise NotImplementedError
    def is_finished(self, now: datetime) -> bool:
        raise NotImplementedError
    def is_upcoming(self, now: datetime) -> bool:
        raise NotImplementedError
    def days_left(self, now: datetime) -> int:
        raise NotImplementedError
    def display_name(self) -> str:
        raise NotImplementedError


if __name__ == "__main__":
    e = Exam(name="Test exam", start_time=datetime.now(), 
             end_time=datetime.now(), location="理教")
    print(e)
