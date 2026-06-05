"""Sync result DTO returned by SyncManager."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SyncResult:
    used_mock: bool = False
    source: str = "network"
    tasks_new: int = 0
    tasks_updated: int = 0
    tasks_unchanged: int = 0
    schedule_new: int = 0
    schedule_updated: int = 0
    schedule_unchanged: int = 0
    exams_new: int = 0
    exams_updated: int = 0
    exams_unchanged: int = 0
    courses_new: int = 0
    errors: list[str] = field(default_factory=list)

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
        )
