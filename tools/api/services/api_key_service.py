"""API key generation, hashing, validation and rotation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass

from tools.api.dealer_store import ensure_dealers_schema, row_to_dealer
from tools.api.schemas import DealerOut
from tools.utils import db

API_KEY_PREFIX = "agrt_"
API_KEY_VISIBLE_PREFIX_CHARS = 10


@dataclass(frozen=True)
class APIKeyMaterial:
    api_key: str
    prefix: str
    key_hash: str


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(api_key: str, stored_hash: str | None) -> bool:
    if not api_key or not stored_hash:
        return False
    return hmac.compare_digest(hash_api_key(api_key), stored_hash)


def generate_api_key() -> APIKeyMaterial:
    api_key = f"{API_KEY_PREFIX}{uuid.uuid4().hex}_{secrets.token_urlsafe(24)}"
    return APIKeyMaterial(
        api_key=api_key,
        prefix=api_key[:API_KEY_VISIBLE_PREFIX_CHARS],
        key_hash=hash_api_key(api_key),
    )


async def get_dealer_by_api_key(api_key: str) -> DealerOut | None:
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute(
            "SELECT * FROM dealers WHERE api_key_hash = ? AND active = 1",
            (hash_api_key(api_key),),
        )
        row = await cursor.fetchone()
    return row_to_dealer(row) if row else None


async def rotate_dealer_api_key(dealer_id: int) -> tuple[DealerOut, APIKeyMaterial] | None:
    material = generate_api_key()
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute(
            """
            UPDATE dealers
            SET api_key_hash = ?, api_key_prefix = ?
            WHERE id = ? AND active = 1
            """,
            (material.key_hash, material.prefix, dealer_id),
        )
        if cursor.rowcount == 0:
            await conn.rollback()
            return None
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM dealers WHERE id = ?", (dealer_id,))
        row = await cursor.fetchone()
    return (row_to_dealer(row), material) if row else None
