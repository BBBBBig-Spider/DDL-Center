"""Tiny helpers shared across GUI widgets and dialogs.

Most ``app/gui/`` modules deal with Pythonic dataclasses (``Task``,
``ScheduleSlot``, ``Exam``, ``Alert``) but a handful of paths — AI suggestions,
import previews, sync results — pass plain ``dict`` objects through the same
view code. ``get_field`` lets a widget read a field uniformly without caring
which shape arrived. ``format_time_field`` and ``duration_hours`` round out
common time-formatting needs that several panels duplicated.
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` off either a dict (``obj[key]``) or an object (``obj.key``)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def format_time_field(value: Any) -> str:
    """Render a time-like value as ``HH:MM``. Strings are truncated; ``None`` becomes ``""``."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:5]
    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)[:5]


def duration_hours(slot_obj: Any) -> float | None:
    """Return slot duration in hours from an object/dict with ``start_time`` and ``end_time``.

    Returns ``None`` when either field is unparseable rather than raising — the
    callers display this in a tooltip and treat ``None`` as "unknown".
    """
    start = format_time_field(get_field(slot_obj, "start_time"))
    end = format_time_field(get_field(slot_obj, "end_time"))
    try:
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
    except ValueError:
        return None
    return max(0.0, (end_dt - start_dt).total_seconds() / 3600)
