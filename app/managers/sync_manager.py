"""Teaching-site sync orchestration."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

from app.models.course import Course
from app.models.exam import Exam
from app.models.schedule_slot import ScheduleSlot
from app.models.sync_record import SyncRecord
from app.models.sync_result import SyncResult
from app.models.task import Task
from app.network.network_errors import NetworkError, SyncError
from app.parsers._common import coerce_str


class SyncManager:
    def __init__(
        self,
        *,
        auth_client,
        teaching_site_client,
        ddl_parser,
        schedule_parser,
        exam_parser,
        task_repository,
        course_repository,
        schedule_repository,
        exam_repository,
        sync_repository,
        ai_assistant_manager=None,
        ai_fallback_enabled: bool = True,
    ) -> None:
        self.auth_client = auth_client
        self.teaching_site_client = teaching_site_client
        self.ddl_parser = ddl_parser
        self.schedule_parser = schedule_parser
        self.exam_parser = exam_parser
        self.task_repository = task_repository
        self.course_repository = course_repository
        self.schedule_repository = schedule_repository
        self.exam_repository = exam_repository
        self.sync_repository = sync_repository
        self.ai_assistant_manager = ai_assistant_manager
        self.ai_fallback_enabled = ai_fallback_enabled

    def sync_from_teaching_site(
        self,
        username: str = "",
        password: str = "",
        *,
        semester: str = "",
    ) -> SyncResult:
        result = SyncResult()
        try:
            session = self._login(username, password)
            result.source = "network"
        except Exception as exc:
            raise SyncError(str(exc)) from exc

        # Outer try is intentionally narrow: it only wraps the fetch + parse
        # pair, because those are "all or nothing" for a sync run — no items
        # means nothing to process. Per-item failures inside
        # ``_process_assignment_items`` are caught individually so one bad
        # task can't silently abort the whole batch. See REVIEW.md severe #5.
        try:
            raw = self.teaching_site_client.fetch_current_semester_ddl(session)
            warnings = getattr(self.teaching_site_client, "_last_warnings", None) or []
            for w in warnings:
                if w:
                    result.errors.append(w)
            try:
                # 让 client 自行清空（如有）
                self.teaching_site_client._last_warnings = []
            except Exception as exc:
                # Best-effort cleanup; surfaces in stdout for debugging but
                # never aborts the sync.
                print(f"[SYNC] failed to clear client warnings: {exc}")
            items = self.ddl_parser.parse_assignment_items(raw)
        except Exception as exc:
            result.errors.append(f"DDL同步失败：{exc}")
            return result

        # Per-item processing has its own internal try/except per item, so
        # we don't wrap it in a try here — letting an unexpected programmer
        # error bubble up is preferable to swallowing it as "DDL同步失败".
        self._process_assignment_items(items, result)
        return result

    def _login(
        self,
        username: str,
        password: str,
    ):
        username = username or os.getenv("PKU_USERNAME", "")
        password = password or os.getenv("PKU_PASSWORD", "")
        if not username or not password:
            raise SyncError("username and password are required for network sync")
        return self.auth_client.login(username, password)

    # ─── 新流程：基于 li 的处理 ────────────────────────────────

    def _process_assignment_items(self, items: list[dict], result: SyncResult) -> None:
        now = datetime.now()
        for item in items:
            # Each item is wrapped so a single bad payload can't abort the
            # entire batch. We surface the failure on ``result.errors`` with
            # enough identifier to track it down. See REVIEW.md severe #5.
            try:
                due = item.get("due_time")
                if due is not None and due < now:
                    result.tasks_dropped_overdue += 1
                    continue
                if due is None:
                    self._ai_resolve_missing_due(item, result, now)
                    continue
                self._upsert_sync_task(item, due, result, now)
            except Exception as exc:
                ext_id = item.get("external_id") or item.get("title") or "?"
                result.errors.append(f"task {ext_id}: {exc}")
                continue

        try:
            self.task_repository.purge_hidden_overdue(now)
        except Exception as exc:
            # Cleanup of hidden-overdue rows is best-effort; failing it
            # shouldn't poison the whole sync result.
            print(f"[SYNC] purge_hidden_overdue failed: {exc}")

    def _upsert_sync_task(
        self,
        item: dict,
        due_time: datetime,
        result: SyncResult,
        now: datetime,
    ) -> None:
        course_external_id = item.get("course_external_id") or ""
        li_id = item.get("external_id") or ""
        if course_external_id:
            external_id = f"{course_external_id}:{li_id}"
        else:
            external_id = li_id
        if not external_id:
            return

        existing = self.task_repository.find_by_external_id(external_id)
        if existing is not None:
            result.tasks_unchanged += 1
            return

        desc = (item.get("description") or "")
        if len(desc) > 120:
            if (
                self.ai_assistant_manager is not None
                and self.ai_fallback_enabled
                and self.ai_assistant_manager.is_available()
            ):
                try:
                    desc = self.ai_assistant_manager.compress_description(desc, 120)
                except Exception:
                    desc = self._truncate(desc, 120)
            else:
                desc = self._truncate(desc, 120)

        course_payload = {
            "course_external_id": course_external_id,
            "course_name": item.get("course_name") or "",
        }
        course_id = self._ensure_course(course_payload, result)

        task = Task(
            title=str(item.get("title") or "未命名作业")[:200],
            due_time=due_time,
            description=desc,
            source="sync",
            external_id=external_id,
            course_id=course_id,
            created_at=now,
            updated_at=now,
            raw_payload=json.dumps(
                {
                    "raw": "sync-v2",
                    "course_external_id": course_external_id,
                    "course_name": item.get("course_name") or "",
                },
                ensure_ascii=False,
            ),
        )
        self.task_repository.add(task)
        result.tasks_new += 1

    def _ai_resolve_missing_due(
        self,
        item: dict,
        result: SyncResult,
        now: datetime,
    ) -> None:
        if (
            not self.ai_fallback_enabled
            or self.ai_assistant_manager is None
            or not self.ai_assistant_manager.is_available()
        ):
            result.ai_drop_no_ai += 1
            return

        text = item.get("text") or item.get("description") or ""
        if not text.strip():
            result.ai_drop_non_task += 1
            return

        try:
            parsed = self.ai_assistant_manager.parse_item_from_text(text[:1500])
        except Exception as exc:
            result.errors.append(
                f"AI 兜底失败：{item.get('title') or item.get('external_id') or ''} → {exc}"
            )
            return

        if parsed.get("type") != "task":
            result.ai_drop_non_task += 1
            return

        payload = parsed.get("payload") or {}
        due_time = self._coerce_datetime(payload.get("due_time"))
        if due_time is None or due_time < now:
            result.ai_drop_overdue += 1
            return

        course_external_id = item.get("course_external_id") or ""
        li_id = item.get("external_id") or ""
        if course_external_id:
            external_id = f"ai-rec-{course_external_id}:{li_id}"
        else:
            external_id = f"ai-rec-{li_id}"
        if not li_id and not course_external_id:
            return

        if self.task_repository.find_by_external_id(external_id) is not None:
            result.tasks_unchanged += 1
            return

        desc = str(payload.get("description") or item.get("description") or "")
        if len(desc) > 120:
            try:
                desc = self.ai_assistant_manager.compress_description(desc, 120)
            except Exception:
                desc = self._truncate(desc, 120)

        course_payload = {
            "course_external_id": course_external_id,
            "course_name": item.get("course_name") or "",
        }
        course_id = self._ensure_course(course_payload, result)

        try:
            estimated = float(payload.get("estimated_hours", 2) or 2)
        except (TypeError, ValueError):
            estimated = 2.0
        if estimated <= 0:
            estimated = 2.0

        task = Task(
            title=str(payload.get("title") or item.get("title") or "AI 兜底任务")[:200],
            due_time=due_time,
            description=desc,
            estimated_hours=estimated,
            status="todo",
            priority=int(payload.get("priority", 2) or 2),
            source="sync",
            external_id=external_id,
            course_id=course_id,
            created_at=now,
            updated_at=now,
            raw_payload=json.dumps(
                {
                    "raw": "ai-recovered",
                    "source_item": item.get("title") or "",
                    "course_external_id": course_external_id,
                    "course_name": item.get("course_name") or "",
                },
                ensure_ascii=False,
            ),
        )
        self.task_repository.add(task)
        result.ai_recovered += 1

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        head = text[: max_chars - 1]
        for sep in ("。", "；", "\n", "！", "？"):
            idx = head.rfind(sep)
            if idx >= max_chars // 2:
                return head[: idx + 1] + "…"
        return head + "…"

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo is not None else value
        if isinstance(value, str) and value.strip():
            try:
                dt = datetime.fromisoformat(value.strip().replace("Z", ""))
            except ValueError:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
        return None

    # ─── 工具 / 公共：course upsert + sync record ──────────────

    def _sync_tasks(self, tasks: list[Task], result: SyncResult) -> None:
        """Backward-compat shim used by tests that bypass the new pipeline.

        Mirrors the legacy "skip when external_id already known, otherwise
        add" semantics on a list of pre-built ``Task`` objects.
        """
        now = datetime.now()
        for task in tasks:
            if not task.external_id:
                continue
            if task.due_time is not None and task.due_time < now:
                continue
            existing = self.task_repository.find_by_external_id(task.external_id)
            if existing is not None:
                result.tasks_unchanged += 1
                continue
            task.created_at = now
            task.updated_at = now
            self.task_repository.add(task)
            result.tasks_new += 1
        try:
            self.task_repository.purge_hidden_overdue(now)
        except Exception as exc:
            # Best-effort cleanup of hidden-overdue rows; never fatal.
            print(f"[SYNC] purge_hidden_overdue failed (legacy path): {exc}")

    def _ensure_course(self, payload: dict[str, Any], result: SyncResult) -> int | None:
        external_id = coerce_str(payload.get("course_external_id"))
        if not external_id:
            raw = payload.get("raw")
            if isinstance(raw, dict):
                external_id = coerce_str(raw.get("course_external_id") or raw.get("courseId"))
        if not external_id:
            return None

        existing = self.course_repository.find_by_external_id(external_id)
        if existing is not None:
            return existing.id

        raw = payload.get("raw")
        name = coerce_str(payload.get("course_name"))
        if not name and isinstance(raw, dict):
            name = coerce_str(raw.get("course") or raw.get("course_name"))
        course = Course(
            name=name or external_id,
            external_id=external_id,
            source="sync",
            raw_payload=json.dumps(payload, ensure_ascii=False, default=str),
        )
        self.course_repository.add(course)
        result.courses_new += 1
        return course.id

    def _record(
        self,
        source_type: str,
        external_id: str,
        local_type: str,
        local_id: int | None,
        raw_hash: str,
        status: str,
    ) -> None:
        if local_id is None:
            return
        self.sync_repository.upsert_record(
            SyncRecord(
                source_type=source_type,
                external_id=external_id,
                local_type=local_type,
                local_id=local_id,
                raw_hash=raw_hash,
                last_seen_at=datetime.now(),
                status=status,
            )
        )

    @staticmethod
    def _payload(raw_payload: str) -> dict[str, Any]:
        if not raw_payload:
            return {}
        try:
            data = json.loads(raw_payload)
            return data if isinstance(data, dict) else {"raw": data}
        except ValueError:
            return {"raw": raw_payload}

    @staticmethod
    def _payload_from_slot(slot: ScheduleSlot) -> dict[str, Any]:
        raw_payload = getattr(slot, "raw_payload", "")
        if raw_payload:
            return SyncManager._payload(raw_payload)
        return {"raw": {"external_id": slot.external_id, "title": slot.title}}

    @staticmethod
    def _hash_object(obj) -> str:
        raw = json.dumps(
            SyncManager._stable_sync_payload(obj),
            default=str,
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _stable_sync_payload(obj) -> dict[str, Any]:
        if isinstance(obj, Task):
            return {
                "type": "task",
                "title": obj.title,
                "due_time": obj.due_time.isoformat(),
                "description": obj.description,
                "estimated_hours": obj.estimated_hours,
                "priority": obj.priority,
                "source": obj.source,
                "external_id": obj.external_id,
                "raw_payload": obj.raw_payload,
            }
        if isinstance(obj, ScheduleSlot):
            return {
                "type": "schedule_slot",
                "title": obj.title,
                "weekday": obj.weekday,
                "start_time": obj.start_time.isoformat(),
                "end_time": obj.end_time.isoformat(),
                "location": obj.location,
                "slot_type": obj.slot_type,
                "start_week": obj.start_week,
                "end_week": obj.end_week,
                "week_type": obj.week_type,
                "source": obj.source,
                "external_id": obj.external_id,
                "raw_payload": getattr(obj, "raw_payload", ""),
            }
        if isinstance(obj, Exam):
            return {
                "type": "exam",
                "name": obj.name,
                "start_time": obj.start_time.isoformat(),
                "end_time": obj.end_time.isoformat(),
                "location": obj.location,
                "seat": obj.seat,
                "exam_type": obj.exam_type,
                "source": obj.source,
                "external_id": obj.external_id,
                "raw_payload": obj.raw_payload,
            }
        return {"type": type(obj).__name__, "value": obj}
