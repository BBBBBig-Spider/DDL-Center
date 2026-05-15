from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


__all__ = ["Alert"]


@dataclass
class Alert:
    task_id: int | None = None                                  # 对应任务
    level: str                                                  # info / warning / urgent / overdue
    kind: str                                                   # deadline / overload / progress
    message: str                                                # 提醒文本
    id: int | None = None                                       # 本地数据库 ID
    created_at: datetime = field(default_factory=datetime.now)  # 生成时间
    is_read: bool = False                                       # 是否已读
    target_type: str = "task"                                   # 'task' | 'day' | 'global'

    def is_urgent(self) -> bool:
        raise NotImplementedError
    def display_text(self) -> str:
        raise NotImplementedError
    

if __name__ == "__main__":
    a = Alert(task_id=1, level="info", kind="progress", message="Test")
    print(a)