"""Database connection dependency for FastAPI routers."""

from __future__ import annotations

from collections.abc import AsyncIterator

import aiosqlite

from tools.utils import db


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    async with db.get_connection() as conn:
        yield conn
