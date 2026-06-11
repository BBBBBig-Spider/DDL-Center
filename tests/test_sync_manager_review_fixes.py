from __future__ import annotations

from datetime import datetime, timedelta

from app.managers.sync_manager import SyncManager
from app.models.task import Task


def test_task_sync_hash_ignores_local_timestamps_and_state() -> None:
    first = Task(
        title="same ddl",
        due_time=datetime(2026, 6, 5, 23, 59),
        source="sync",
        external_id="ddl-1",
        raw_payload='{"id":"ddl-1"}',
    )
    second = Task(
        title="same ddl",
        due_time=datetime(2026, 6, 5, 23, 59),
        source="sync",
        external_id="ddl-1",
        raw_payload='{"id":"ddl-1"}',
        created_at=datetime.now() + timedelta(days=1),
        updated_at=datetime.now() + timedelta(days=2),
        status="done",
        user_modified=True,
    )

    assert SyncManager._hash_object(first) == SyncManager._hash_object(second)


def test_task_sync_hash_changes_when_external_content_changes() -> None:
    first = Task(
        title="same ddl",
        due_time=datetime(2026, 6, 5, 23, 59),
        source="sync",
        external_id="ddl-1",
        raw_payload='{"id":"ddl-1","version":1}',
    )
    second = Task(
        title="same ddl",
        due_time=datetime(2026, 6, 6, 23, 59),
        source="sync",
        external_id="ddl-1",
        raw_payload='{"id":"ddl-1","version":2}',
    )

    assert SyncManager._hash_object(first) != SyncManager._hash_object(second)
