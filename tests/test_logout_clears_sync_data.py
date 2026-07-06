"""退出登录 = 清空所有本地用户数据。

This is a contract test: logout must wipe the DB file, theme palette
file, and credentials, while preserving the Deepseek API key. It does
NOT test the GUI restart path (covered by integration / manual test).

This file replaces the previous test_logout_clears_sync_data contract:
logout no longer surgically removes synced rows — it now wipes the
whole DB file and resets the app to first-launch state.
"""
from __future__ import annotations

from pathlib import Path


def test_logout_deletes_db_and_palette_and_credentials(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create the three artifacts that logout should remove.
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db = data_dir / "ddl_center.db"
    db.write_bytes(b"\x00" * 16)
    palette = data_dir / ".theme_palette"
    palette.write_text("ocean_blue", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("PKU_USERNAME=foo\nPKU_PASSWORD=bar\n", encoding="utf-8")

    # Point credentials_store at the temp .env so its clear() touches our
    # fixture file rather than the real project root.
    from app.services import credentials_store
    monkeypatch.setattr(credentials_store, "ENV_PATH", env)

    from app.managers.app_facade import AppFacade

    class _FakeDB:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    facade = AppFacade(task_manager=None)
    facade.db_manager = _FakeDB()

    summary = facade.logout_and_reset_local_state()

    assert summary["db_deleted"] is True
    assert summary["theme_palette_deleted"] is True
    assert summary["credentials_cleared"] is True
    assert facade.db_manager.closed is True
    assert not db.exists()
    assert not palette.exists()
    # credentials_store.clear() removes the username/password lines from
    # .env — when those were the only lines the file is unlinked entirely.
    if env.exists():
        contents = env.read_text(encoding="utf-8")
        assert "PKU_USERNAME=" not in contents
        assert "PKU_PASSWORD=" not in contents


def test_logout_handles_missing_artifacts_gracefully(tmp_path, monkeypatch):
    """Nothing to delete is fine — logout still succeeds."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    from app.services import credentials_store
    monkeypatch.setattr(credentials_store, "ENV_PATH", tmp_path / ".env")

    from app.managers.app_facade import AppFacade
    facade = AppFacade(task_manager=None)  # no db_manager attr — handled by getattr in impl

    summary = facade.logout_and_reset_local_state()
    assert summary["db_deleted"] is False
    assert summary["theme_palette_deleted"] is False
    # credentials_cleared is True even when there's nothing to clear —
    # clear() is idempotent and only fails on actual I/O errors.
    assert summary["credentials_cleared"] is True


def test_logout_does_not_touch_keyring(tmp_path, monkeypatch):
    """The Deepseek API key lives in the OS keyring, not the DB file.
    Logout must NEVER touch it."""
    monkeypatch.chdir(tmp_path)

    from app.services import credentials_store
    monkeypatch.setattr(credentials_store, "ENV_PATH", tmp_path / ".env")

    calls = []

    # Stub keyring at the module level so any logout-time use would record.
    import keyring
    monkeypatch.setattr(keyring, "delete_password",
                        lambda *a, **kw: calls.append(("delete", a, kw)))
    monkeypatch.setattr(keyring, "set_password",
                        lambda *a, **kw: calls.append(("set", a, kw)))

    from app.managers.app_facade import AppFacade
    facade = AppFacade(task_manager=None)
    facade.logout_and_reset_local_state()

    # Logout did not call delete_password / set_password on keyring.
    assert calls == []
