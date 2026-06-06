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


class SyncManager:
    def __init__(
        self,
        *,
        auth_client,
        portal_auth_client=None,
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
    ) -> None:
        self.auth_client = auth_client
        self.portal_auth_client = portal_auth_client or auth_client
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

    def sync_from_teaching_site(
        self,
        username: str = "",
        password: str = "",
        *,
        semester: str = "",
        otp_code: str = "",
    ) -> SyncResult:
        result = SyncResult()
        try:
            session = self._login(username, password)
            result.source = "network"
        except Exception as exc:
            raise SyncError(str(exc)) from exc

        self._sync_section(
            result,
            label="DDL",
            fetch=lambda: self.teaching_site_client.fetch_ddl(session, semester),
            parse=self.ddl_parser.parse,
            apply=self._sync_tasks,
        )
        self._sync_section(
            result,
            label="课表",
            fetch=lambda: self.teaching_site_client.fetch_schedule(self._login_portal(username, password, otp_code), semester),
            parse=self.schedule_parser.parse,
            apply=self._sync_schedule,
        )
        self._sync_section(
            result,
            label="考试",
            fetch=lambda: self.teaching_site_client.fetch_exams(session, semester),
            parse=self.exam_parser.parse,
            apply=self._sync_exams,
        )
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

    def _login_portal(
        self,
        username: str,
        password: str,
        otp_code: str = "",
    ):
        username = username or os.getenv("PKU_USERNAME", "")
        password = password or os.getenv("PKU_PASSWORD", "")
        otp_code = otp_code or os.getenv("PKU_OTP_CODE", "")
        if not username or not password:
            raise SyncError("username and password are required for portal sync")
        return self.portal_auth_client.login(username, password, otp_code=otp_code)

    @staticmethod
    def _sync_section(result: SyncResult, *, label: str, fetch, parse, apply) -> None:
        try:
            raw = fetch()
            items = parse(raw)
            apply(items, result)
        except Exception as exc:
            result.errors.append(f"{label}同步失败：{exc}")

    def _sync_tasks(self, tasks: list[Task], result: SyncResult) -> None:
        for task in tasks:
            if not task.external_id:
                continue
            payload = self._payload(task.raw_payload)
            task.course_id = self._ensure_course(payload, result)
            old_record = self.sync_repository.get_record("ddl", task.external_id)
            raw_hash = self._hash_object(task)
            existing = self.task_repository.find_by_external_id(task.external_id)

            if existing is None:
                task.created_at = datetime.now()
                task.updated_at = task.created_at
                self.task_repository.add(task)
                status = "new"
                result.tasks_new += 1
            elif old_record is not None and old_record.raw_hash == raw_hash:
                status = "unchanged"
                result.tasks_unchanged += 1
                task.id = existing.id
            elif existing.user_modified:
                status = "unchanged"
                result.tasks_unchanged += 1
                task.id = existing.id
            else:
                task.id = existing.id
                task.created_at = existing.created_at
                task.updated_at = datetime.now()
                task.status = existing.status
                task.completed_at = existing.completed_at
                task.user_modified = existing.user_modified
                self.task_repository.update(task)
                status = "updated"
                result.tasks_updated += 1

            self._record("ddl", task.external_id, "task", task.id, raw_hash, status)

    def _sync_schedule(self, slots: list[ScheduleSlot], result: SyncResult) -> None:
        for slot in slots:
            if not slot.external_id:
                continue
            payload = self._payload_from_slot(slot)
            slot.course_id = self._ensure_course(payload, result)
            old_record = self.sync_repository.get_record("schedule", slot.external_id)
            raw_hash = self._hash_object(slot)
            existing = self.schedule_repository.find_by_external_id(slot.external_id)

            if existing is None:
                self.schedule_repository.add(slot)
                status = "new"
                result.schedule_new += 1
            elif old_record is not None and old_record.raw_hash == raw_hash:
                slot.id = existing.id
                status = "unchanged"
                result.schedule_unchanged += 1
            else:
                slot.id = existing.id
                self.schedule_repository.update(slot)
                status = "updated"
                result.schedule_updated += 1
            self._record("schedule", slot.external_id, "schedule_slot", slot.id, raw_hash, status)

    def _sync_exams(self, exams: list[Exam], result: SyncResult) -> None:
        for exam in exams:
            if not exam.external_id:
                continue
            payload = self._payload(exam.raw_payload)
            exam.course_id = self._ensure_course(payload, result)
            old_record = self.sync_repository.get_record("exam", exam.external_id)
            raw_hash = self._hash_object(exam)
            existing = self.exam_repository.find_by_external_id(exam.external_id)

            if existing is None:
                self.exam_repository.add(exam)
                status = "new"
                result.exams_new += 1
            elif old_record is not None and old_record.raw_hash == raw_hash:
                exam.id = existing.id
                status = "unchanged"
                result.exams_unchanged += 1
            else:
                exam.id = existing.id
                self.exam_repository.update(exam)
                status = "updated"
                result.exams_updated += 1
            self._record("exam", exam.external_id, "exam", exam.id, raw_hash, status)

    def _ensure_course(self, payload: dict[str, Any], result: SyncResult) -> int | None:
        external_id = self._coerce_str(payload.get("course_external_id"))
        if not external_id:
            raw = payload.get("raw")
            if isinstance(raw, dict):
                external_id = self._coerce_str(raw.get("course_external_id") or raw.get("courseId"))
        if not external_id:
            return None

        existing = self.course_repository.find_by_external_id(external_id)
        if existing is not None:
            return existing.id

        raw = payload.get("raw")
        name = self._coerce_str(payload.get("course_name"))
        if not name and isinstance(raw, dict):
            name = self._coerce_str(raw.get("course") or raw.get("course_name"))
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

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else str(value)
