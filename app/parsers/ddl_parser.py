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
        raw_payload = str(item)

        return Task(
            title=title,
            due_time=due_time,
            description=description,
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
