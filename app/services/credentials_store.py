from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"

USERNAME_KEY = "PKU_USERNAME"
PASSWORD_KEY = "PKU_PASSWORD"

_PKU_LINE_RE = re.compile(r"^(PKU_USERNAME|PKU_PASSWORD)\s*=", re.M)


def _read_env_text() -> str:
    path = ENV_PATH
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _parse_pairs(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pairs[key.strip()] = value.strip()
    return pairs


def load() -> tuple[str, str]:
    text = _read_env_text()
    pairs = _parse_pairs(text)
    return pairs.get(USERNAME_KEY, ""), pairs.get(PASSWORD_KEY, "")


def _upsert_line(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.M)
    new_line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(new_line, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + new_line + "\n"


def save(username: str, password: str) -> None:
    text = _read_env_text()
    text = _upsert_line(text, USERNAME_KEY, username)
    text = _upsert_line(text, PASSWORD_KEY, password)
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text(text, encoding="utf-8")
    os.environ[USERNAME_KEY] = username
    os.environ[PASSWORD_KEY] = password


def clear() -> None:
    text = _read_env_text()
    if text:
        new_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{USERNAME_KEY}=") or stripped.startswith(f"{PASSWORD_KEY}="):
                continue
            new_lines.append(line)
        new_text = "\n".join(new_lines)
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        if new_text:
            ENV_PATH.write_text(new_text, encoding="utf-8")
        else:
            try:
                ENV_PATH.unlink()
            except FileNotFoundError:
                pass
    os.environ.pop(USERNAME_KEY, None)
    os.environ.pop(PASSWORD_KEY, None)


def is_logged_in() -> bool:
    username, password = load()
    return bool(username) and bool(password)
