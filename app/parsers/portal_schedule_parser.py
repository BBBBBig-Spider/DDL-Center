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

# "备注：..." trailers describe a *different* class (recitation / 习题课) with
# its own day / week-parity / location. We split this off before parsing the
# main lecture so that 双周/单周 markers inside the remark don't get mistaken
# for the main lecture's week parity.
_REMARK_SPLIT_RE = re.compile(r"\s*备注\s*[:：]")

# Recitation-slot patterns. Kept module-level so they compile once.
_RECITATION_PRESENT_RE = re.compile(r"习题课")
_RECITATION_WEEKTYPE_RE = re.compile(r"(每周|单周|双周)")
_RECITATION_WEEKDAY_RE = re.compile(r"周([一二三四五六日七天])")
_RECITATION_PERIOD_RE = re.compile(r"(\d{1,2})\s*[~\-～—]\s*(\d{1,2})\s*节")
_RECITATION_LOCATION_RE = re.compile(r"教室\s*[:：]\s*([^\s]+)")

# Chinese weekday char -> grid weekday (Monday=1 ... Sunday=7); the portal
# uses both 七 and 日/天 to mean Sunday.
_CHINESE_WEEKDAY = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "七": 7, "天": 7}


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
    # Recitations described in 备注 trailers repeat across every cell the
    # main course occupies (a course meeting Wed periods 1+2 has two cells,
    # both carrying the same 备注). Dedup on (title, weekday, period) so we
    # emit the recitation once per real time slot, not N times.
    seen_recitation_keys: set[tuple[str, int, int]] = set()

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

        # Pull recitation slots from the 备注 trailer. Reuse the main
        # lecture's week range when present (the remark usually doesn't
        # repeat "1-15周").
        if slot is not None:
            rec_start_week = slot["start_week"]
            rec_end_week = slot["end_week"]
        else:
            rec_start_week, rec_end_week = _parse_week_range(_strip_remark(schedule_line))
        for r_slot in _build_recitation_slots(title, schedule_line, rec_start_week, rec_end_week):
            key = (r_slot["title"], r_slot["weekday"], r_slot["period"])
            if key in seen_recitation_keys:
                continue
            seen_recitation_keys.add(key)
            slots.append(r_slot)

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
    # The "备注：..." trailer often describes a *different* class (recitation /
    # 习题课) with its own day / week-parity / location. Stripping it before
    # parsing prevents 双周/单周 markers inside the remark from being
    # misclassified as the main lecture's week parity. The remark itself is
    # consumed separately by _build_recitation_slots() to emit a second slot.
    info_main = _strip_remark(info_line)
    start_week, end_week = _parse_week_range(info_main)
    week_type = _parse_week_type(info_main)
    location = _extract_schedule_location(info_main)
    return {
        "title": title,
        "weekday": weekday,
        "period": period,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "slot_type": "lecture",
        "start_week": start_week,
        "end_week": end_week,
        "week_type": week_type,
        # Stable hash anchor: identical inputs always compute the same id, so
        # repeating the import upserts the row instead of duplicating it.
        "external_id": (
            f"portal:{title}:wd={weekday}:p={period}:wt={week_type}"
            f":w={start_week}-{end_week}"
        ),
    }


def _strip_remark(info_line: str) -> str:
    """Return only the part before '备注：' — the main lecture's info."""
    return _REMARK_SPLIT_RE.split(info_line, maxsplit=1)[0]


def _extract_remark(info_line: str) -> str:
    """Return only the part after '备注：' — the supplementary info, or ''."""
    parts = _REMARK_SPLIT_RE.split(info_line, maxsplit=1)
    return parts[1].strip() if len(parts) >= 2 else ""


def _build_recitation_slots(
    title: str,
    info_line: str,
    main_start_week: int,
    main_end_week: int,
) -> list[dict]:
    """Parse '备注：习题课X周Y10-11节，教室：Z' into one or more slots.

    Returns [] when no recitation marker is present, or when the format isn't
    recognized — recitations are best-effort and should never crash the main
    parse. Each occupied period becomes its own slot so the schedule grid
    renders them as adjacent rows, mirroring how lectures are emitted.
    """
    remark = _extract_remark(info_line)
    if not remark or not _RECITATION_PRESENT_RE.search(remark):
        return []

    week_type_match = _RECITATION_WEEKTYPE_RE.search(remark)
    week_type = {"每周": "all", "单周": "odd", "双周": "even"}.get(
        week_type_match.group(1) if week_type_match else "", "all"
    )

    weekday_match = _RECITATION_WEEKDAY_RE.search(remark)
    if not weekday_match:
        return []
    weekday = _CHINESE_WEEKDAY.get(weekday_match.group(1))
    if weekday is None:
        return []

    period_match = _RECITATION_PERIOD_RE.search(remark)
    if not period_match:
        return []
    period_start = int(period_match.group(1))
    period_end = int(period_match.group(2))
    if not (1 <= period_start <= period_end <= len(_PERIOD_TIMES)):
        return []

    # Location: the remark often lists multiple rooms separated by 、
    # ("三教208、二教315、二教317") — pick the first as the canonical room.
    location_match = _RECITATION_LOCATION_RE.search(remark)
    if location_match:
        location_raw = location_match.group(1)
    else:
        # No 教室 label — sometimes the remark just says "10-11节" with no
        # room specified. Leave empty rather than guess.
        location_raw = ""
    location = location_raw.split("、")[0].strip(" ,，") if location_raw else ""

    slots = []
    for p in range(period_start, period_end + 1):
        st, et = _PERIOD_TIMES[p - 1]
        rec_title = f"{title} 习题课"
        slots.append({
            "title": rec_title,
            "weekday": weekday,
            "period": p,
            "start_time": st,
            "end_time": et,
            "start_week": main_start_week,
            "end_week": main_end_week,
            "week_type": week_type,
            "location": location,
            "slot_type": "lecture",
            "is_recitation": True,
            "external_id": (
                f"portal:{rec_title}:wd={weekday}:p={p}:wt={week_type}"
                f":w={main_start_week}-{main_end_week}"
            ),
        })
    return slots


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
