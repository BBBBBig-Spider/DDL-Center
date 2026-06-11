from __future__ import annotations

from app.managers.app_facade import AppFacade
from app.services import credentials_store


class _FakeTaskRepo:
    def __init__(self) -> None:
        self.calls = 0

    def delete_all_synced(self) -> int:
        self.calls += 1
        return 7


class _FakeExamRepo:
    def __init__(self) -> None:
        self.calls = 0

    def delete_all_synced(self) -> int:
        self.calls += 1
        return 3


class _FakeSyncRepo:
    def __init__(self) -> None:
        self.calls = 0

    def clear_ai_reviews(self) -> int:
        self.calls += 1
        return 5


class _FakeSyncManager:
    def __init__(self) -> None:
        self.task_repository = _FakeTaskRepo()
        self.exam_repository = _FakeExamRepo()
        self.sync_repository = _FakeSyncRepo()
        self.auth_client = object()


def test_logout_and_clear_sync_data_invokes_repos_and_credentials(monkeypatch) -> None:
    sync_manager = _FakeSyncManager()
    facade = AppFacade(task_manager=None, sync_manager=sync_manager)

    cleared = {"called": 0}

    def fake_clear() -> None:
        cleared["called"] += 1

    monkeypatch.setattr(credentials_store, "clear", fake_clear)

    counts = facade.logout_and_clear_sync_data()

    assert sync_manager.task_repository.calls == 1
    assert sync_manager.exam_repository.calls == 1
    assert sync_manager.sync_repository.calls == 1
    assert cleared["called"] == 1
    assert counts == {
        "tasks_deleted": 7,
        "exams_deleted": 3,
        "reviews_deleted": 5,
    }


def test_logout_returns_zero_counts_when_repos_missing(monkeypatch) -> None:
    class _BareSyncManager:
        auth_client = object()

    facade = AppFacade(task_manager=None, sync_manager=_BareSyncManager())

    cleared = {"called": 0}

    def fake_clear() -> None:
        cleared["called"] += 1

    monkeypatch.setattr(credentials_store, "clear", fake_clear)

    counts = facade.logout_and_clear_sync_data()

    assert cleared["called"] == 1
    assert counts == {
        "tasks_deleted": 0,
        "exams_deleted": 0,
        "reviews_deleted": 0,
    }
