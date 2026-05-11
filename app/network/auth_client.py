"""
PKU IAAA OAuth authentication client.

Flow:
  1. GET RSA public key from IAAA
  2. RSA-encrypt the password (PKCS#1 v1.5, matches JSEncrypt behaviour)
  3. POST credentials to IAAA oauthlogin.do → receive token
  4. Visit app-specific campusLogin URL with token to obtain a session cookie
"""

from __future__ import annotations

import base64
import random
import time
from dataclasses import dataclass, field

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from app.config import (
    BB_APPID,
    BB_REDIR_URL,
    IAAA_LOGIN_URL,
    IAAA_PUBKEY_URL,
)
from app.network.network_errors import AuthError, ConnectionError, ParseError


@dataclass
class AuthSession:
    token: str
    username: str
    appid: str
    redir_url: str
    session: requests.Session = field(default_factory=requests.Session)


def _fetch_rsa_public_key(session: requests.Session) -> str:
    """Return the PEM public key string from IAAA."""
    try:
        resp = session.get(IAAA_PUBKEY_URL, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f"Failed to fetch RSA public key: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise ParseError("RSA public key response is not valid JSON") from exc

    if not data.get("success"):
        raise ParseError(f"IAAA returned failure for public key request: {data}")

    return data["key"]


def _rsa_encrypt(public_key_pem: str, plaintext: str) -> str:
    """Encrypt plaintext with the given RSA public key (PKCS#1 v1.5)."""
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_v1_5.new(key)
    encrypted_bytes = cipher.encrypt(plaintext.encode("utf-8"))
    return base64.b64encode(encrypted_bytes).decode("utf-8")


def _iaaa_login(
    session: requests.Session,
    username: str,
    encrypted_password: str,
    appid: str,
    redir_url: str,
) -> str:
    """POST to IAAA and return the token string."""
    payload = {
        "appid": appid,
        "userName": username,
        "password": encrypted_password,
        "redirUrl": redir_url,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

    try:
        resp = session.post(IAAA_LOGIN_URL, data=payload, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f"IAAA login request failed: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise ParseError("IAAA login response is not valid JSON") from exc

    if not data.get("success"):
        errors = data.get("errors", {})
        raise AuthError(
            code=errors.get("code", ""),
            msg=errors.get("msg", "Unknown IAAA error"),
        )

    return data["token"]


def _campus_login(
    session: requests.Session,
    token: str,
    redir_url: str,
) -> None:
    """Visit the app-specific campusLogin URL to set session cookies."""
    rand = f"{random.random():.16f}"
    url = f"{redir_url}?_rand={rand}&token={token}"
    try:
        resp = session.get(url, timeout=10, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f"Campus login redirect failed: {exc}") from exc


class AuthClient:
    """Handles PKU IAAA authentication for a single app (e.g. Blackboard)."""

    def __init__(
        self,
        appid: str = BB_APPID,
        redir_url: str = BB_REDIR_URL,
    ) -> None:
        self._appid = appid
        self._redir_url = redir_url
        self._session: requests.Session | None = None
        self._auth_session: AuthSession | None = None

    def login(self, username: str, password: str) -> AuthSession:
        """
        Authenticate with IAAA and perform campusLogin for the target app.
        Returns an AuthSession containing the token and a cookie-bearing session.
        """
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (DDL-Center/1.0)"})

        pub_key = _fetch_rsa_public_key(session)
        encrypted_pwd = _rsa_encrypt(pub_key, password)
        token = _iaaa_login(session, username, encrypted_pwd, self._appid, self._redir_url)
        _campus_login(session, token, self._redir_url)

        self._session = session
        self._auth_session = AuthSession(
            token=token,
            username=username,
            appid=self._appid,
            redir_url=self._redir_url,
            session=session,
        )
        return self._auth_session

    def logout(self) -> None:
        if self._session:
            self._session.close()
        self._session = None
        self._auth_session = None

    def is_logged_in(self) -> bool:
        return self._auth_session is not None

    @property
    def current_session(self) -> AuthSession | None:
        return self._auth_session
