"""Parse teaching-site schedule data into ScheduleSlot objects."""
from __future__ import annotations

import json
from datetime import time
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schedule_slot import ScheduleSlot
from app.network.network_errors import ParseError


class ScheduleParser:
    JSON_ITEMS_KEYS = ("items", "schedule", "slots", "data")
    HTML_ITEM_SELECTOR = "tr.schedule-item, div.schedule-item, li.schedule-item"
    VALID_WEEK_TYPES = {"all", "odd", "even"}
    VALID_SLOT_TYPES = {"lecture", "lab", "tutorial", "custom", "free"}

    def parse(self, html_or_json: str) -> list[ScheduleSlot]:
        if not isinstance(html_or_json, str):
            raise TypeError("html_or_json must be str")
        text = html_or_json.strip()
        if not text:
            return []
        if text[:1] in ("[", "{"):
            return self._parse_json(text)
        return self._parse_html(text)

    def _parse_json(self, text: str) -> list[ScheduleSlot]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid schedule JSON payload: {exc}") from exc

        if isinstance(data, list):
            items: Any = data
        elif isinstance(data, dict):
            items = next((data[key] for key in self.JSON_ITEMS_KEYS if key in data), None)
            if items is None:
                raise ParseError(
                    f"JSON object must contain one of: {', '.join(self.JSON_ITEMS_KEYS)}"
                )
        else:
            raise ParseError("Schedule JSON payload must be a list or object")

        if not isinstance(items, list):
            raise ParseError("Schedule items must be a list")

        slots: list[ScheduleSlot] = []
        for entry in items:
            if isinstance(entry, dict):
                slot = self._build_slot_from_dict(entry)
                if slot is not None:
                    slots.append(slot)
        return slots

    def _parse_html(self, text: str) -> list[ScheduleSlot]:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:
            raise ParseError(f"Failed to parse schedule HTML: {exc}") from exc

        slots: list[ScheduleSlot] = []
        for item in soup.select(self.HTML_ITEM_SELECTOR):
            slot = self._build_slot_from_html(item)
            if slot is not None:
                slots.append(slot)
        return slots

    def _build_slot_from_dict(self, entry: dict) -> Optional[ScheduleSlot]:
        title = self._coerce_str(entry.get("title") or entry.get("course") or entry.get("name"))
        weekday = self._parse_int(entry.get("weekday"))
        start_time = self._parse_time(entry.get("start_time") or entry.get("startTime"))
        end_time = self._parse_time(entry.get("end_time") or entry.get("endTime"))
        if not title or weekday is None or start_time is None or end_time is None:
            return None
        if not 1 <= weekday <= 7 or end_time <= start_time:
            return None

        slot_type = self._normalize_choice(
            entry.get("slot_type") or entry.get("slotType"),
            self.VALID_SLOT_TYPES,
            "lecture",
        )
        week_type = self._normalize_choice(
            entry.get("week_type") or entry.get("weekType"),
            self.VALID_WEEK_TYPES,
            "all",
        )
        start_week = self._parse_int(entry.get("start_week") or entry.get("startWeek")) or 1
        end_week = self._parse_int(entry.get("end_week") or entry.get("endWeek")) or start_week
        if start_week < 1 or end_week < start_week:
            return None

        raw_payload = json.dumps(
            {
                "course_external_id": self._coerce_str(
                    entry.get("course_external_id") or entry.get("courseId")
                ),
                "raw": entry,
            },
            ensure_ascii=False,
        )

        slot = ScheduleSlot(
            title=title,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            location=self._coerce_str(entry.get("location")),
            slot_type=slot_type,
            start_week=start_week,
            end_week=end_week,
            week_type=week_type,
            source="sync",
            external_id=self._coerce_external_id(entry.get("external_id") or entry.get("id")),
        )
        slot.raw_payload = raw_payload
        return slot

    def _build_slot_from_html(self, item: Tag) -> Optional[ScheduleSlot]:
        entry = {
            "title": self._extract_text(item, ".title, .course, .name"),
            "course_external_id": self._extract_text(item, ".course-external-id"),
            "weekday": self._extract_text(item, ".weekday"),
            "start_time": self._extract_text(item, ".start-time"),
            "end_time": self._extract_text(item, ".end-time"),
            "location": self._extract_text(item, ".location"),
            "slot_type": self._extract_text(item, ".slot-type, .type"),
            "start_week": self._extract_text(item, ".start-week"),
            "end_week": self._extract_text(item, ".end-week"),
            "week_type": self._extract_text(item, ".week-type"),
            "external_id": item.get("data-external-id"),
        }
        return self._build_slot_from_dict(entry)

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

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        if isinstance(value, bool) or value is None:
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_time(value: Any) -> Optional[time]:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        try:
            return time.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                parts = text.split(":")
                if fmt == "%H:%M" and len(parts) == 2:
                    return time(int(parts[0]), int(parts[1]))
                if fmt == "%H:%M:%S" and len(parts) == 3:
                    return time(int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                continue
        return None

    @staticmethod
    def _normalize_choice(value: Any, valid: set[str], default: str) -> str:
        text = value.strip().lower() if isinstance(value, str) else ""
        return text if text in valid else default
