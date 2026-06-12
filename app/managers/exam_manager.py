"""Business-facing exam queries."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from app.models.exam import Exam


class ExamManager:
    def __init__(self, exam_repository) -> None:
        self.exam_repository = exam_repository

    def list_exams(self, course_id: int | None = None) -> list[Exam]:
        if course_id is None:
            return self.exam_repository.list_all()
        if not isinstance(course_id, int) or isinstance(course_id, bool):
            raise TypeError("course_id must be int or None")
        return self.exam_repository.list_by_course(course_id)

    def get_exam(self, exam_id: int) -> Exam | None:
        if not isinstance(exam_id, int) or isinstance(exam_id, bool):
            raise TypeError("exam_id must be int")
        return self.exam_repository.get_by_id(exam_id)

    def create_exam(self, data: dict) -> int:
        exam = self._dict_to_exam(data)
        if exam.external_id:
            existing = self.exam_repository.find_by_external_id(exam.external_id)
            if existing is not None:
                exam.id = existing.id
                self.exam_repository.update(exam)
                return existing.id
        return self.exam_repository.add(exam)

    def delete_all(self) -> int:
        """Delete every exam (manual + sync). Returns row count removed."""
        return self.exam_repository.delete_all()

    def _dict_to_exam(self, data: dict) -> Exam:
        if not isinstance(data, dict):
            raise TypeError("data must be dict")

        name = self._coerce_str(data.get("name") or data.get("title"))
        if not name:
            raise ValueError("exam name cannot be empty")

        start_time = self._coerce_datetime(data.get("start_time") or data.get("startTime"))
        if start_time is None:
            raise ValueError("exam start_time is required")

        end_time = self._coerce_datetime(data.get("end_time") or data.get("endTime"))
        if end_time is None:
            end_time = start_time + timedelta(hours=2)
        if end_time <= start_time:
            raise ValueError("exam end_time must be after start_time")

        external_id = self._coerce_str(data.get("external_id") or data.get("id")) or self._external_id(
            name,
            start_time,
            self._coerce_str(data.get("location")),
        )
        raw_payload = data.get("raw_payload")
        if not isinstance(raw_payload, str):
            raw_payload = json.dumps({"raw": data}, ensure_ascii=False, default=str)

        return Exam(
            name=name,
            course_id=self._coerce_optional_int(data.get("course_id") or data.get("courseId")),
            start_time=start_time,
            end_time=end_time,
            location=self._coerce_str(data.get("location")),
            seat=self._coerce_str(data.get("seat")),
            exam_type=self._normalize_exam_type(data.get("exam_type") or data.get("type")),
            source=self._normalize_source(data.get("source")),
            external_id=external_id,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else str(value).strip()

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if value in (None, "") or isinstance(value, bool):
            return None
        return int(value)

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _normalize_exam_type(value: Any) -> str:
        text = value.strip().lower() if isinstance(value, str) else ""
        return text if text in {"midterm", "final", "quiz", "other"} else "other"

    @staticmethod
    def _normalize_source(value: Any) -> str:
        text = value.strip().lower() if isinstance(value, str) else ""
        return text if text in {"manual", "sync"} else "sync"

    @staticmethod
    def _external_id(name: str, start_time: datetime, location: str) -> str:
        digest = hashlib.sha256(f"{name}|{start_time.isoformat()}|{location}".encode("utf-8")).hexdigest()
        return f"exam-{digest[:16]}"
