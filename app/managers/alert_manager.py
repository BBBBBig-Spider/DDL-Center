"""app/managers/alert_manager.py"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import List

from app.config import (
    ALERT_DAYS_URGENT,
    ALERT_DAYS_WARNING,
    CLOSE_DEADLINE_HOURS,
    OVERLOAD_THRESHOLD,
)
from app.models.alert import Alert
from app.models.task import Task
from app.repositories.alert_repository import AlertRepository
from app.repositories.task_repository import TaskRepository


__all__ = ["AlertManager"]


class AlertManager:
    """提醒生成与持久化。4 个 detection 方法是纯函数；
    generate_alerts() 是聚合入口，由 AppFacade 调用。"""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        alert_repository: AlertRepository | None = None,
    ):
        self.task_repository = task_repository
        self.alert_repository = alert_repository

    # ─── 聚合入口：拉 task → 跑 3 类 → 持久化（去重） ──────────

    @staticmethod
    def _signature(alert: Alert) -> tuple:
        return (alert.target_type, alert.task_id, alert.kind, alert.level, alert.message)

    def generate_alerts(self) -> List[Alert]:
        if self.task_repository is None or self.alert_repository is None:
            raise RuntimeError("AlertManager needs task_repository and alert_repository")

        tasks = self.task_repository.list_all()
        now = datetime.now()

        candidates: List[Alert] = []
        candidates.extend(self.generate_deadline_alerts(tasks, now))
        candidates.extend(self.detect_same_day_overload(tasks))
        candidates.extend(self.detect_close_deadlines(tasks))

        seen = {self._signature(a) for a in self.alert_repository.list_all()}

        produced: List[Alert] = []
        for alert in candidates:
            sig = self._signature(alert)
            if sig in seen:
                continue
            seen.add(sig)
            self.alert_repository.add(alert)
            produced.append(alert)

        return produced

    # ─── 截止日提醒（3 天 / 1 天 / 逾期） ───────────────────────

    def generate_deadline_alerts(
        self, tasks: List[Task], now: datetime
    ) -> List[Alert]:
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime")

        warning_window = timedelta(days=ALERT_DAYS_WARNING)
        urgent_window = timedelta(days=ALERT_DAYS_URGENT)

        alerts: List[Alert] = []
        for task in tasks:
            if task.is_done():
                continue

            if task.due_time <= now:
                level = "overdue"
                message = f"任务「{task.title}」已逾期"
            elif task.due_time <= now + urgent_window:
                level = "urgent"
                message = f"任务「{task.title}」将在 {ALERT_DAYS_URGENT} 天内到期"
            elif task.due_time <= now + warning_window:
                level = "warning"
                message = f"任务「{task.title}」将在 {ALERT_DAYS_WARNING} 天内到期"
            else:
                continue

            alerts.append(
                Alert(
                    task_id=task.id,
                    target_type="task",
                    level=level,
                    kind="deadline",
                    message=message,
                    created_at=now,
                )
            )

        return alerts

    # ─── 同日 DDL 过多预警 ────────────────────────────────────

    def detect_same_day_overload(self, tasks: List[Task]) -> List[Alert]:
        counter: Counter[str] = Counter()
        for task in tasks:
            if task.is_done():
                continue
            counter[task.due_time.date().isoformat()] += 1

        alerts: List[Alert] = []
        for day_key, count in counter.items():
            if count < OVERLOAD_THRESHOLD:
                continue
            alerts.append(
                Alert(
                    task_id=None,
                    target_type="day",
                    level="warning",
                    kind="overload",
                    message=f"{day_key} 共有 {count} 个 DDL，注意分配时间",
                )
            )

        return alerts

    # ─── 相邻 DDL 间隔过短预警 ───────────────────────────────

    def detect_close_deadlines(self, tasks: List[Task]) -> List[Alert]:
        active = sorted(
            (t for t in tasks if not t.is_done()),
            key=lambda t: t.due_time,
        )

        close_window = timedelta(hours=CLOSE_DEADLINE_HOURS)
        flagged: set[int | None] = set()
        alerts: List[Alert] = []

        for prev, curr in zip(active, active[1:]):
            if curr.due_time - prev.due_time >= close_window:
                continue
            for task in (prev, curr):
                if task.id in flagged:
                    continue
                flagged.add(task.id)
                alerts.append(
                    Alert(
                        task_id=task.id,
                        target_type="task",
                        level="warning",
                        kind="deadline",
                        message=(
                            f"任务「{task.title}」与相邻 DDL 间隔不足 "
                            f"{CLOSE_DEADLINE_HOURS} 小时"
                        ),
                    )
                )

        return alerts

    # ─── 进度提醒（基于 StatisticsData） ──────────────────────

    def generate_progress_alert(self, statistics) -> List[Alert]:
        """完成率过低时生成一条全局 progress 提醒。
        StatisticsData 还未定型，按 duck-typing 取 completion_rate。"""
        rate = getattr(statistics, "completion_rate", None)
        if rate is None:
            return []

        if rate >= 0.5:
            return []

        return [
            Alert(
                task_id=None,
                target_type="global",
                level="info",
                kind="progress",
                message=f"近期完成率仅 {rate:.0%}，注意补进度",
            )
        ]
