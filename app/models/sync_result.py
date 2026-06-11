"""Sync result DTO returned by SyncManager."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SyncResult:
    source: str = "network"
    tasks_new: int = 0
    tasks_updated: int = 0
    tasks_unchanged: int = 0
    tasks_dropped_overdue: int = 0
    schedule_new: int = 0
    schedule_updated: int = 0
    schedule_unchanged: int = 0
    exams_new: int = 0
    exams_updated: int = 0
    exams_unchanged: int = 0
    courses_new: int = 0
    ai_recovered: int = 0
    ai_drop_overdue: int = 0
    ai_drop_non_task: int = 0
    ai_drop_no_ai: int = 0
    # Legacy fields kept for backward compatibility — never written by the
    # new sync flow but referenced by older imports/tests.
    ai_recovered_exams: int = 0
    ai_skipped_announcements: int = 0
    ai_class_hints: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ai_recovered_tasks(self) -> int:
        return self.ai_recovered

    @ai_recovered_tasks.setter
    def ai_recovered_tasks(self, value: int) -> None:
        self.ai_recovered = int(value)

    @property
    def total_changed(self) -> int:
        return (
            self.tasks_new
            + self.tasks_updated
            + self.schedule_new
            + self.schedule_updated
            + self.exams_new
            + self.exams_updated
            + self.courses_new
            + self.ai_recovered
            + self.ai_recovered_exams
        )
