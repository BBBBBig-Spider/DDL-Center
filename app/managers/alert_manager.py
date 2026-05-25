"""app/managers/alert_manager.py

Day 10-13: 提醒生成。基于 tasks 与 config.py 中的阈值，产出三类提醒：

  1) deadline       —— 每个未完成任务一条（取最严重等级）
                       * overdue:  due_time <= now
                       * urgent:   now < due_time <= now + ALERT_DAYS_URGENT 天
                       * warning:  now < due_time <= now + ALERT_DAYS_WARNING 天
  2) overload       —— 同一天的未完成 DDL >= OVERLOAD_THRESHOLD 时，
                       target_type='day'，task_id=None
  3) deadline (close) —— 同一未完成任务集合中，相邻两个 DDL 之间间隔 <
                       CLOSE_DEADLINE_HOURS 小时时各自再发一条 warning 提醒

调用 ``AlertManager.generate_alerts(now=...)`` 会把上述提醒写入 alert 表，
返回本次新写入的 Alert 列表。重复调用是幂等的：同一 (task_id, kind, level)
组合在已有未读条目时不会重复插入。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List

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
    def __init__(
        self,
        alert_repository: AlertRepository,
        task_repository: TaskRepository,
    ):
        if not isinstance(alert_repository, AlertRepository):
            raise TypeError("alert_repository must be an AlertRepository")
        if not isinstance(task_repository, TaskRepository):
            raise TypeError("task_repository must be a TaskRepository")
        self.alert_repository = alert_repository
        self.task_repository = task_repository

    # ─── public API ────────────────────────────────────────────────

    def generate_alerts(self, now: datetime | None = None) -> List[Alert]:
        """生成提醒。返回本次写入数据库的新 Alert 列表。"""
        if now is None:
            now = datetime.now()
        if not isinstance(now, datetime):
            raise TypeError("now must be datetime or None")

        active_tasks = [t for t in self.task_repository.list_all() if not t.is_done()]
        existing = self._existing_signatures()

        new_alerts: List[Alert] = []
        new_alerts.extend(self._deadline_alerts(active_tasks, now, existing))
        new_alerts.extend(self._overload_alerts(active_tasks, existing))
        new_alerts.extend(self._close_deadline_alerts(active_tasks, existing))

        for alert in new_alerts:
            self.alert_repository.add(alert)

        return new_alerts

    def list_unread(self) -> List[Alert]:
        return self.alert_repository.list_unread()

    def list_all(self) -> List[Alert]:
        return self.alert_repository.list_all()

    def mark_read(self, alert_id: int) -> bool:
        if not isinstance(alert_id, int) or isinstance(alert_id, bool):
            raise TypeError("alert_id must be int")
        return self.alert_repository.mark_read(alert_id)

    def mark_all_read(self) -> int:
        return self.alert_repository.mark_all_read()

    # ─── deadline ───────────────────────────────────────────────────

    def _deadline_alerts(
        self,
        tasks: Iterable[Task],
        now: datetime,
        existing: set[tuple],
    ) -> List[Alert]:
        alerts: List[Alert] = []
        warning_window = timedelta(days=ALERT_DAYS_WARNING)
        urgent_window = timedelta(days=ALERT_DAYS_URGENT)

        for task in tasks:
            if task.id is None:
                continue

            if task.due_time <= now:
                level = "overdue"
                message = f"任务「{task.title}」已逾期"
            elif task.due_time <= now + urgent_window:
                level = "urgent"
                message = f"任务「{task.title}」将在 24 小时内到期"
            elif task.due_time <= now + warning_window:
                level = "warning"
                message = f"任务「{task.title}」将在 {ALERT_DAYS_WARNING} 天内到期"
            else:
                continue

            signature = ("task", task.id, "deadline", level)
            if signature in existing:
                continue

            alerts.append(
                Alert(
                    task_id=task.id,
                    target_type="task",
                    level=level,
                    kind="deadline",
                    message=message,
                    created_at=now,
                    is_read=False,
                )
            )
            existing.add(signature)

        return alerts

    # ─── overload ──────────────────────────────────────────────────

    def _overload_alerts(
        self,
        tasks: Iterable[Task],
        existing: set[tuple],
    ) -> List[Alert]:
        from collections import defaultdict

        per_day: dict[str, list[Task]] = defaultdict(list)
        for task in tasks:
            per_day[task.due_time.date().isoformat()].append(task)

        alerts: List[Alert] = []
        for day_key, day_tasks in per_day.items():
            if len(day_tasks) < OVERLOAD_THRESHOLD:
                continue

            signature = ("day", day_key, "overload", "warning")
            if signature in existing:
                continue

            message = f"{day_key} 这一天有 {len(day_tasks)} 个 DDL，注意分配时间"
            alerts.append(
                Alert(
                    task_id=None,
                    target_type="day",
                    level="warning",
                    kind="overload",
                    message=message,
                    is_read=False,
                )
            )
            existing.add(signature)

        return alerts

    # ─── close-deadline pairs ──────────────────────────────────────

    def _close_deadline_alerts(
        self,
        tasks: Iterable[Task],
        existing: set[tuple],
    ) -> List[Alert]:
        sorted_tasks = sorted(
            (t for t in tasks if t.id is not None),
            key=lambda t: t.due_time,
        )
        if len(sorted_tasks) < 2:
            return []

        close_window = timedelta(hours=CLOSE_DEADLINE_HOURS)
        flagged: set[int] = set()
        alerts: List[Alert] = []

        for prev, curr in zip(sorted_tasks, sorted_tasks[1:]):
            if curr.due_time - prev.due_time >= close_window:
                continue
            for task in (prev, curr):
                if task.id in flagged:
                    continue
                signature = ("task", task.id, "deadline", "close")
                if signature in existing:
                    flagged.add(task.id)
                    continue
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
                        is_read=False,
                    )
                )
                flagged.add(task.id)
                existing.add(signature)

        return alerts

    # ─── existing signature index ──────────────────────────────────

    def _existing_signatures(self) -> set[tuple]:
        """读出 alerts 表里已有的(task_id 或 day_key, kind, level/close)签名，
        让 generate_alerts() 幂等。"""
        signatures: set[tuple] = set()
        for alert in self.alert_repository.list_all():
            if alert.target_type == "task" and alert.task_id is not None:
                signatures.add(("task", alert.task_id, alert.kind, alert.level))
                if alert.kind == "deadline" and "间隔不足" in alert.message:
                    signatures.add(("task", alert.task_id, "deadline", "close"))
            elif alert.target_type == "day":
                day_key = alert.created_at.date().isoformat()
                if "这一天有" in alert.message:
                    head = alert.message.split(" 这一天", 1)[0]
                    day_key = head.strip() or day_key
                signatures.add(("day", day_key, alert.kind, alert.level))
        return signatures
