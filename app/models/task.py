from dataclasses import dataclass, field
from datetime import datetime, timedelta

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
    is_hidden: bool = False                                    # 软删除标志：对同步任务不物理删除

    def mark_done(self, now: datetime) -> None:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        self.status = "done"
        self.completed_at = now
        self.updated_at = now

    def reopen(self, now: datetime) -> None:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        self.status = "todo"
        self.completed_at = None
        self.updated_at = now

    def is_done(self) -> bool:
        return self.status == "done"

    def is_overdue(self, now: datetime) -> bool:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        return not self.is_done() and self.due_time < now

    def is_due_within(self, now: datetime, days: int) -> bool:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        if not isinstance(days, int) or isinstance(days, bool):
            raise TypeError("days must be int")
        if days < 0:
            raise ValueError("days must be >= 0")
        if self.is_done():
            return False
        return now <= self.due_time <= now + timedelta(days=days)

    def days_left(self, now: datetime) -> int:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        delta = self.due_time - now
        return delta.days

    def update_estimated_hours(self, hours: float, now: datetime) -> None:
        if not isinstance(hours, (int, float)) or isinstance(hours, bool):
            raise TypeError("hours must be a number")
        if hours < 0:
            raise ValueError("hours must be >= 0")
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")
        self.estimated_hours = float(hours)
        self.updated_at = now


if __name__ == "__main__":
    t = Task("Test task", datetime.now())
    print(t)
