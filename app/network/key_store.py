"""Small API-key store for AI features."""
from __future__ import annotations

import os
from typing import Optional

try:
    import keyring
except ImportError:  # pragma: no cover - keyring is optional at runtime
    keyring = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is listed in requirements
    load_dotenv = None


class KeyStore:
    SERVICE_NAME = "DDL-Center"
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
        if self._set_keyring_key(key):
            self._delete_repository_key()
            return
        if self.setting_repository is None:
            os.environ[self.ENV_NAMES[0]] = key
            return
        self.setting_repository.set(self.KEY_NAME, key)

    def get_key(self) -> Optional[str]:
        key = self._get_keyring_key()
        if key:
            return key
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
        self._delete_keyring_key()
        self._delete_repository_key()
        for name in self.ENV_NAMES:
            os.environ.pop(name, None)

    def has_key(self) -> bool:
        return self.get_key() is not None

    def _set_keyring_key(self, key: str) -> bool:
        if keyring is None:
            return False
        try:
            keyring.set_password(self.SERVICE_NAME, self.KEY_NAME, key)
            return True
        except Exception:
            return False

    def _get_keyring_key(self) -> Optional[str]:
        if keyring is None:
            return None
        try:
            key = keyring.get_password(self.SERVICE_NAME, self.KEY_NAME)
        except Exception:
            return None
        return key.strip() if key else None

    def _delete_keyring_key(self) -> None:
        if keyring is None:
            return
        try:
            keyring.delete_password(self.SERVICE_NAME, self.KEY_NAME)
        except Exception:
            return

    def _delete_repository_key(self) -> None:
        if self.setting_repository is None:
            return
        try:
            self.setting_repository.delete(self.KEY_NAME)
        except Exception:
            return
