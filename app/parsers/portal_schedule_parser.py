"""Parse PKU Portal course-table HTML into schedule slot dicts.

Each <td id="{day}{period}"> cell may contain one or more course entries:
  课程名(主)
  上课信息：X-Y周 每周/单周/双周 教室  教师：name [备注：...]
  考试信息：...
"""
from __future__ import annotations

import re
from datetime import time
from typing import Optional

from bs4 import BeautifulSoup

_DAY_MAP = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}

# Period number (1-12) → (start_time, end_time), mirroring ScheduleWidget.PERIODS
_PERIOD_TIMES: dict[int, tuple[time, time]] = {
    1:  (time(8,  0),  time(8,  50)),
    2:  (time(9,  0),  time(9,  50)),
    3:  (time(10, 10), time(11, 0)),
    4:  (time(11, 10), time(12, 0)),
    5:  (time(13, 0),  time(13, 50)),
    6:  (time(14, 0),  time(14, 50)),
    7:  (time(15, 10), time(16, 0)),
    8:  (time(16, 10), time(17, 0)),
    9:  (time(17, 10), time(18, 0)),
    10: (time(18, 40), time(19, 30)),
    11: (time(19, 40), time(20, 30)),
    12: (time(20, 40), time(21, 30)),
}

_WEEK_TYPE_MAP = {"每周": "all", "单周": "odd", "双周": "even"}

# Pattern for each course entry inside a cell
# Group 1: course name; Group 2: week range; Group 3: week type; Group 4: location (may be empty)
_INFO_RE = re.compile(
    r"上课信息[：:]"
    r"(\d+)-(\d+)周\s+"          # start_week - end_week
    r"(每周|单周|双周)\s*"         # week_type
    r"([^\s　]*)\s*"               # location (may be empty or classroom)
    r"教师[：:]([^\n备注]*)"       # teacher
)


def parse_portal_html(html: str) -> list[dict]:
    """Return a list of schedule-slot dicts from PKU Portal course table HTML."""
    soup = BeautifulSoup(html, "lxml")
    slots: list[dict] = []

    for td in soup.find_all("td", id=True):
        cell_id: str = td["id"]
        day_str = re.match(r"([a-z]+)(\d+)", cell_id)
        if day_str is None:
            continue
        day_abbr, period_str = day_str.group(1), day_str.group(2)
        weekday = _DAY_MAP.get(day_abbr)
        period = int(period_str) if period_str.isdigit() else None
        if weekday is None or period is None or period not in _PERIOD_TIMES:
            continue

        text = td.get_text(separator="\n", strip=True)
        if not text:
            continue

        for entry in _split_entries(text):
            slot = _parse_entry(entry, weekday, period)
            if slot:
                slots.append(slot)

    return slots


def _split_entries(text: str) -> list[str]:
    """Split a cell's text into individual course entries."""
    # Each entry starts with a course name line (ends with (主) or similar)
    # Split on lines that look like course name headers
    entries: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # A new course entry starts when we see a line containing "上课信息" or
        # a line that ends with "(主)" or similar and is NOT an info line
        if current and _is_course_name_line(line):
            entries.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("\n".join(current))
    return entries


def _is_course_name_line(line: str) -> bool:
    """Return True if line looks like a course name (not an info line)."""
    if line.startswith("上课信息") or line.startswith("考试信息"):
        return False
    return bool(re.search(r"\(主\)", line) or (len(line) > 1 and not re.match(r"^\d", line) and "教师" not in line and "周" not in line[:4]))


def _parse_entry(text: str, weekday: int, period: int) -> Optional[dict]:
    """Parse a single course entry text into a slot dict."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    # First line is the course name
    course_name = re.sub(r"\(主\)$", "", lines[0]).strip()
    if not course_name:
        return None

    # Find 上课信息 line
    info_line = next((l for l in lines if l.startswith("上课信息")), "")
    m = _INFO_RE.search(info_line)
    if m is None:
        # Minimal fallback: use period times with no week constraints
        start_t, end_t = _PERIOD_TIMES[period]
        return {
            "title": course_name,
            "weekday": weekday,
            "start_time": start_t.strftime("%H:%M"),
            "end_time": end_t.strftime("%H:%M"),
            "location": "",
            "slot_type": "lecture",
            "start_week": 1,
            "end_week": 16,
            "week_type": "all",
        }

    start_week = int(m.group(1))
    end_week = int(m.group(2))
    week_type = _WEEK_TYPE_MAP.get(m.group(3), "all")
    location = m.group(4).strip()

    start_t, end_t = _PERIOD_TIMES[period]
    return {
        "title": course_name,
        "weekday": weekday,
        "start_time": start_t.strftime("%H:%M"),
        "end_time": end_t.strftime("%H:%M"),
        "location": location,
        "slot_type": "lecture",
        "start_week": start_week,
        "end_week": end_week,
        "week_type": week_type,
    }
