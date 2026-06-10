"""SyncManager._sync_tasks must not overwrite user-edited sync tasks.

A task that came from the teaching site keeps its row when re-synced — the
existing-by-external_id check returns the row unchanged, regardless of
user_modified flag. This locks that contract so a future "smart merge"
refactor can't silently regress it.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.managers.sync_manager import SyncManager
from app.models.sync_result import SyncResult
from app.models.task import Task


class _FakeTaskRepo:
    def __init__(self, existing: Task):
        self._existing = existing
        self.added: list[Task] = []
        self.updated: list[Task] = []

    def find_by_external_id(self, external_id: str):
        if self._existing.external_id == external_id:
            return self._existing
        return None

    def add(self, task):
        self.added.append(task)
        return 999

    def update(self, task):
        self.updated.append(task)
        return True

    def purge_hidden_overdue(self, _now):
        return 0


class _NoopSyncRepo:
    def upsert_record(self, _record):
        return 1

    def get_record(self, _source_type, _external_id):
        return None


def _make_manager(task_repo) -> SyncManager:
    return SyncManager(
        auth_client=None,
        teaching_site_client=None,
        ddl_parser=None,
        schedule_parser=None,
        exam_parser=None,
        task_repository=task_repo,
        course_repository=None,
        schedule_repository=None,
        exam_repository=None,
        sync_repository=_NoopSyncRepo(),
    )


def test_user_edited_sync_task_is_not_overwritten_on_resync() -> None:
    # User edited title/description on a sync task; user_modified=True.
    edited = Task(
        id=42,
        title="Lab4（已改名）",
        due_time=datetime.now() + timedelta(days=10),
        description="本地补的笔记",
        source="sync",
        external_id="contentListItem:_1624444_1",
        user_modified=True,
    )
    repo = _FakeTaskRepo(edited)
    sm = _make_manager(repo)

    # Fresh upstream copy carrying upstream's title and description.
    upstream = Task(
        title="Lab4（教学网原标题）",
        due_time=edited.due_time,
        description="教学网原描述",
        source="sync",
        external_id="contentListItem:_1624444_1",
        raw_payload="{}",
    )

    result = SyncResult()
    sm._sync_tasks([upstream], result)

    # Existing row is left alone — no add, no update.
    assert repo.added == []
    assert repo.updated == []
    assert result.tasks_unchanged == 1
    assert result.tasks_new == 0

    # And the local edits survive.
    assert edited.title == "Lab4（已改名）"
    assert edited.description == "本地补的笔记"
    assert edited.user_modified is True


def test_unedited_sync_task_also_kept_unchanged_on_resync() -> None:
    """Even without user edits, a re-sync hits the same 'existing → unchanged'
    branch — this catches accidental upstream-overwrite regressions."""
    existing = Task(
        id=7,
        title="Lab4",
        due_time=datetime.now() + timedelta(days=10),
        source="sync",
        external_id="contentListItem:_1624444_1",
    )
    repo = _FakeTaskRepo(existing)
    sm = _make_manager(repo)

    upstream = Task(
        title="Lab4 - upstream tweak",
        due_time=existing.due_time,
        source="sync",
        external_id="contentListItem:_1624444_1",
        raw_payload="{}",
    )

    result = SyncResult()
    sm._sync_tasks([upstream], result)

    assert repo.added == []
    assert repo.updated == []
    assert result.tasks_unchanged == 1
