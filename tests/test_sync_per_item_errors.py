"""tests/test_sync_per_item_errors.py — verify per-item failures during
DDL sync don't abort the whole batch (REVIEW.md severe #5).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.managers.sync_manager import SyncManager
from app.models.sync_result import SyncResult


# ─── Minimal fakes ─────────────────────────────────────────────────────


class _FakeRepo:
    def __init__(self):
        self.added: list = []
        self._next_id = 1
        self._by_ext: dict[str, object] = {}

    def add(self, item):
        item.id = self._next_id
        self._next_id += 1
        self.added.append(item)
        if getattr(item, "external_id", None):
            self._by_ext[item.external_id] = item
        return item.id

    def find_by_external_id(self, external_id: str):
        return self._by_ext.get(external_id)


class _FakeTaskRepo(_FakeRepo):
    def purge_hidden_overdue(self, _now):
        return 0


class _FlakyTaskRepo(_FakeTaskRepo):
    """``find_by_external_id`` raises the first time it's called, then
    behaves normally. This simulates a transient DB hiccup partway
    through a batch."""

    def __init__(self):
        super().__init__()
        self._calls = 0

    def find_by_external_id(self, external_id: str):
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("simulated DB hiccup on first item")
        return super().find_by_external_id(external_id)


class _FakeSyncRepo:
    def upsert_record(self, _record):
        return 1

    def get_record(self, _source_type, _external_id):
        return None


class _FakeAuth:
    def login(self, _u, _p):
        return object()


class _GoodClient:
    """Fetches a fixed payload successfully."""

    def __init__(self):
        self._last_warnings: list[str] = []

    def fetch_current_semester_ddl(self, _session) -> str:
        return "<html>ignored</html>"


class _ExplodingClient:
    """Always raises during fetch — simulates a network/HTTP error."""

    def __init__(self):
        self._last_warnings: list[str] = []

    def fetch_current_semester_ddl(self, _session):
        raise RuntimeError("teaching site is down")


class _StaticParser:
    """Returns a pre-canned list of items, regardless of the input HTML."""

    def __init__(self, items):
        self._items = items

    def parse_assignment_items(self, _raw):
        return list(self._items)


def _make_sm(*, client, parser, task_repo=None) -> SyncManager:
    return SyncManager(
        auth_client=_FakeAuth(),
        teaching_site_client=client,
        ddl_parser=parser,
        schedule_parser=None,
        exam_parser=None,
        task_repository=task_repo or _FakeTaskRepo(),
        course_repository=_FakeRepo(),
        schedule_repository=None,
        exam_repository=_FakeRepo(),
        sync_repository=_FakeSyncRepo(),
    )


# ─── Tests ─────────────────────────────────────────────────────────────


def test_per_item_error_does_not_abort_batch():
    """Item #1 raises (flaky repo). Item #2 must still be processed and
    item #1 must be reported in ``result.errors`` with its identifier."""
    future = datetime.now() + timedelta(days=3)
    items = [
        {
            "external_id": "item-1",
            "course_external_id": "C1",
            "course_name": "Course 1",
            "title": "First task",
            "due_time": future,
            "description": "first",
        },
        {
            "external_id": "item-2",
            "course_external_id": "C1",
            "course_name": "Course 1",
            "title": "Second task",
            "due_time": future,
            "description": "second",
        },
    ]
    task_repo = _FlakyTaskRepo()
    sm = _make_sm(client=_GoodClient(), parser=_StaticParser(items), task_repo=task_repo)

    result = sm.sync_from_teaching_site("u", "p")

    # Second task survived.
    assert result.tasks_new == 1
    assert any(t.external_id == "C1:item-2" for t in task_repo.added)
    # First task's failure surfaced — must mention its external_id.
    assert any("item-1" in err for err in result.errors), result.errors


def test_outer_fetch_failure_surfaces_as_ddl_failure():
    """When the fetch itself blows up, the sync result reports the legacy
    'DDL同步失败' message — the outer try is still in place for fetch+parse."""
    sm = _make_sm(client=_ExplodingClient(), parser=_StaticParser([]))

    result = sm.sync_from_teaching_site("u", "p")

    assert any("DDL同步失败" in err for err in result.errors), result.errors
    assert result.tasks_new == 0


def test_all_items_failing_still_returns_result():
    """Even if every item raises, ``sync_from_teaching_site`` should
    return a populated ``SyncResult`` (not propagate the exception)."""
    future = datetime.now() + timedelta(days=3)

    class _AlwaysFlakyRepo(_FakeTaskRepo):
        def find_by_external_id(self, external_id: str):
            raise RuntimeError(f"boom on {external_id}")

    items = [
        {"external_id": "a", "course_external_id": "C", "course_name": "C",
         "title": "A", "due_time": future, "description": ""},
        {"external_id": "b", "course_external_id": "C", "course_name": "C",
         "title": "B", "due_time": future, "description": ""},
    ]
    sm = _make_sm(
        client=_GoodClient(),
        parser=_StaticParser(items),
        task_repo=_AlwaysFlakyRepo(),
    )

    result = sm.sync_from_teaching_site("u", "p")

    assert isinstance(result, SyncResult)
    # Both items reported individually rather than collapsed into one.
    assert sum(1 for err in result.errors if "task " in err) == 2
