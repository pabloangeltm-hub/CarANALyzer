"""Production auth primitives for F4.

Routers still use the F2 stdlib helpers until F4-T06 wires this service in.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Literal

import aiosqlite
import bcrypt
import jwt

from tools.api.security import verify_password as verify_legacy_password
from tools.utils import db

TokenType = Literal["access", "refresh"]

ACCESS_TOKEN_SECONDS = 3600
REFRESH_TOKEN_SECONDS = 7 * 24 * 3600
JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    return (
        os.getenv("JWT_SECRET")
        or os.getenv("AGARTHA_AUTH_SECRET")
        or os.getenv("API_KEY")
        or "dev-secret-change-me"
    )


def _password_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) <= 72:
        return raw
    return hashlib.sha256(raw).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        return verify_legacy_password(password, stored_hash)
    try:
        return bcrypt.checkpw(_password_bytes(password), stored_hash.encode("ascii"))
    except (TypeError, ValueError):
        return False


def create_jwt(
    subject: str | int,
    *,
    token_type: TokenType = "access",
    expires_in: int | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    ttl = expires_in or (
        ACCESS_TOKEN_SECONDS if token_type == "access" else REFRESH_TOKEN_SECONDS
    )
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": secrets.token_urlsafe(24),
    }
    if additional_claims:
        payload.update(additional_claims)
        payload["sub"] = str(subject)
        payload["typ"] = token_type
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_jwt(
    token: str,
    *,
    token_type: TokenType | None = None,
    verify_exp: bool = True,
) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": verify_exp},
        )
    except jwt.PyJWTError:
        return None
    if token_type is not None and payload.get("typ") != token_type:
        return None
    return payload


async def ensure_token_blacklist_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS auth_token_blacklist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            jti        TEXT NOT NULL UNIQUE,
            token_type TEXT NOT NULL,
            subject    TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            revoked_at TEXT NOT NULL,
            reason     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_auth_token_blacklist_expires_at
            ON auth_token_blacklist(expires_at);

        CREATE INDEX IF NOT EXISTS idx_auth_token_blacklist_subject
            ON auth_token_blacklist(subject);
        """
    )


async def revoke_token(token: str, *, reason: str = "logout") -> bool:
    payload = decode_jwt(token, verify_exp=False)
    if not payload:
        return False
    jti = payload.get("jti")
    subject = payload.get("sub")
    token_type = payload.get("typ")
    expires_at = payload.get("exp")
    if not all((jti, subject, token_type, expires_at)):
        return False

    async with db.get_connection() as conn:
        await ensure_token_blacklist_schema(conn)
        await conn.execute(
            """
            INSERT INTO auth_token_blacklist
                (jti, token_type, subject, expires_at, revoked_at, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(jti) DO UPDATE SET
                revoked_at = excluded.revoked_at,
                reason     = excluded.reason
            """,
            (
                str(jti),
                str(token_type),
                str(subject),
                int(expires_at),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                reason,
            ),
        )
        await conn.commit()
    return True


async def is_token_revoked(jti: str) -> bool:
    async with db.get_connection() as conn:
        await ensure_token_blacklist_schema(conn)
        cursor = await conn.execute(
            "SELECT 1 FROM auth_token_blacklist WHERE jti = ?",
            (jti,),
        )
        return await cursor.fetchone() is not None


async def verify_jwt(
    token: str,
    *,
    token_type: TokenType = "access",
    check_blacklist: bool = True,
) -> dict[str, Any] | None:
    payload = decode_jwt(token, token_type=token_type)
    if not payload:
        return None
    jti = payload.get("jti")
    if check_blacklist and jti and await is_token_revoked(str(jti)):
        return None
    return payload
