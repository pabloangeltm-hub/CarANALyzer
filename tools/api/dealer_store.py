"""Async SQLite helpers for dealer records."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from tools.api.schemas import DealerCreate, DealerOut, DealerUpdate
from tools.api.security import generate_api_key, hash_api_key
from tools.api.services.auth_service import hash_password
from tools.utils import db

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_DEALERS_MIGRATION = _MIGRATIONS_DIR / "002_dealers.sql"
_DEALERS_MIGRATION_COLUMNS: dict[str, str] = {
    "name": "TEXT",
    "email": "TEXT",
    "password_hash": "TEXT",
    "plan": "TEXT NOT NULL DEFAULT 'free'",
    "api_key_hash": "TEXT",
    "api_key_prefix": "TEXT",
    "stripe_customer_id": "TEXT",
    "created_at": "TEXT",
    "active": "INTEGER NOT NULL DEFAULT 1",
    "calls_today": "INTEGER NOT NULL DEFAULT 0",
}


def _dealers_schema_sql() -> str:
    return _DEALERS_MIGRATION.read_text(encoding="utf-8")


async def _ensure_dealer_columns(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("PRAGMA table_info(dealers)")
    existing = {row["name"] for row in await cursor.fetchall()}
    for column_name, column_type in _DEALERS_MIGRATION_COLUMNS.items():
        if column_name not in existing:
            await conn.execute(f"ALTER TABLE dealers ADD COLUMN {column_name} {column_type}")


async def ensure_dealers_schema(conn: aiosqlite.Connection) -> None:
    schema_sql = _dealers_schema_sql()
    try:
        await conn.executescript(schema_sql)
    except aiosqlite.OperationalError as exc:
        if "no such column" not in str(exc).lower():
            raise
        await _ensure_dealer_columns(conn)
        await conn.executescript(schema_sql)
    await _ensure_dealer_columns(conn)


def row_to_dealer(row: aiosqlite.Row | dict[str, Any]) -> DealerOut:
    data = dict(row)
    data["active"] = bool(data.get("active"))
    return DealerOut.model_validate(data)


async def create_dealer(payload: DealerCreate) -> tuple[DealerOut, str]:
    api_key, prefix, key_hash = generate_api_key()
    created_at = datetime.now().isoformat(timespec="seconds")
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute(
            """
            INSERT INTO dealers
                (name, email, password_hash, plan, api_key_hash, api_key_prefix, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.email,
                hash_password(payload.password),
                payload.plan,
                key_hash,
                prefix,
                created_at,
            ),
        )
        dealer_id = cursor.lastrowid
        await conn.commit()
        row = await get_dealer_row_by_id(dealer_id, conn=conn)
        if row is None:
            raise RuntimeError("created dealer could not be reloaded")
        return row_to_dealer(row), api_key


async def update_dealer(dealer_id: int, payload: DealerUpdate) -> DealerOut | None:
    fields: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("name", payload.name),
        ("plan", payload.plan),
        ("active", int(payload.active) if payload.active is not None else None),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)

    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        if fields:
            await conn.execute(
                f"UPDATE dealers SET {', '.join(fields)} WHERE id = ?",
                [*params, dealer_id],
            )
            await conn.commit()
        row = await get_dealer_row_by_id(dealer_id, conn=conn)
    return row_to_dealer(row) if row else None


async def list_dealers(limit: int, offset: int) -> list[DealerOut]:
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute(
            "SELECT * FROM dealers ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
    return [row_to_dealer(row) for row in rows]


async def get_dealer_row_by_id(
    dealer_id: int,
    *,
    conn: aiosqlite.Connection | None = None,
) -> aiosqlite.Row | None:
    if conn is not None:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute("SELECT * FROM dealers WHERE id = ?", (dealer_id,))
        return await cursor.fetchone()

    async with db.get_connection() as owned_conn:
        await ensure_dealers_schema(owned_conn)
        cursor = await owned_conn.execute("SELECT * FROM dealers WHERE id = ?", (dealer_id,))
        return await cursor.fetchone()


async def get_dealer_by_id(dealer_id: int) -> DealerOut | None:
    row = await get_dealer_row_by_id(dealer_id)
    return row_to_dealer(row) if row else None


async def get_dealer_row_by_email(email: str) -> aiosqlite.Row | None:
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute("SELECT * FROM dealers WHERE email = ?", (email,))
        return await cursor.fetchone()


async def get_dealer_row_by_api_key(api_key: str) -> aiosqlite.Row | None:
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        cursor = await conn.execute(
            "SELECT * FROM dealers WHERE api_key_hash = ? AND active = 1",
            (hash_api_key(api_key),),
        )
        return await cursor.fetchone()


async def rotate_api_key(dealer_id: int) -> tuple[DealerOut, str] | None:
    api_key, prefix, key_hash = generate_api_key()
    async with db.get_connection() as conn:
        await ensure_dealers_schema(conn)
        await conn.execute(
            """
            UPDATE dealers
            SET api_key_hash = ?, api_key_prefix = ?
            WHERE id = ? AND active = 1
            """,
            (key_hash, prefix, dealer_id),
        )
        await conn.commit()
        row = await get_dealer_row_by_id(dealer_id, conn=conn)
    return (row_to_dealer(row), api_key) if row else None
