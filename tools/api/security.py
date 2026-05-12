"""Small stdlib-only security helpers for the API layer."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

_PASSWORD_ITERATIONS = 240_000


def _secret() -> bytes:
    raw = os.getenv("AGARTHA_AUTH_SECRET") or os.getenv("API_KEY") or "dev-secret-change-me"
    return raw.encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(actual, expected)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    api_key = f"agrt_{secrets.token_urlsafe(32)}"
    return api_key, api_key[:10], hash_api_key(api_key)


def create_token(subject: str, *, expires_in: int, token_type: str = "access") -> str:
    payload = {
        "sub": subject,
        "typ": token_type,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    signature = hmac.new(_secret(), body, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{body.decode('ascii')}.{encoded_signature.decode('ascii')}"


def verify_token(token: str, *, token_type: str = "access") -> dict[str, Any] | None:
    try:
        body, encoded_signature = token.split(".", 1)
        body_bytes = body.encode("ascii")
        expected = base64.urlsafe_b64encode(
            hmac.new(_secret(), body_bytes, hashlib.sha256).digest()
        ).rstrip(b"=")
        if not hmac.compare_digest(encoded_signature.encode("ascii"), expected):
            return None
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except Exception:
        return None
    if payload.get("typ") != token_type:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
