import asyncio

import aiosqlite

from tools.api.dealer_store import ensure_dealers_schema


EXPECTED_COLUMNS = {
    "id",
    "name",
    "email",
    "password_hash",
    "plan",
    "api_key_hash",
    "api_key_prefix",
    "stripe_customer_id",
    "created_at",
    "active",
    "calls_today",
}


def test_dealers_schema_migration_is_idempotent(tmp_path):
    async def _run() -> tuple[set[str], set[str], int]:
        async with aiosqlite.connect(tmp_path / "dealers.db") as conn:
            conn.row_factory = aiosqlite.Row
            await ensure_dealers_schema(conn)
            await ensure_dealers_schema(conn)
            await conn.commit()

            columns_cursor = await conn.execute("PRAGMA table_info(dealers)")
            columns = {row["name"] for row in await columns_cursor.fetchall()}

            indexes_cursor = await conn.execute("PRAGMA index_list(dealers)")
            indexes = {row["name"] for row in await indexes_cursor.fetchall()}

            inserted = await conn.execute(
                """
                INSERT INTO dealers
                    (name, email, password_hash, plan, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Agartha Dealer", "dealer@example.com", "hash", "trial", "2026-05-09T00:00:00"),
            )
            await conn.commit()
            return columns, indexes, int(inserted.lastrowid)

    columns, indexes, dealer_id = asyncio.run(_run())

    assert EXPECTED_COLUMNS.issubset(columns)
    assert "idx_dealers_email_unique" in indexes
    assert "idx_dealers_api_key_hash_unique" in indexes
    assert "idx_dealers_plan_active" in indexes
    assert dealer_id == 1


def test_dealers_schema_adds_missing_f4_columns_to_existing_table(tmp_path):
    async def _run() -> set[str]:
        async with aiosqlite.connect(tmp_path / "legacy_dealers.db") as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute(
                """
                CREATE TABLE dealers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT
                )
                """
            )
            await ensure_dealers_schema(conn)
            await conn.commit()
            cursor = await conn.execute("PRAGMA table_info(dealers)")
            return {row["name"] for row in await cursor.fetchall()}

    columns = asyncio.run(_run())

    assert EXPECTED_COLUMNS.issubset(columns)
