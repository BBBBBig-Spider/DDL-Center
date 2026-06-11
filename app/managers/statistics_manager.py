"""Build chart-ready statistics from tasks."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from app.models.statistics import StatisticsData


class StatisticsManager:
    def __init__(self, task_manager) -> None:
        self.task_manager = task_manager

    def get_statistics(self, *, now: datetime | None = None) -> StatisticsData:
        now = now or datetime.now()
        tasks = self.task_manager.list_tasks()

        by_status: Counter[str] = Counter(task.status for task in tasks)
        by_priority: Counter[int] = Counter(task.priority for task in tasks)
        workload_by_day: defaultdict[str, float] = defaultdict(float)
        upcoming: list[dict] = []

        for task in tasks:
            if task.status != "done":
                workload_by_day[task.due_time.date().isoformat()] += float(task.estimated_hours)
                if task.due_time >= now:
                    upcoming.append(
                        {
                            "id": task.id,
                            "title": task.title,
                            "due_time": task.due_time.isoformat(),
                            "priority": task.priority,
                        }
                    )

        total = len(tasks)
        done = by_status.get("done", 0)
        overdue = sum(1 for task in tasks if task.is_overdue(now))
        upcoming.sort(key=lambda item: item["due_time"])

        return StatisticsData(
            total_tasks=total,
            done_tasks=done,
            open_tasks=total - done,
            overdue_tasks=overdue,
            completion_rate=(done / total if total else 0.0),
            by_status=dict(by_status),
            by_priority=dict(by_priority),
            workload_by_day=dict(sorted(workload_by_day.items())),
            upcoming_deadlines=upcoming[:10],
        )
