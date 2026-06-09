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
