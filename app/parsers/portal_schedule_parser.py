"""Parse PKU Portal coursetable HTML into schedule slots, exams and exam-week range.

This is the parser used by the GUI "导入课表" dialog when the pasted content is
HTML. It works on the simplified DOM emitted by the portal's print-friendly
coursetable view: each course occupies a `<td id="{weekday}{period}">` cell
containing free-text lines like:

    高等数学(一班)
    上课信息：1-16周 每周 理教303 教师：张老师
    考试信息：2026-06-20 09:00-11:00 理教303

and a sibling text node carrying `考试周：YYYY-MM-DD 至 YYYY-MM-DD`.

Two entry points are exposed:

* `parse_portal_html(html) -> list[dict]` — slot dicts only (legacy contract).
* `parse_portal_import(html) -> dict` — `{slots, exams, exam_week_start,
  exam_week_end}` for the import dialog.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

# weekday id-prefix map used by the portal coursetable cells
_WEEKDAY_PREFIX = {
    "mon": 1, "tue": 2, "wed": 3, "thu": 4,
    "fri": 5, "sat": 6, "sun": 7,
}
_CELL_ID_RE = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)(\d{1,2})$", re.IGNORECASE)

# canonical period -> (start_time, end_time) in HH:MM, mirrors ScheduleParser.PERIOD_TIMES
_PERIOD_TIMES = [
    ("08:00", "08:50"),
    ("09:00", "09:50"),
    ("10:10", "11:00"),
    ("11:10", "12:00"),
    ("13:00", "13:50"),
    ("14:00", "14:50"),
    ("15:10", "16:00"),
    ("16:10", "17:00"),
    ("17:10", "18:00"),
    ("18:40", "19:30"),
    ("19:40", "20:30"),
    ("20:40", "21:30"),
]

_CLASS_SUFFIX_RE = re.compile(r"\s*[\(（][^()（）]*[\)）]\s*$")
_WEEK_RANGE_RE = re.compile(r"(\d{1,2})\s*[-~－—]\s*(\d{1,2})\s*周")
_SINGLE_WEEK_RE = re.compile(r"第?\s*(\d{1,2})\s*周")
_EXAM_LINE_RE = re.compile(
    r"(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})\s*[-~－—]\s*(\d{1,2}:\d{2})\s*([^\s].*)?"
)
# Compact PKU portal layout: "20260618 星期四 下午 二教105" — date is 8
# digits, the clock is replaced by a 时段 keyword (上午/下午/晚上/中午).
_EXAM_LINE_COMPACT_RE = re.compile(
    r"(?P<date>\d{8})"
    r"(?:\s*星期[一二三四五六七日天])?"
    r"\s*(?P<period>上午|下午|晚上|中午|早上|凌晨)"
    r"\s*(?P<location>[^<\n\r]+)?"
)
_PERIOD_TIME_WINDOWS = {
    "早上": ("08:00", "12:00"),
    "上午": ("08:00", "12:00"),
    "中午": ("12:00", "13:00"),
    "下午": ("13:00", "17:00"),
    "晚上": ("18:00", "22:00"),
    "凌晨": ("00:00", "06:00"),
}
_EXAM_WEEK_RE = re.compile(
    r"考试周[:：]?\s*(\d{4}-\d{1,2}-\d{1,2})\s*(?:至|到|-|~|—)\s*(\d{4}-\d{1,2}-\d{1,2})"
)


def parse_portal_html(html: str) -> list[dict]:
    """Return only the schedule-slot dicts (legacy contract used by older callers)."""
    parsed = parse_portal_import(html)
    return parsed["slots"]


def parse_portal_import(html: str) -> dict:
    """Return slots, exams and exam-week range parsed from a portal HTML page."""
    if not isinstance(html, str):
        raise TypeError("html must be str")

    soup = BeautifulSoup(html, "lxml")
    slots: list[dict] = []
    exams: list[dict] = []
    seen_exam_keys: set[tuple] = set()

    for cell in soup.find_all(attrs={"id": _CELL_ID_RE}):
        match = _CELL_ID_RE.match(cell.get("id", ""))
        if not match:
            continue
        weekday = _WEEKDAY_PREFIX[match.group(1).lower()]
        period = int(match.group(2))
        text = cell.get_text("\n", strip=True)
        if not text:
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = _CLASS_SUFFIX_RE.sub("", lines[0]).strip()
        if not title:
            continue

        schedule_line = next((ln for ln in lines if "上课信息" in ln), "")
        exam_line = next((ln for ln in lines if "考试信息" in ln), "")

        slot = _build_slot(title, weekday, period, schedule_line)
        if slot is not None:
            slots.append(slot)

        exam = _build_exam(title, exam_line)
        if exam is not None:
            # The same course shows up in many cells (one per period it
            # meets each week), so guard against duplicates by (course, time).
            key = (exam["course_name"], exam["start_time"])
            if key not in seen_exam_keys:
                seen_exam_keys.add(key)
                exams.append(exam)

    exam_week_start, exam_week_end = _extract_exam_week(soup)
    return {
        "slots": slots,
        "exams": exams,
        "exam_week_start": exam_week_start,
        "exam_week_end": exam_week_end,
    }


def _build_slot(title: str, weekday: int, period: int, info_line: str) -> Optional[dict]:
    if not 1 <= period <= len(_PERIOD_TIMES):
        return None
    start_time, end_time = _PERIOD_TIMES[period - 1]
    start_week, end_week = _parse_week_range(info_line)
    week_type = _parse_week_type(info_line)
    location = _extract_schedule_location(info_line)
    return {
        "title": title,
        "weekday": weekday,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "slot_type": "lecture",
        "start_week": start_week,
        "end_week": end_week,
        "week_type": week_type,
    }


def _build_exam(title: str, exam_line: str) -> Optional[dict]:
    if not exam_line:
        return None
    body = exam_line.split("：", 1)[-1] if "：" in exam_line else exam_line
    body = body.split(":", 1)[-1] if body == exam_line and ":" in exam_line else body
    body = body.strip()

    # Format A (legacy): "2026-06-20 09:00-11:00 理教303"
    match = _EXAM_LINE_RE.search(body)
    if match:
        date_str, start_clock, end_clock, location = match.groups()
        date_norm = _normalize_date(date_str)
        if date_norm is None:
            return None
        location = (location or "").strip()
        return {
            "name": f"{title}考试",
            "start_time": f"{date_norm}T{_pad_clock(start_clock)}",
            "end_time": f"{date_norm}T{_pad_clock(end_clock)}",
            "location": location,
            "exam_type": "final",
            "course_name": title,
        }

    # Format B (PKU portal compact): "20260618 星期四 下午 二教105"
    match = _EXAM_LINE_COMPACT_RE.search(body)
    if match:
        raw_date = match.group("date")
        period = match.group("period")
        location = (match.group("location") or "").strip()
        try:
            date_norm = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            datetime.strptime(date_norm, "%Y-%m-%d")
        except ValueError:
            return None
        start_clock, end_clock = _PERIOD_TIME_WINDOWS.get(period, ("09:00", "11:00"))
        return {
            "name": f"{title}考试",
            "start_time": f"{date_norm}T{_pad_clock(start_clock)}",
            "end_time": f"{date_norm}T{_pad_clock(end_clock)}",
            "location": location,
            "exam_type": "final",
            "course_name": title,
        }
    return None


def _parse_week_range(text: str) -> tuple[int, int]:
    if not text:
        return 1, 16
    match = _WEEK_RANGE_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = _SINGLE_WEEK_RE.search(text)
    if match:
        week = int(match.group(1))
        return week, week
    return 1, 16


def _parse_week_type(text: str) -> str:
    if "单周" in text:
        return "odd"
    if "双周" in text:
        return "even"
    return "all"


def _extract_schedule_location(text: str) -> str:
    """Pick a building/room token out of the 上课信息 line. Best effort, never raises."""
    if not text:
        return ""
    body = text.split("：", 1)[-1] if "：" in text else text
    body = re.sub(_WEEK_RANGE_RE, "", body)
    body = re.sub(_SINGLE_WEEK_RE, "", body)
    body = body.replace("每周", "").replace("单周", "").replace("双周", "")
    body = re.sub(r"教师\s*[:：][^\s]+", "", body)
    tokens = [tok for tok in re.split(r"\s+", body.strip()) if tok]
    for tok in tokens:
        if any(marker in tok for marker in ("楼", "馆", "教室", "校区", "室", "教")):
            return tok
    return tokens[0] if tokens else ""


def _extract_exam_week(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    text = soup.get_text(" ", strip=True)
    match = _EXAM_WEEK_RE.search(text)
    if not match:
        return None, None
    start = _normalize_date(match.group(1))
    end = _normalize_date(match.group(2))
    return start, end


def _normalize_date(value: str) -> Optional[str]:
    parts = value.split("-")
    if len(parts) != 3:
        return None
    try:
        y, m, d = (int(p) for p in parts)
    except ValueError:
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _pad_clock(value: str) -> str:
    h, _, m = value.partition(":")
    try:
        return f"{int(h):02d}:{int(m):02d}"
    except ValueError:
        return value
