"""Parse PKU Blackboard DDL pages into Task objects."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.task import Task
from app.network.network_errors import ParseError


class DDLParser:
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
    BLACKBOARD_ITEM_SELECTOR = (
        "li.liItem, div.liItem, "
        "li[id^='contentListItem:'], div[id^='contentListItem:']"
    )

    def parse(self, html_or_json: str) -> list[Task]:
        if not isinstance(html_or_json, str):
            raise TypeError("html_or_json must be str")
        text = html_or_json.strip()
        if not text:
            return []
        if text[:1] in ("[", "{"):
            return self._parse_json(text)
        return self._parse_html(text)

    def _parse_json(self, text: str) -> list[Task]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON payload: {exc}") from exc

        if isinstance(data, list):
            items: Any = data
        elif isinstance(data, dict):
            items = next((data[key] for key in self.JSON_ITEMS_KEYS if key in data), None)
            if items is None:
                raise ParseError(f"JSON object must contain one of: {', '.join(self.JSON_ITEMS_KEYS)}")
        else:
            raise ParseError("JSON payload must be a list or object")

        if not isinstance(items, list):
            raise ParseError("DDL items must be a list")

        tasks: list[Task] = []
        for entry in items:
            if isinstance(entry, dict):
                task = self._build_task_from_dict(entry)
                if task is not None:
                    tasks.append(task)
        return tasks

    def _build_task_from_dict(self, entry: dict) -> Optional[Task]:
        title = self._coerce_str(entry.get("title"))
        due_raw = self._coerce_str(entry.get("due_time") or entry.get("dueTime") or entry.get("deadline"))
        if not title or not due_raw:
            return None
        due_time = self._parse_datetime(due_raw)
        if due_time is None:
            return None

        course_name = self._coerce_str(entry.get("course_name") or entry.get("course"))
        course_external_id = self._coerce_str(entry.get("course_external_id") or entry.get("courseId"))
        kind = self._coerce_str(entry.get("kind") or entry.get("type") or "assignment")
        external_id = self._coerce_external_id(entry.get("external_id") or entry.get("id"))
        if external_id is None:
            external_id = self._fallback_external_id(title, due_time, course_external_id)

        raw_payload = json.dumps(
            {
                "course_external_id": course_external_id,
                "course_name": course_name,
                "kind": kind,
                "raw": entry,
            },
            ensure_ascii=False,
        )
        return Task(
            title=title,
            due_time=due_time,
            description=self._format_description(kind, course_name),
            source="sync",
            external_id=external_id,
            raw_payload=raw_payload,
        )

    def _parse_html(self, text: str) -> list[Task]:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:
            raise ParseError(f"Failed to parse HTML: {exc}") from exc

        tasks: list[Task] = []
        for item in soup.select(self.HTML_ITEM_SELECTOR):
            task = self._build_task_from_structured_html(item)
            if task is not None:
                tasks.append(task)
        if tasks:
            return self._dedupe(tasks)

        for item in soup.select(self.BLACKBOARD_ITEM_SELECTOR):
            task = self._build_task_from_blackboard_item(item, soup)
            if task is not None:
                tasks.append(task)
        if tasks:
            return self._dedupe(tasks)

        # Concatenated Blackboard pages can create invalid multi-document HTML.
        # Slice contentListItem blocks as a fallback.
        for item_html in re.findall(
            r'(<li[^>]+id=["\']contentListItem:[\s\S]*?</li>)',
            text,
            flags=re.IGNORECASE,
        ):
            item_soup = BeautifulSoup(item_html, "lxml")
            item = item_soup.select_one("li")
            if item is None:
                continue
            task = self._build_task_from_blackboard_item(item, item_soup)
            if task is not None:
                tasks.append(task)
        return self._dedupe(tasks)

    def _build_task_from_structured_html(self, item: Tag) -> Optional[Task]:
        title = self._extract_text(item, ".title")
        due_raw = self._extract_text(item, ".due-time, .deadline")
        due_time = self._parse_datetime(due_raw) if due_raw else None
        if not title or due_time is None:
            return None

        course_name = self._extract_text(item, ".course")
        course_external_id = (
            self._extract_text(item, ".course-external-id")
            or self._extract_course_external_id(str(item))
        )
        kind = self._extract_text(item, ".kind, .type") or "assignment"
        external_id = self._coerce_external_id(item.get("data-external-id")) or self._blackboard_external_id(item, title, due_time)
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
            description=self._format_description(kind, course_name),
            source="sync",
            external_id=external_id,
            raw_payload=raw_payload,
        )

    def _build_task_from_blackboard_item(self, item: Tag, soup: BeautifulSoup) -> Optional[Task]:
        title = self._extract_text(item, "h3, h4, .item h3, .item h4, .itemTitle, .vtbegenerated h3, a")
        text = item.get_text(" ", strip=True)
        if not title:
            return None
        due_time = self._parse_blackboard_due_time(text)
        if due_time is None:
            return None

        raw_html = str(item)
        course_wrapper = item.find_parent(attrs={"data-course-external-id": True})
        wrapped_course_id = self._coerce_str(course_wrapper.get("data-course-external-id")) if course_wrapper else ""
        wrapped_course_name = self._coerce_str(course_wrapper.get("data-course-name")) if course_wrapper else ""
        course_external_id = wrapped_course_id or self._extract_course_external_id(raw_html) or self._extract_course_external_id(str(soup))
        course_name = wrapped_course_name or self._course_name_from_title(soup)
        external_id = self._blackboard_external_id(item, title, due_time)
        raw_payload = json.dumps(
            {
                "course_external_id": course_external_id,
                "course_name": course_name,
                "kind": "assignment",
                "raw": raw_html,
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

    def _parse_datetime(self, raw: str) -> Optional[datetime]:
        text = raw.strip()
        if not text:
            return None
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

    def _parse_blackboard_due_time(self, text: str) -> Optional[datetime]:
        compact = re.sub(r"\s+", "", text)
        patterns = (
            r"(?:提交)?(?:截止|结束)(?:时间)?(?:为|至|到)?[:：]?(?:北京时间)?(?P<month>\d{1,2})月(?P<day>\d{1,2})日?(?:晚|上午|下午)?(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
            r"(?:提交)?(?:截止|结束)(?:时间)?(?:为|至|到)?[:：]?(?:北京时间)?(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日?(?:晚|上午|下午)?(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
            r"(?:提交)?(?:截止|结束)(?:时间)?(?:为|至|到)?[:：]?(?P<year>\d{4})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})[T ]?(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
            r"(?:deadline|due)[:：]?(?P<year>\d{4})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})[T ]?(?P<hour>\d{1,2})[:：](?P<minute>\d{2})",
        )
        for pattern in patterns:
            match = re.search(pattern, compact, flags=re.IGNORECASE)
            if not match:
                continue
            parts = match.groupdict()
            now = datetime.now()
            has_explicit_year = bool(parts.get("year"))
            year = int(parts.get("year") or now.year)
            hour = int(parts["hour"])
            matched_text = match.group(0)
            if ("下午" in matched_text or "晚" in matched_text) and hour < 12:
                hour += 12
            try:
                due_time = datetime(year, int(parts["month"]), int(parts["day"]), hour, int(parts["minute"]))
            except (TypeError, ValueError):
                return None
            if not has_explicit_year and due_time < now - timedelta(days=30):
                try:
                    bumped = due_time.replace(year=due_time.year + 1)
                    # Only accept the bump if the result is within 8 months from
                    # now — avoids pushing genuinely past-due dates into a future
                    # year when syncing mid-semester.
                    if bumped <= now + timedelta(days=240):
                        due_time = bumped
                except ValueError:
                    pass
            return due_time
        return None

    @staticmethod
    def _extract_course_external_id(html: str) -> str:
        patterns = (
            r"course_id=([^&'\"\s<>]+)",
            r"courseId=([^&'\"\s<>]+)",
            r"/courses/([^/'\"\s<>]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _course_name_from_title(soup: BeautifulSoup) -> str:
        title = soup.title.get_text(strip=True) if soup.title else ""
        for sep in ("–", "—", "-"):
            if sep in title:
                return title.split(sep, 1)[1].strip()
        return ""

    @staticmethod
    def _blackboard_external_id(item: Tag, title: str, due_time: datetime) -> str:
        candidates = [item.get("id"), item.get("data-content-id"), item.get("data-external-id")]
        for node in item.find_all(True):
            candidates.extend([node.get("id"), node.get("href"), node.get("name")])
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()[:180]
        return DDLParser._fallback_external_id(title, due_time, "")

    @staticmethod
    def _fallback_external_id(title: str, due_time: datetime, course_external_id: str) -> str:
        digest = hashlib.sha256(f"{course_external_id}|{title}|{due_time.isoformat()}".encode("utf-8")).hexdigest()
        return f"blackboard-{digest[:16]}"

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
    def _format_description(kind: str, course_name: str) -> str:
        parts = []
        if kind:
            parts.append(f"[{kind}]")
        if course_name:
            parts.append(course_name)
        return " ".join(parts)

    @staticmethod
    def _dedupe(tasks: list[Task]) -> list[Task]:
        seen: set[str] = set()
        result: list[Task] = []
        for task in tasks:
            key = task.external_id or f"{task.title}|{task.due_time.isoformat()}"
            if key in seen:
                continue
            seen.add(key)
            result.append(task)
        return result
