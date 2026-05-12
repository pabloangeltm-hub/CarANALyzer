import asyncio

import pytest

from tools.api.services.auth_service import (
    create_jwt,
    decode_jwt,
    ensure_token_blacklist_schema,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_jwt,
    verify_password,
)
from tools.utils import db


@pytest.fixture()
def auth_service_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "auth_service.db")
    db._backup_done = False
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def test_bcrypt_password_hashing_verifies_passwords():
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$2")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
    assert not verify_password("correct horse battery staple", "not-a-bcrypt-hash")


def test_bcrypt_password_hashing_handles_long_passwords():
    password = "x" * 120

    password_hash = hash_password(password)

    assert verify_password(password, password_hash)
    assert not verify_password(password + "!", password_hash)


def test_jwt_encode_decode_and_token_type_validation(auth_service_db):
    token = create_jwt(
        42,
        token_type="access",
        expires_in=3600,
        additional_claims={"plan": "premium"},
    )

    payload = decode_jwt(token, token_type="access")

    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["typ"] == "access"
    assert payload["plan"] == "premium"
    assert payload["jti"]
    assert decode_jwt(token, token_type="refresh") is None


def test_jwt_rejects_expired_or_tampered_tokens(auth_service_db):
    expired = create_jwt("dealer-1", token_type="access", expires_in=-1)
    valid = create_jwt("dealer-1", token_type="access", expires_in=3600)
    tampered = valid.rsplit(".", 1)[0] + ".invalid-signature"

    assert decode_jwt(expired, token_type="access") is None
    assert decode_jwt(tampered, token_type="access") is None


def test_token_blacklist_revokes_jwt(auth_service_db):
    async def _run() -> tuple[bool, bool, bool]:
        token = create_jwt("dealer-1", token_type="access", expires_in=3600)
        payload = decode_jwt(token, token_type="access")
        assert payload is not None
        before = await verify_jwt(token, token_type="access")
        revoked = await revoke_token(token, reason="test")
        after = await verify_jwt(token, token_type="access")
        row_exists = await is_token_revoked(payload["jti"])
        return before is not None, revoked, after is None and row_exists

    assert asyncio.run(_run()) == (True, True, True)


def test_blacklist_schema_is_idempotent(auth_service_db):
    async def _run() -> set[str]:
        async with db.get_connection() as conn:
            await ensure_token_blacklist_schema(conn)
            await ensure_token_blacklist_schema(conn)
            cursor = await conn.execute("PRAGMA table_info(auth_token_blacklist)")
            return {row["name"] for row in await cursor.fetchall()}

    columns = asyncio.run(_run())

    assert {"id", "jti", "token_type", "subject", "expires_at", "revoked_at", "reason"}.issubset(
        columns
    )
