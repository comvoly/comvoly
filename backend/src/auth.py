"""Small owner-session boundary for the local Comvoly MVP.

This deliberately uses only the Python standard library. Production community
accounts should move to a managed identity provider before the private pilot.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from http.cookies import SimpleCookie


SESSION_COOKIE = "comvoly_session"
SESSION_SECONDS = 12 * 60 * 60
PBKDF2_ITERATIONS = 600_000


def authentication_configured() -> bool:
    return bool(os.getenv("COMVOLY_OWNER_PASSWORD_HASH") and os.getenv("COMVOLY_SESSION_SECRET"))


def hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Use an owner password with at least 12 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None = None) -> bool:
    encoded = encoded or os.getenv("COMVOLY_OWNER_PASSWORD_HASH", "")
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session(now: int | None = None) -> str:
    secret = os.getenv("COMVOLY_SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("Owner authentication has not been configured.")
    payload = _encode(json.dumps({"role": "owner", "exp": (now or int(time.time())) + SESSION_SECONDS}, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_session(token: str, now: int | None = None) -> bool:
    secret = os.getenv("COMVOLY_SESSION_SECRET", "")
    try:
        payload, signature = token.split(".", 1)
        expected = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
        data = json.loads(_decode(payload))
        return bool(secret) and hmac.compare_digest(signature, expected) and data.get("role") == "owner" and int(data["exp"]) >= (now or int(time.time()))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def session_from_cookie(header: str | None) -> str:
    if not header:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(header)
        return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else ""
    except Exception:
        return ""


def session_cookie(token: str, secure: bool = False) -> str:
    parts = [f"{SESSION_COOKIE}={token}", "Path=/", f"Max-Age={SESSION_SECONDS}", "HttpOnly", "SameSite=Strict"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def expired_session_cookie(secure: bool = False) -> str:
    parts = [f"{SESSION_COOKIE}=", "Path=/", "Max-Age=0", "HttpOnly", "SameSite=Strict"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)
