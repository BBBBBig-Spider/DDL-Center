"""Statistics DTOs used by StatisticsManager and AppFacade."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StatisticsData:
    total_tasks: int = 0
    done_tasks: int = 0
    open_tasks: int = 0
    overdue_tasks: int = 0
    completion_rate: float = 0.0
    by_status: dict[str, int] = field(default_factory=dict)
    by_priority: dict[int, int] = field(default_factory=dict)
    workload_by_day: dict[str, float] = field(default_factory=dict)
    upcoming_deadlines: list[dict] = field(default_factory=list)
