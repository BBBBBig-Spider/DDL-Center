"""Small API-key store for AI features.

The preferred demo path is environment variables. If a SettingRepository is
provided, user-entered keys are stored there. This keeps the implementation
inside the allowed manager/network layers and avoids adding dependencies.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is listed in requirements
    load_dotenv = None


class KeyStore:
    KEY_NAME = "deepseek_api_key"
    ENV_NAMES = ("DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "OPENAI_API_KEY")

    def __init__(self, setting_repository=None) -> None:
        self.setting_repository = setting_repository
        if load_dotenv is not None:
            load_dotenv()

    def set_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be str")
        key = key.strip()
        if not key:
            raise ValueError("key cannot be empty")
        if self.setting_repository is None:
            os.environ[self.ENV_NAMES[0]] = key
            return
        self.setting_repository.set(self.KEY_NAME, key)

    def get_key(self) -> Optional[str]:
        if self.setting_repository is not None:
            key = self.setting_repository.get(self.KEY_NAME)
            if key:
                return key
        for name in self.ENV_NAMES:
            key = os.getenv(name)
            if key:
                return key.strip()
        return None

    def delete_key(self) -> None:
        if self.setting_repository is not None:
            self.setting_repository.delete(self.KEY_NAME)
        for name in self.ENV_NAMES:
            os.environ.pop(name, None)

    def has_key(self) -> bool:
        return self.get_key() is not None
