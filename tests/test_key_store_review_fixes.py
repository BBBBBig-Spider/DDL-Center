from __future__ import annotations

from app.network import key_store as key_store_module
from app.network.key_store import KeyStore


class FakeKeyring:
    def __init__(self) -> None:
        self.values = {}

    def set_password(self, service: str, key: str, value: str) -> None:
        self.values[(service, key)] = value

    def get_password(self, service: str, key: str):
        return self.values.get((service, key))

    def delete_password(self, service: str, key: str) -> None:
        self.values.pop((service, key), None)


class FakeSettingRepository:
    def __init__(self) -> None:
        self.values = {KeyStore.KEY_NAME: "old-plaintext-key"}

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> bool:
        return self.values.pop(key, None) is not None


def test_set_key_clears_old_repository_key_when_keyring_succeeds(monkeypatch) -> None:
    fake_keyring = FakeKeyring()
    repository = FakeSettingRepository()
    monkeypatch.setattr(key_store_module, "keyring", fake_keyring)

    store = KeyStore(repository)
    store.set_key("new-key")

    assert store.get_key() == "new-key"
    assert KeyStore.KEY_NAME not in repository.values
