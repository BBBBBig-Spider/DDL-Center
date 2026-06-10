from __future__ import annotations

from app.services import credentials_store
from app.services.credentials_store import USERNAME_KEY, PASSWORD_KEY


def _isolate(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    monkeypatch.setattr(credentials_store, "ENV_PATH", env_path)
    monkeypatch.delenv(USERNAME_KEY, raising=False)
    monkeypatch.delenv(PASSWORD_KEY, raising=False)
    return env_path


def test_load_empty_when_no_file(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    username, password = credentials_store.load()
    assert username == ""
    assert password == ""
    assert credentials_store.is_logged_in() is False


def test_save_then_load_roundtrip(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    credentials_store.save("alice", "p@ss123")
    username, password = credentials_store.load()
    assert username == "alice"
    assert password == "p@ss123"
    assert credentials_store.is_logged_in() is True


def test_save_preserves_unrelated_lines_and_comments(monkeypatch, tmp_path) -> None:
    env_path = _isolate(monkeypatch, tmp_path)
    env_path.write_text(
        "# top comment\nDEEPSEEK_API_KEY=sk-abc\nOTHER=value\n",
        encoding="utf-8",
    )
    credentials_store.save("bob", "secret")
    text = env_path.read_text(encoding="utf-8")
    assert "# top comment" in text
    assert "DEEPSEEK_API_KEY=sk-abc" in text
    assert "OTHER=value" in text
    assert "PKU_USERNAME=bob" in text
    assert "PKU_PASSWORD=secret" in text


def test_clear_removes_only_pku_keys(monkeypatch, tmp_path) -> None:
    env_path = _isolate(monkeypatch, tmp_path)
    env_path.write_text(
        "# header\nDEEPSEEK_API_KEY=sk-xyz\nPKU_USERNAME=carol\nPKU_PASSWORD=hunter2\nKEEP=ok\n",
        encoding="utf-8",
    )
    credentials_store.clear()
    text = env_path.read_text(encoding="utf-8")
    assert "PKU_USERNAME" not in text
    assert "PKU_PASSWORD" not in text
    assert "# header" in text
    assert "DEEPSEEK_API_KEY=sk-xyz" in text
    assert "KEEP=ok" in text


def test_save_updates_existing_key_without_duplication(monkeypatch, tmp_path) -> None:
    env_path = _isolate(monkeypatch, tmp_path)
    credentials_store.save("dave", "first")
    credentials_store.save("dave", "second")
    text = env_path.read_text(encoding="utf-8")
    assert text.count("PKU_USERNAME=") == 1
    assert text.count("PKU_PASSWORD=") == 1
    username, password = credentials_store.load()
    assert username == "dave"
    assert password == "second"
