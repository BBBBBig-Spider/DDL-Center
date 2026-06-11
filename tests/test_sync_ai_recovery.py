"""End-to-end tests for SyncManager._ai_resolve_missing_due (新流程).

The fixtures are stubs (no Qt, no SQLite, no network). Old "全量复审" 用例
已删除；现在只覆盖：1) 无结束时间 → AI 兜底写入；2) AI 返回逾期任务被丢弃；
3) ai_fallback_enabled=False 时不调 AI。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.managers.sync_manager import SyncManager
from app.models.sync_result import SyncResult
from app.models.task import Task


# ─── Fakes ──────────────────────────────────────────────────────────────


class _FakeAIManager:
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = 0
        self.compress_calls = 0

    def is_available(self) -> bool:
        return True

    def parse_item_from_text(self, _text: str) -> dict:
        self.calls += 1
        if not self._replies:
            raise RuntimeError("No more scripted replies")
        return self._replies.pop(0)

    def compress_description(self, text: str, max_chars: int = 120) -> str:
        self.compress_calls += 1
        return text[:max_chars]


class _FakeSyncRepository:
    def upsert_record(self, _record):
        return 1

    def get_record(self, _source_type, _external_id):
        return None


class _FakeRepository:
    def __init__(self):
        self.added: list = []
        self._next_id = 1
        self._by_ext_id: dict[str, object] = {}

    def add(self, item):
        item.id = self._next_id
        self._next_id += 1
        self.added.append(item)
        if getattr(item, "external_id", None):
            self._by_ext_id[item.external_id] = item
        return item.id

    def find_by_external_id(self, external_id: str):
        return self._by_ext_id.get(external_id)


class _FakeTaskRepository(_FakeRepository):
    def purge_hidden_overdue(self, _now):
        return 0


class _FakeCourse:
    def __init__(self, id_: int, external_id: str, name: str):
        self.id = id_
        self.external_id = external_id
        self.name = name


class _FakeCourseRepository:
    def __init__(self):
        self._by_ext: dict[str, _FakeCourse] = {}
        self._next_id = 1
        self.added: list = []

    def find_by_external_id(self, external_id: str):
        return self._by_ext.get(external_id)

    def add(self, course):
        course.id = self._next_id
        self._next_id += 1
        self._by_ext[course.external_id] = course
        self.added.append(course)
        return course.id


def _make_manager(*, ai_replies, ai_fallback_enabled=True, course_repository=None):
    ai = _FakeAIManager(ai_replies)
    task_repo = _FakeTaskRepository()
    sm = SyncManager(
        auth_client=None,
        teaching_site_client=None,
        ddl_parser=None,
        schedule_parser=None,
        exam_parser=None,
        task_repository=task_repo,
        course_repository=course_repository or _FakeCourseRepository(),
        schedule_repository=None,
        exam_repository=_FakeRepository(),
        sync_repository=_FakeSyncRepository(),
        ai_assistant_manager=ai,
        ai_fallback_enabled=ai_fallback_enabled,
    )
    return sm, ai, task_repo


# ─── Tests ──────────────────────────────────────────────────────────────


def test_ai_resolves_missing_due_and_writes():
    """无结束时间的 li → AI 返回 type=task + 未来 due → 写库。"""
    item = {
        "external_id": "li-1",
        "title": "新作业公告",
        "description": "请于 6 月 30 日 23:59 前提交报告",
        "text": "请于 6 月 30 日 23:59 前提交报告",
        "due_time": None,
        "course_external_id": "AI-2026-01",
        "course_name": "人工智能引论",
        "raw_html": "<li/>",
    }
    ai_reply = {
        "type": "task",
        "payload": {
            "title": "提交报告",
            "due_time": datetime(2099, 6, 30, 23, 59),
            "description": "",
            "estimated_hours": 2.0,
            "priority": 2,
            "status": "todo",
        },
    }
    sm, ai, task_repo = _make_manager(ai_replies=[ai_reply])
    result = SyncResult()
    sm._process_assignment_items([item], result)

    assert ai.calls == 1
    assert len(task_repo.added) == 1
    written = task_repo.added[0]
    assert written.external_id == "ai-rec-AI-2026-01:li-1"
    assert written.title == "提交报告"
    assert result.ai_recovered == 1


def test_ai_recovery_skips_overdue_task():
    """AI 返回的 due 已过期 → 不写库，记 ai_drop_overdue。"""
    item = {
        "external_id": "li-old",
        "title": "旧作业",
        "description": "...",
        "text": "...",
        "due_time": None,
        "course_external_id": "C1",
        "course_name": "课程1",
        "raw_html": "<li/>",
    }
    ai_reply = {
        "type": "task",
        "payload": {
            "title": "旧作业",
            "due_time": datetime.now() - timedelta(days=2),
            "description": "",
            "estimated_hours": 2.0,
            "priority": 2,
            "status": "todo",
        },
    }
    sm, ai, task_repo = _make_manager(ai_replies=[ai_reply])
    result = SyncResult()
    sm._process_assignment_items([item], result)

    assert ai.calls == 1
    assert task_repo.added == []
    assert result.ai_recovered == 0
    assert result.ai_drop_overdue == 1


def test_ai_recovery_disabled_when_flag_off():
    """ai_fallback_enabled=False 时不调 AI；item 计入 ai_drop_no_ai。"""
    item = {
        "external_id": "li-x",
        "title": "新作业",
        "description": "...",
        "text": "...",
        "due_time": None,
        "course_external_id": "C1",
        "course_name": "课程1",
        "raw_html": "<li/>",
    }
    ai_reply = {
        "type": "task",
        "payload": {
            "title": "X",
            "due_time": datetime(2099, 1, 1),
            "description": "",
            "estimated_hours": 2.0,
            "priority": 2,
            "status": "todo",
        },
    }
    sm, ai, task_repo = _make_manager(
        ai_replies=[ai_reply], ai_fallback_enabled=False
    )
    result = SyncResult()
    sm._process_assignment_items([item], result)

    assert ai.calls == 0
    assert task_repo.added == []
    assert result.ai_drop_no_ai == 1
