# tests/test_mock_data.py
"""
Mock 数据回归测试（架构规划 Part 5.1 教学网保底）。

目的：保证 data/ 下的本地样例文件始终存在且结构合法，
真实教学网不可用时，离线 fallback 演示路径不会悄悄失效。

- mock_ddl.html：有真实存在的 DDLParser，端到端验证能解析成 Task。
- mock_schedule.html / mock_exams.html：对应的 ScheduleParser / ExamParser
  由 B 负责、尚未实现，这里先做"文件存在 + 关键结构标记齐全"的轻量校验，
  等解析器落地后再补端到端断言。
"""
from __future__ import annotations

import unittest
from datetime import datetime

from bs4 import BeautifulSoup

from app.config import MOCK_DDL_PATH, MOCK_EXAMS_PATH, MOCK_SCHEDULE_PATH
from app.models.task import Task
from app.parsers.ddl_parser import DDLParser


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestMockDDL(unittest.TestCase):
    """mock_ddl.html 必须能被 DDLParser 端到端解析。"""

    def setUp(self) -> None:
        self.html = _read(MOCK_DDL_PATH)
        self.tasks = DDLParser().parse(self.html)

    def test_parses_expected_number_of_tasks(self) -> None:
        self.assertEqual(len(self.tasks), 5)

    def test_every_task_is_valid_sync_task(self) -> None:
        for task in self.tasks:
            self.assertIsInstance(task, Task)
            self.assertEqual(task.source, "sync")
            self.assertTrue(task.title.strip())
            self.assertIsInstance(task.due_time, datetime)
            self.assertTrue(task.external_id)  # 同步去重依赖 external_id

    def test_external_ids_are_unique(self) -> None:
        ext_ids = [t.external_id for t in self.tasks]
        self.assertEqual(len(ext_ids), len(set(ext_ids)))

    def test_known_item_round_trips(self) -> None:
        by_ext = {t.external_id: t for t in self.tasks}
        self.assertIn("bb_ddl_1001", by_ext)
        first = by_ext["bb_ddl_1001"]
        self.assertEqual(first.due_time, datetime(2026, 6, 5, 23, 59))
        self.assertIn("编译原理", first.description)

    def test_tolerates_mixed_date_formats(self) -> None:
        by_ext = {t.external_id: t for t in self.tasks}
        # 斜杠日期
        self.assertEqual(by_ext["bb_ddl_1003"].due_time, datetime(2026, 6, 12, 14, 0))
        # 仅日期（无时间）
        self.assertEqual(by_ext["bb_ddl_1005"].due_time, datetime(2026, 6, 3, 0, 0))


class TestMockScheduleStructure(unittest.TestCase):
    """mock_schedule.html 结构校验（ScheduleParser 落地前的占位保障）。"""

    REQUIRED_FIELDS = (
        ".course",
        ".course-external-id",
        ".weekday",
        ".start-time",
        ".end-time",
        ".location",
        ".slot-type",
        ".start-week",
        ".end-week",
        ".week-type",
    )

    def setUp(self) -> None:
        self.soup = BeautifulSoup(_read(MOCK_SCHEDULE_PATH), "lxml")
        self.items = self.soup.select(".schedule-item")

    def test_has_schedule_items(self) -> None:
        self.assertGreaterEqual(len(self.items), 1)

    def test_each_item_has_external_id_and_required_fields(self) -> None:
        for item in self.items:
            self.assertTrue(item.get("data-external-id"))
            for selector in self.REQUIRED_FIELDS:
                node = item.select_one(selector)
                self.assertIsNotNone(
                    node, f"schedule-item 缺少 {selector}"
                )
                self.assertTrue(node.get_text(strip=True), f"{selector} 为空")

    def test_weekday_values_in_range(self) -> None:
        for item in self.items:
            weekday = int(item.select_one(".weekday").get_text(strip=True))
            self.assertIn(weekday, range(1, 8))


class TestMockExamsStructure(unittest.TestCase):
    """mock_exams.html 结构校验（ExamParser 落地前的占位保障）。"""

    REQUIRED_FIELDS = (
        ".name",
        ".course",
        ".course-external-id",
        ".start-time",
        ".end-time",
        ".location",
        ".exam-type",
    )

    def setUp(self) -> None:
        self.soup = BeautifulSoup(_read(MOCK_EXAMS_PATH), "lxml")
        self.items = self.soup.select(".exam-item")

    def test_has_exam_items(self) -> None:
        self.assertGreaterEqual(len(self.items), 1)

    def test_each_item_has_external_id_and_required_fields(self) -> None:
        for item in self.items:
            self.assertTrue(item.get("data-external-id"))
            for selector in self.REQUIRED_FIELDS:
                node = item.select_one(selector)
                self.assertIsNotNone(node, f"exam-item 缺少 {selector}")
                self.assertTrue(node.get_text(strip=True), f"{selector} 为空")

    def test_exam_type_is_valid(self) -> None:
        valid = {"midterm", "final", "quiz", "other"}
        for item in self.items:
            exam_type = item.select_one(".exam-type").get_text(strip=True)
            self.assertIn(exam_type, valid)


if __name__ == "__main__":
    unittest.main()
