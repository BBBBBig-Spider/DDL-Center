"""Parse teaching-site schedule data into ScheduleSlot objects."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import time
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schedule_slot import ScheduleSlot
from app.network.network_errors import ParseError
from app.parsers._common import coerce_external_id, coerce_str


class ScheduleParser:
    JSON_ITEMS_KEYS = ("items", "schedule", "slots", "data")
    HTML_ITEM_SELECTOR = "tr.schedule-item, div.schedule-item, li.schedule-item"
    VALID_WEEK_TYPES = {"all", "odd", "even"}
    VALID_SLOT_TYPES = {"lecture", "lab", "tutorial", "custom", "free"}
    PERIOD_TIMES = [
        (time(8, 0), time(8, 50)),
        (time(9, 0), time(9, 50)),
        (time(10, 10), time(11, 0)),
        (time(11, 10), time(12, 0)),
        (time(13, 0), time(13, 50)),
        (time(14, 0), time(14, 50)),
        (time(15, 10), time(16, 0)),
        (time(16, 10), time(17, 0)),
        (time(17, 10), time(18, 0)),
        (time(18, 40), time(19, 30)),
        (time(19, 40), time(20, 30)),
        (time(20, 40), time(21, 30)),
    ]

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
                raise ParseError(f"JSON object must contain one of: {', '.join(self.JSON_ITEMS_KEYS)}")
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
        if slots:
            return self._dedupe(slots)
        return self._dedupe(self._parse_table_schedule(soup))

    def _build_slot_from_dict(self, entry: dict) -> Optional[ScheduleSlot]:
        title = coerce_str(entry.get("title") or entry.get("course") or entry.get("name"))
        weekday = self._parse_int(entry.get("weekday"))
        start_time = self._parse_time(entry.get("start_time") or entry.get("startTime"))
        end_time = self._parse_time(entry.get("end_time") or entry.get("endTime"))
        if not title or weekday is None or start_time is None or end_time is None:
            return None
        if not 1 <= weekday <= 7 or end_time <= start_time:
            return None

        slot_type = self._normalize_choice(entry.get("slot_type") or entry.get("slotType"), self.VALID_SLOT_TYPES, "lecture")
        week_type = self._normalize_choice(entry.get("week_type") or entry.get("weekType"), self.VALID_WEEK_TYPES, "all")
        start_week = self._parse_int(entry.get("start_week") or entry.get("startWeek")) or 1
        end_week = self._parse_int(entry.get("end_week") or entry.get("endWeek")) or start_week
        if start_week < 1 or end_week < start_week:
            return None

        course_external_id = coerce_str(entry.get("course_external_id") or entry.get("courseId"))
        course_name = coerce_str(entry.get("course_name") or entry.get("course"))
        raw_payload = json.dumps(
            {"course_external_id": course_external_id, "course_name": course_name or title, "raw": entry},
            ensure_ascii=False,
        )

        slot = ScheduleSlot(
            title=title,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            location=coerce_str(entry.get("location")),
            slot_type=slot_type,
            start_week=start_week,
            end_week=end_week,
            week_type=week_type,
            source="sync",
            external_id=coerce_external_id(entry.get("external_id") or entry.get("id")) or self._external_id(title, weekday, start_time, end_time),
        )
        slot.raw_payload = raw_payload
        return slot

    def _build_slot_from_html(self, item: Tag) -> Optional[ScheduleSlot]:
        entry = {
            "title": self._extract_text(item, ".title, .course, .name"),
            "course_external_id": self._extract_text(item, ".course-external-id"),
            "course_name": self._extract_text(item, ".course, .name"),
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

    def _parse_table_schedule(self, soup: BeautifulSoup) -> list[ScheduleSlot]:
        slots: list[ScheduleSlot] = []
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            weekday_columns = self._weekday_columns(rows)
            if not weekday_columns:
                continue
            occupied: dict[tuple[int, int], bool] = {}
            period_counter = 0
            for row_index, row in enumerate(rows[1:], start=1):
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                row_text = row.get_text(" ", strip=True)
                row_period = self._period_from_text(row_text)
                if row_period is not None and 1 <= row_period <= 12:
                    period_counter = row_period
                elif period_counter == 0:
                    # No period header row seen yet — fall back to row index but
                    # cap so we never index beyond PERIOD_TIMES.
                    period_counter = row_index if 1 <= row_index <= 12 else 0
                # If neither branch produced a valid period, skip this row
                # without incrementing — unmarked filler rows must not push
                # the counter past 12 and silently drop the rest of the table.
                if not 1 <= period_counter <= 12:
                    continue

                visual_col = 0
                for cell in cells:
                    while occupied.get((row_index, visual_col)):
                        visual_col += 1
                    colspan = self._parse_int(cell.get("colspan")) or 1
                    rowspan = self._parse_int(cell.get("rowspan")) or 1
                    weekday = weekday_columns.get(visual_col)
                    if weekday is not None:
                        slots.extend(self._slots_from_cell(cell, weekday, period_counter, rowspan))
                    for r in range(row_index, row_index + rowspan):
                        for c in range(visual_col, visual_col + colspan):
                            occupied[(r, c)] = True
                    visual_col += colspan
        return slots

    def _weekday_columns(self, rows: list[Tag]) -> dict[int, int]:
        weekday_columns: dict[int, int] = {}
        for row in rows[:3]:
            visual_col = 0
            for cell in row.find_all(["td", "th"]):
                text = cell.get_text(" ", strip=True)
                weekday = self._weekday_from_text(text)
                colspan = self._parse_int(cell.get("colspan")) or 1
                if weekday is not None:
                    for offset in range(colspan):
                        weekday_columns[visual_col + offset] = weekday
                visual_col += colspan
            if weekday_columns:
                return weekday_columns
        return {}

    def _slots_from_cell(self, cell: Tag, weekday: int, start_period: int, rowspan: int) -> list[ScheduleSlot]:
        text = cell.get_text("\n", strip=True)
        text = self._clean_cell_text(text)
        if not text or self._is_empty_cell(text):
            return []

        blocks = [block.strip() for block in re.split(r"\n{2,}|;|；", text) if block.strip()]
        if not blocks:
            blocks = [text]

        slots: list[ScheduleSlot] = []
        for block in blocks:
            title, location = self._parse_title_location(block)
            if not title or self._is_empty_cell(title):
                continue
            start_week, end_week = self._parse_week_range(block)
            week_type = self._parse_week_type(block)
            start_time, end_time = self._period_range_to_time(start_period, start_period + max(rowspan, 1) - 1)
            raw = {"text": block, "weekday": weekday, "start_period": start_period, "rowspan": rowspan}
            slot = ScheduleSlot(
                title=title,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                location=location,
                slot_type="lecture",
                start_week=start_week,
                end_week=end_week,
                week_type=week_type,
                source="sync",
                external_id=self._external_id(title, weekday, start_time, end_time),
            )
            slot.raw_payload = json.dumps(
                {"course_external_id": self._external_id(title, 0, start_time, end_time)[:32], "course_name": title, "raw": raw},
                ensure_ascii=False,
            )
            slots.append(slot)
        return slots

    @staticmethod
    def _clean_cell_text(text: str) -> str:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _is_empty_cell(text: str) -> bool:
        compact = text.strip().lower()
        return compact in {"", "-", "--", "无", "none", " "}

    @staticmethod
    def _parse_title_location(text: str) -> tuple[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else text.strip()
        title = re.sub(r"\s*\(?\d+\s*-\s*\d+周.*$", "", title).strip()
        title = re.sub(r"\s*第?\d+\s*-\s*\d+节.*$", "", title).strip()
        location = ""
        for line in lines[1:]:
            if any(key in line for key in ("楼", "馆", "教室", "校区", "地点", "室")):
                location = re.sub(r"^(地点|上课地点)[:：]?", "", line).strip()
                break
        return title[:80], location[:80]

    @staticmethod
    def _parse_week_range(text: str) -> tuple[int, int]:
        match = re.search(r"(\d{1,2})\s*[-~－—]\s*(\d{1,2})\s*周", text)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"第?\s*(\d{1,2})\s*周", text)
        if match:
            week = int(match.group(1))
            return week, week
        return 1, 16

    @staticmethod
    def _parse_week_type(text: str) -> str:
        if "单周" in text:
            return "odd"
        if "双周" in text:
            return "even"
        return "all"

    def _period_range_to_time(self, start_period: int, end_period: int) -> tuple[time, time]:
        start_index = max(1, min(12, start_period)) - 1
        end_index = max(1, min(12, end_period)) - 1
        return self.PERIOD_TIMES[start_index][0], self.PERIOD_TIMES[end_index][1]

    @staticmethod
    def _weekday_from_text(text: str) -> Optional[int]:
        mapping = {
            "周一": 1, "星期一": 1, "一": 1,
            "周二": 2, "星期二": 2, "二": 2,
            "周三": 3, "星期三": 3, "三": 3,
            "周四": 4, "星期四": 4, "四": 4,
            "周五": 5, "星期五": 5, "五": 5,
            "周六": 6, "星期六": 6, "六": 6,
            "周日": 7, "星期日": 7, "星期天": 7, "日": 7, "天": 7,
        }
        compact = text.replace(" ", "")
        for key, value in mapping.items():
            if key in compact:
                return value
        return None

    @staticmethod
    def _period_from_text(text: str) -> Optional[int]:
        match = re.search(r"第?\s*(\d{1,2})\s*节", text)
        if match:
            value = int(match.group(1))
            return value if 1 <= value <= 12 else None
        match = re.search(r"^\s*(\d{1,2})\s*$", text)
        if match:
            value = int(match.group(1))
            return value if 1 <= value <= 12 else None
        return None

    @staticmethod
    def _extract_text(parent: Tag, selector: str) -> str:
        node = parent.select_one(selector)
        return "" if node is None else node.get_text(strip=True)

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
        parts = text.split(":")
        try:
            if len(parts) == 2:
                return time(int(parts[0]), int(parts[1]))
            if len(parts) == 3:
                return time(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None
        return None

    @staticmethod
    def _normalize_choice(value: Any, valid: set[str], default: str) -> str:
        text = value.strip().lower() if isinstance(value, str) else ""
        return text if text in valid else default

    @staticmethod
    def _external_id(title: str, weekday: int, start_time: time, end_time: time) -> str:
        digest = hashlib.sha256(f"{title}|{weekday}|{start_time}|{end_time}".encode("utf-8")).hexdigest()
        return f"schedule-{digest[:16]}"

    @staticmethod
    def _dedupe(slots: list[ScheduleSlot]) -> list[ScheduleSlot]:
        seen: set[str] = set()
        result: list[ScheduleSlot] = []
        for slot in slots:
            key = slot.external_id or f"{slot.title}|{slot.weekday}|{slot.start_time}|{slot.end_time}"
            if key in seen:
                continue
            seen.add(key)
            result.append(slot)
        return result
