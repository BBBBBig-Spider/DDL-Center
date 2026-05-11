"""
Probe script: verify PKU IAAA login → Blackboard token → campusLogin.

Usage:
    python scripts/probe_teaching_site.py

Reads PKU_USERNAME and PKU_PASSWORD from the environment (or .env file).
Prints a step-by-step status report; saves raw page snippets to data/ for
use as mock data.
"""

from __future__ import annotations

import os
import sys
import textwrap

# Allow running from project root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("PKU_USERNAME", "")
PASSWORD = os.getenv("PKU_PASSWORD", "")

if not USERNAME or not PASSWORD:
    print("ERROR: Set PKU_USERNAME and PKU_PASSWORD in your .env file or environment.")
    sys.exit(1)


def _step(label: str, ok: bool, detail: str = "") -> None:
    status = "OK " if ok else "FAIL"
    print(f"  [{status}] {label}")
    if detail:
        for line in textwrap.wrap(detail, width=80, initial_indent="         "):
            print(line)


def main() -> None:
    print("=" * 60)
    print("PKU Teaching Site Probe")
    print("=" * 60)

    # ── Step 1: fetch RSA public key ──────────────────────────────
    print("\n[1] Fetching RSA public key from IAAA...")
    import requests as _req
    from app.network.network_errors import NetworkError
    from app.config import IAAA_PUBKEY_URL

    session = _req.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (DDL-Center probe)"

    try:
        resp = session.get(IAAA_PUBKEY_URL, timeout=10)
        data = resp.json()
        ok = data.get("success", False)
        _step("GET " + IAAA_PUBKEY_URL, ok, data.get("key", "")[:60] + "…" if ok else str(data))
        pub_key_pem = data.get("key", "")
    except Exception as exc:
        _step("GET " + IAAA_PUBKEY_URL, False, str(exc))
        sys.exit(1)

    # ── Step 2: RSA-encrypt password ──────────────────────────────
    print("\n[2] Encrypting password with RSA public key...")
    try:
        import base64
        from Crypto.Cipher import PKCS1_v1_5
        from Crypto.PublicKey import RSA

        key = RSA.import_key(pub_key_pem)
        cipher = PKCS1_v1_5.new(key)
        encrypted_pwd = base64.b64encode(cipher.encrypt(PASSWORD.encode())).decode()
        _step("RSA encrypt", True, encrypted_pwd[:40] + "…")
    except Exception as exc:
        _step("RSA encrypt", False, str(exc))
        sys.exit(1)

    # ── Step 3: IAAA login ────────────────────────────────────────
    print("\n[3] Logging in via IAAA...")
    from app.config import IAAA_LOGIN_URL, BB_APPID, BB_REDIR_URL

    payload = {
        "appid": BB_APPID,
        "userName": USERNAME,
        "password": encrypted_pwd,
        "redirUrl": BB_REDIR_URL,
    }
    try:
        resp = session.post(
            IAAA_LOGIN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            timeout=10,
        )
        data = resp.json()
        ok = data.get("success", False)
        token = data.get("token", "")
        _step("POST oauthlogin.do", ok, f"token={token[:20]}…" if ok else str(data))
        if not ok:
            sys.exit(1)
    except Exception as exc:
        _step("POST oauthlogin.do", False, str(exc))
        sys.exit(1)

    # ── Step 4: campusLogin redirect ─────────────────────────────
    print("\n[4] Performing campusLogin redirect (Blackboard)...")
    import random

    rand = f"{random.random():.16f}"
    campus_url = f"{BB_REDIR_URL}?_rand={rand}&token={token}"
    try:
        resp = session.get(campus_url, timeout=10, allow_redirects=True)
        ok = resp.status_code < 400
        cookies = dict(session.cookies)
        _step(
            "GET campusLogin",
            ok,
            f"status={resp.status_code}  cookies={list(cookies.keys())}",
        )
    except Exception as exc:
        _step("GET campusLogin", False, str(exc))
        sys.exit(1)

    # ── Step 5: fetch a page and save as mock ────────────────────
    print("\n[5] Fetching DDL page (saving snippet as mock data)...")
    from app.config import MOCK_DDL_PATH, MOCK_SCHEDULE_PATH

    ddl_url = (
        "http://course.pku.edu.cn/webapps/bb-assignment-BBLEARN/execute/viewStudentSubmissions"
        "?course_id=_&mode=all"
    )
    try:
        resp = session.get(ddl_url, timeout=15, allow_redirects=True)
        ok = resp.status_code < 400
        _step("GET DDL page", ok, f"status={resp.status_code}  length={len(resp.text)}")
        if ok:
            os.makedirs(os.path.dirname(MOCK_DDL_PATH), exist_ok=True)
            with open(MOCK_DDL_PATH, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"         → Saved to {MOCK_DDL_PATH}")
    except Exception as exc:
        _step("GET DDL page", False, str(exc))

    print("\n" + "=" * 60)
    print("Probe complete. Check above for any FAIL items.")
    print("=" * 60)


if __name__ == "__main__":
    main()
