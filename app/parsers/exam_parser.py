"""Parse teaching-site exam data into Exam objects."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.exam import Exam
from app.network.network_errors import ParseError


class ExamParser:
    JSON_ITEMS_KEYS = ("items", "exams", "tests", "data")
    HTML_ITEM_SELECTOR = "li.exam-item, div.exam-item, tr.exam-item"
    VALID_EXAM_TYPES = {"midterm", "final", "quiz", "other"}
    DATETIME_FORMATS = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    )

    def parse(self, html_or_json: str) -> list[Exam]:
        if not isinstance(html_or_json, str):
            raise TypeError("html_or_json must be str")
        text = html_or_json.strip()
        if not text:
            return []
        if text[:1] in ("[", "{"):
            return self._parse_json(text)
        return self._parse_html(text)

    def _parse_json(self, text: str) -> list[Exam]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid exam JSON payload: {exc}") from exc

        if isinstance(data, list):
            items: Any = data
        elif isinstance(data, dict):
            items = next((data[key] for key in self.JSON_ITEMS_KEYS if key in data), None)
            if items is None:
                raise ParseError(
                    f"JSON object must contain one of: {', '.join(self.JSON_ITEMS_KEYS)}"
                )
        else:
            raise ParseError("Exam JSON payload must be a list or object")

        if not isinstance(items, list):
            raise ParseError("Exam items must be a list")

        exams: list[Exam] = []
        for entry in items:
            if isinstance(entry, dict):
                exam = self._build_exam_from_dict(entry)
                if exam is not None:
                    exams.append(exam)
        return exams

    def _parse_html(self, text: str) -> list[Exam]:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:
            raise ParseError(f"Failed to parse exam HTML: {exc}") from exc

        exams: list[Exam] = []
        for item in soup.select(self.HTML_ITEM_SELECTOR):
            exam = self._build_exam_from_html(item)
            if exam is not None:
                exams.append(exam)
        return exams

    def _build_exam_from_dict(self, entry: dict) -> Optional[Exam]:
        name = self._coerce_str(entry.get("name") or entry.get("title"))
        start_time = self._parse_datetime(entry.get("start_time") or entry.get("startTime"))
        end_time = self._parse_datetime(entry.get("end_time") or entry.get("endTime"))
        if not name or start_time is None:
            return None
        if end_time is None:
            end_time = start_time + timedelta(hours=2)
        if end_time <= start_time:
            return None

        exam_type = self._normalize_exam_type(entry.get("exam_type") or entry.get("type"))
        raw_payload = json.dumps(
            {
                "course_external_id": self._coerce_str(
                    entry.get("course_external_id") or entry.get("courseId")
                ),
                "course_name": self._coerce_str(entry.get("course") or entry.get("course_name")),
                "raw": entry,
            },
            ensure_ascii=False,
        )

        return Exam(
            name=name,
            start_time=start_time,
            end_time=end_time,
            location=self._coerce_str(entry.get("location")),
            seat=self._coerce_str(entry.get("seat")),
            exam_type=exam_type,
            source="sync",
            external_id=self._coerce_external_id(entry.get("external_id") or entry.get("id")),
            raw_payload=raw_payload,
        )

    def _build_exam_from_html(self, item: Tag) -> Optional[Exam]:
        entry = {
            "name": self._extract_text(item, ".name, .title"),
            "course": self._extract_text(item, ".course"),
            "course_external_id": self._extract_text(item, ".course-external-id"),
            "start_time": self._extract_text(item, ".start-time"),
            "end_time": self._extract_text(item, ".end-time"),
            "location": self._extract_text(item, ".location"),
            "seat": self._extract_text(item, ".seat"),
            "exam_type": self._extract_text(item, ".exam-type, .type"),
            "external_id": item.get("data-external-id"),
        }
        return self._build_exam_from_dict(entry)

    @staticmethod
    def _extract_text(parent: Tag, selector: str) -> str:
        node = parent.select_one(selector)
        return "" if node is None else node.get_text(strip=True)

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else str(value)

    @staticmethod
    def _coerce_external_id(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = value.strip() if isinstance(value, str) else str(value)
        return text or None

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in self.DATETIME_FORMATS:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _normalize_exam_type(self, value: Any) -> str:
        text = value.strip().lower() if isinstance(value, str) else ""
        return text if text in self.VALID_EXAM_TYPES else "other"
