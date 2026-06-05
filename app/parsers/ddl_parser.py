"""app/parsers/ddl_parser.py

Parse the PKU Blackboard DDL (assignment) page into Task objects.

Signature follows the architecture doc:
    DDLParser.parse(html_or_json: str) -> list[Task]

Accepts:
- HTML strings (real Blackboard pages, once a real sample is captured).
- JSON strings (used by mock data / tests / future structured endpoints).

The parser does **not** touch the database. Course resolution
(course_external_id → course_id) is the responsibility of SyncManager,
which calls CourseRepository.find_by_external_id on the parsed result.

The HTML branch uses assumed CSS selectors (.deadline-item, .title,
.due-time, .course, .course-external-id, .kind, data-external-id).
These selectors are a placeholder — once `data/mock_ddl.html` is captured
by `scripts/probe_teaching_site.py`, the selectors should be reviewed
against the real DOM.
"""
from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime
from typing import Any, List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.task import Task
from app.network.network_errors import ParseError


class DDLParser:
    """Parse DDL listings (HTML or JSON) into Task objects."""

    DATETIME_FORMATS = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    )

    JSON_ITEMS_KEYS = ("items", "ddls", "assignments", "data")
    HTML_ITEM_SELECTOR = "div.deadline-item, li.deadline-item"

    def parse(self, html_or_json: str) -> List[Task]:
        """Entry point. Dispatches to JSON or HTML branch based on input shape."""
        if not isinstance(html_or_json, str):
            raise TypeError("html_or_json must be str")

        text = html_or_json.strip()
        if not text:
            return []

        if self._looks_like_json(text):
            return self._parse_json(text)
        return self._parse_html(text)

    @staticmethod
    def _looks_like_json(text: str) -> bool:
        return text[:1] in ("[", "{")

    def _parse_json(self, text: str) -> List[Task]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON payload: {exc}") from exc

        if isinstance(data, list):
            items: Any = data
        elif isinstance(data, dict):
            items = None
            for key in self.JSON_ITEMS_KEYS:
                if key in data:
                    items = data[key]
                    break
            if items is None:
                raise ParseError(
                    f"JSON object must contain one of: {', '.join(self.JSON_ITEMS_KEYS)}"
                )
        else:
            raise ParseError("JSON payload must be a list or object")

        if not isinstance(items, list):
            raise ParseError("DDL items must be a list")

        tasks: List[Task] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            task = self._build_task_from_dict(entry)
            if task is not None:
                tasks.append(task)
        return tasks

    def _build_task_from_dict(self, entry: dict) -> Optional[Task]:
        title = entry.get("title")
        due_raw = (
            entry.get("due_time")
            or entry.get("dueTime")
            or entry.get("deadline")
        )
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(due_raw, str) or not due_raw.strip():
            return None
        due_time = self._parse_datetime(due_raw)
        if due_time is None:
            return None

        external_id = self._coerce_external_id(
            entry.get("external_id") or entry.get("id")
        )

        course_name = self._coerce_str(
            entry.get("course_name") or entry.get("course")
        )
        course_external_id = self._coerce_str(
            entry.get("course_external_id") or entry.get("courseId")
        )
        kind = self._coerce_str(entry.get("kind") or entry.get("type"))

        description = self._format_description(kind, course_name)
        raw_payload = json.dumps(
            {
                "course_external_id": course_external_id,
                "kind": kind,
                "raw": entry,
            },
            ensure_ascii=False,
        )

        return Task(
            title=title.strip(),
            due_time=due_time,
            description=description,
            source="sync",
            external_id=external_id,
            raw_payload=raw_payload,
        )

    def _parse_html(self, text: str) -> List[Task]:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:
            raise ParseError(f"Failed to parse HTML: {exc}") from exc

        items = soup.select(self.HTML_ITEM_SELECTOR)
        tasks: List[Task] = []
        for item in items:
            task = self._build_task_from_html(item)
            if task is not None:
                tasks.append(task)
        if tasks:
            return tasks

        for item in soup.select("li.liItem, div.liItem"):
            task = self._build_task_from_blackboard_item(item, soup)
            if task is not None:
                tasks.append(task)
        return tasks

    def _build_task_from_html(self, item: Tag) -> Optional[Task]:
        title = self._extract_text(item, ".title")
        due_raw = self._extract_text(item, ".due-time, .deadline")
        if not title or not due_raw:
            return None
        due_time = self._parse_datetime(due_raw)
        if due_time is None:
            return None

        external_id_attr = item.get("data-external-id")
        external_id = self._coerce_external_id(external_id_attr)

        course_name = self._extract_text(item, ".course")
        course_external_id = self._extract_text(item, ".course-external-id")
        kind = self._extract_text(item, ".kind, .type")

        description = self._format_description(kind, course_name)
        raw_payload = json.dumps(
            {
                "course_external_id": course_external_id,
                "course_name": course_name,
                "kind": kind,
                "raw": str(item),
            },
            ensure_ascii=False,
        )

        return Task(
            title=title,
            due_time=due_time,
            description=description,
            source="sync",
            external_id=external_id,
            raw_payload=raw_payload,
        )

    def _build_task_from_blackboard_item(
        self,
        item: Tag,
        soup: BeautifulSoup,
    ) -> Optional[Task]:
        title = self._extract_text(
            item,
            "h3, h4, .item h3, .item h4, .itemTitle, .vtbegenerated h3, a",
        )
        text = item.get_text(" ", strip=True)
        if not title:
            return None

        due_time = self._parse_blackboard_due_time(text)
        if due_time is None:
            return None

        course_name = self._course_name_from_title(soup)
        external_id = self._blackboard_external_id(item, title, due_time)
        raw_payload = json.dumps(
            {
                "course_name": course_name,
                "kind": "assignment",
                "raw": str(item),
            },
            ensure_ascii=False,
        )
        return Task(
            title=title,
            due_time=due_time,
            description=self._format_description("assignment", course_name),
            source="sync",
            external_id=external_id,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _extract_text(parent: Tag, selector: str) -> str:
        node = parent.select_one(selector)
        if node is None:
            return ""
        return node.get_text(strip=True)

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value)

    @staticmethod
    def _coerce_external_id(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return str(value)

    @staticmethod
    def _format_description(kind: str, course_name: str) -> str:
        parts = []
        if kind:
            parts.append(f"[{kind}]")
        if course_name:
            parts.append(course_name)
        return " ".join(parts)

    def _parse_datetime(self, raw: str) -> Optional[datetime]:
        s = raw.strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
        for fmt in self.DATETIME_FORMATS:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    def _parse_blackboard_due_time(self, text: str) -> Optional[datetime]:
        compact = re.sub(r"\s+", "", text)
        patterns = (
            r"(?:提交)?截止(?:时间)?[:：]?(?:北京时间)?(?P<month>\d{1,2})月(?P<day>\d{1,2})日(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
            r"(?:提交)?截止(?:时间)?[:：]?(?:北京时间)?(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
            r"(?:提交)?截止(?:时间)?[:：]?(?P<year>\d{4})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})[T ]?(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
        )
        for pattern in patterns:
            match = re.search(pattern, compact, flags=re.IGNORECASE)
            if not match:
                continue
            parts = match.groupdict()
            year = int(parts.get("year") or datetime.now().year)
            try:
                return datetime(
                    year,
                    int(parts["month"]),
                    int(parts["day"]),
                    int(parts["hour"]),
                    int(parts["minute"]),
                )
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _course_name_from_title(soup: BeautifulSoup) -> str:
        title = soup.title.get_text(strip=True) if soup.title else ""
        if "–" in title:
            return title.split("–", 1)[1].strip()
        if "-" in title:
            return title.split("-", 1)[1].strip()
        return ""

    @staticmethod
    def _blackboard_external_id(item: Tag, title: str, due_time: datetime) -> str:
        candidates = [
            item.get("id"),
            item.get("data-content-id"),
            item.get("data-external-id"),
        ]
        for node in item.find_all(True):
            candidates.extend([node.get("id"), node.get("href"), node.get("name")])
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()[:180]
        digest = hashlib.sha256(f"{title}|{due_time.isoformat()}".encode("utf-8")).hexdigest()
        return f"blackboard-{digest[:16]}"
