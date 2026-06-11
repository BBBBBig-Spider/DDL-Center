from __future__ import annotations

from datetime import datetime

from app.parsers import ddl_parser as ddl_parser_module
from app.parsers.ddl_parser import DDLParser


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 12, 20, 12, 0)


def test_blackboard_due_time_without_year_rolls_forward_across_year(monkeypatch) -> None:
    monkeypatch.setattr(ddl_parser_module, "datetime", FixedDateTime)

    parsed = DDLParser()._parse_blackboard_due_time(
        "提交截止时间: 北京时间1月5日23:59"
    )

    assert parsed == datetime(2027, 1, 5, 23, 59)


def test_blackboard_due_date_with_chinese_weekday_and_pm() -> None:
    # Real-world Blackboard layout for an assignment "Lab4":
    # "到期日期 / 2026年6月30日 星期二 / 下午11:59"
    # Whitespace gets collapsed by the parser before matching.
    raw = (
        "Lab4：上载作业： lab4 作业信息 到期日期 2026年6月30日 星期二 下午11:59 "
        "满分 100 提交截止时间:lab4的提交时间为6月30日23:59 "
        "请毕业班的同学务必6月21日前提交"
    )
    parsed = DDLParser()._parse_blackboard_due_time(raw)
    assert parsed == datetime(2026, 6, 30, 23, 59)


def test_blackboard_due_date_no_year_with_pm() -> None:
    # Same layout but no year — the "无 year + 30天兜底" path should leave
    # an in-range future date alone.
    raw = "到期日期 6月30日 星期二 下午11:59"
    parsed = DDLParser()._parse_blackboard_due_time(raw)
    assert parsed is not None
    assert (parsed.month, parsed.day, parsed.hour, parsed.minute) == (6, 30, 23, 59)


def test_blackboard_due_time_keyword_separated_from_date_by_filler() -> None:
    # Real-world lab4 wording: "提交截止时间:lab4的提交时间为6月30日23:59".
    # The 截止 keyword is 9 chars away from the date — historically the regex
    # required them to be adjacent and silently dropped this row.
    raw = "lab4 已附加文件: lab4.zip ( 2.355 MB ) 提交截止时间:lab4的提交时间为6月30日23:59"
    parsed = DDLParser()._parse_blackboard_due_time(raw)
    assert parsed is not None
    assert (parsed.month, parsed.day, parsed.hour, parsed.minute) == (6, 30, 23, 59)
