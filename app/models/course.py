from dataclasses import dataclass, field
from datetime import datetime


__all__ = ["Course"]


@dataclass
class Course:
    name: str                       # 课程名
    id: int | None = None           # 本地数据库 ID
    teacher: str = ""               # 教师
    semester: str = ""              # 学期
    external_id: str | None = None  # 教学网课程 ID
    color: str = "#4F81BD"        # GUI 显示颜色
    source: str = "manual"          # manual / sync
    raw_payload: str = ""           # 原始同步内容，调试用

    def display_name(self) -> str:
        raise NotImplementedError
    def has_external_id(self) -> bool:
        raise NotImplementedError
    

if __name__ == "__main__":
    c = Course("Test")
    print(c)