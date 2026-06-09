"""Shared helpers used across the parsers package.

The four parsers (ddl, exam, schedule, portal) all reach for the same handful of
type-coercion utilities. Keeping one canonical copy here avoids subtle drift
when one parser tightens a rule the others need too.
"""
from __future__ import annotations

from typing import Any, Optional


def coerce_str(value: Any) -> str:
    """Return a stripped string representation of ``value``.

    ``None`` becomes an empty string. Strings are stripped; everything else is
    passed through ``str()`` unchanged (no strip — caller decides).
    """
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value)


def coerce_external_id(value: Any) -> Optional[str]:
    """Coerce ``value`` into a non-empty external-id string, or ``None``.

    Empty / whitespace-only strings collapse to ``None`` so callers can use the
    classic ``coerce_external_id(...) or fallback`` pattern.
    """
    if value is None:
        return None
    text = value.strip() if isinstance(value, str) else str(value)
    return text or None
