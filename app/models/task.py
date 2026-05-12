from dataclasses import dataclass, field
from datetime import datetime

__all__ = ["Task"]

@dataclass
class Task:
    title: str                                                 # 任务标题
    due_time: datetime                                         # 截止时间
    id: int | None = None                                       # 本地数据库 ID
    course_id: int | None = None                               # 所属课程
    related_exam_id: int | None = None                         # 关联考试
    description: str = ""                                      # 任务描述
    estimated_hours: float = 1.0                               # 预计耗时
    status: str = "todo"                                       # todo / doing / done / blocked
    priority: int = 2                                          # 1 高，2 中，3 低
    source: str = "manual"                                       # manual / sync
    user_modified: bool = False                                # 用户手动改过的任务在同步时不被覆盖（默认 False）
    external_id: str | None = None                             # 教学网来源 ID
    created_at: datetime = field(default_factory=datetime.now) # 创建时间
    updated_at: datetime = field(default_factory=datetime.now) # 更新时间
    completed_at: datetime | None = None                       # 完成时间
    raw_payload: str = ""                                      # 调试用原始同步内容

    def mark_done(self, now: datetime) -> None:
        raise NotImplementedError
    def reopen(self, now: datetime) -> None:
        raise NotImplementedError
    def is_done(self) -> bool:
        raise NotImplementedError
    def is_overdue(self, now: datetime) -> bool:
        raise NotImplementedError
    def is_due_within(self, now: datetime, days: int) -> bool:
        raise NotImplementedError
    def days_left(self, now: datetime) -> int:
        raise NotImplementedError
    def update_estimated_hours(self, hours: float, now: datetime) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    t = Task("Test task", datetime.now())
    print(t)