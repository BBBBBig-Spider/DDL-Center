"""Single source of truth for "what semester week is today?".

Historically this calculation was inlined 5 times across managers/widgets
with diverging defaults (different semester-start values, different
upper-bound clamps) — see REVIEW.md severe #4. All callers MUST go
through ``compute_current_week`` so a user's "semester start" change is
reflected everywhere consistently.

The helper accepts an optional ``setting_repo`` and falls back to the
``app.config.SEMESTER_START`` constant + an upper bound of 30 weeks.
The previous AI helper hardcoded 16 (see REVIEW.md severe #2), which
made every late-semester AI suggestion off by N weeks for users whose
schedule extended past week 16.
"""
from __future__ import annotations

from datetime import date


def compute_current_week(
    setting_repo=None,
    *,
    fallback_start: date | None = None,
    fallback_upper: int = 30,
) -> int:
    """Return the current semester week (1-indexed).

    Parameters
    ----------
    setting_repo:
        Optional setting repository exposing ``.get(key, default)``. When
        provided, the helper reads ``semester_start`` (ISO date) and
        ``semester_total_weeks`` (int) to override the defaults.
    fallback_start:
        Override for the semester start when the repo doesn't carry one.
        Defaults to ``app.config.SEMESTER_START``.
    fallback_upper:
        Upper bound clamp when the repo doesn't carry ``semester_total_weeks``.
        Defaults to 30.

    Returns
    -------
    int
        The 1-indexed week number, clamped to ``[1, upper]``. If "today"
        is before the semester start, returns 1.
    """
    from app.config import SEMESTER_START as CONFIG_START

    start = fallback_start if fallback_start is not None else CONFIG_START
    upper = fallback_upper

    if setting_repo is not None:
        try:
            stored_start = setting_repo.get("semester_start", None)
            if stored_start:
                # Accept ISO strings ("YYYY-MM-DD") and date-like values.
                if isinstance(stored_start, date):
                    start = stored_start
                else:
                    start = date.fromisoformat(str(stored_start)[:10])
        except Exception:
            # Bad value in the repo shouldn't break the world; fall back.
            pass
        try:
            stored_total = setting_repo.get("semester_total_weeks", None)
            if stored_total is not None:
                upper = max(1, min(40, int(stored_total)))
        except Exception:
            pass

    delta = (date.today() - start).days
    if delta < 0:
        return 1
    return max(1, min(upper, delta // 7 + 1))
