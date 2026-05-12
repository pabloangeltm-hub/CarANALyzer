"""Service layer for dealer persistence and account state."""

from __future__ import annotations

from typing import Any

from tools.api.dealer_store import (
    create_dealer,
    ensure_dealers_schema,
    get_dealer_by_id,
    get_dealer_row_by_email,
    list_dealers,
    row_to_dealer,
    update_dealer,
)
from tools.api.models.plan import PlanName
from tools.api.schemas import DealerCreate, DealerOut, DealerUpdate
from tools.utils import db


class DealerService:
    async def create(self, payload: DealerCreate) -> tuple[DealerOut, str]:
        return await create_dealer(payload)

    async def get(self, dealer_id: int) -> DealerOut | None:
        return await get_dealer_by_id(dealer_id)

    async def get_by_email(self, email: str) -> DealerOut | None:
        row = await get_dealer_row_by_email(email.strip().lower())
        return row_to_dealer(row) if row else None

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> DealerOut | None:
        async with db.get_connection() as conn:
            await ensure_dealers_schema(conn)
            cursor = await conn.execute(
                "SELECT * FROM dealers WHERE stripe_customer_id = ?",
                (stripe_customer_id,),
            )
            row = await cursor.fetchone()
        return row_to_dealer(row) if row else None

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[DealerOut]:
        return await list_dealers(limit=limit, offset=offset)

    async def update_profile(self, dealer_id: int, payload: DealerUpdate) -> DealerOut | None:
        return await update_dealer(dealer_id, payload)

    async def set_plan(self, dealer_id: int, plan: PlanName) -> DealerOut | None:
        return await update_dealer(dealer_id, DealerUpdate(plan=plan))

    async def set_active(self, dealer_id: int, active: bool) -> DealerOut | None:
        return await update_dealer(dealer_id, DealerUpdate(active=active))

    async def set_stripe_customer_id(
        self,
        dealer_id: int,
        stripe_customer_id: str | None,
    ) -> DealerOut | None:
        return await self._update_fields(
            dealer_id,
            {"stripe_customer_id": stripe_customer_id},
        )

    async def increment_calls_today(self, dealer_id: int, amount: int = 1) -> DealerOut | None:
        if amount < 1:
            raise ValueError("amount must be >= 1")
        async with db.get_connection() as conn:
            await ensure_dealers_schema(conn)
            await conn.execute(
                """
                UPDATE dealers
                SET calls_today = calls_today + ?
                WHERE id = ?
                """,
                (amount, dealer_id),
            )
            await conn.commit()
        return await self.get(dealer_id)

    async def reset_calls_today(self, dealer_id: int | None = None) -> int:
        async with db.get_connection() as conn:
            await ensure_dealers_schema(conn)
            if dealer_id is None:
                cursor = await conn.execute("UPDATE dealers SET calls_today = 0")
            else:
                cursor = await conn.execute(
                    "UPDATE dealers SET calls_today = 0 WHERE id = ?",
                    (dealer_id,),
                )
            await conn.commit()
            return cursor.rowcount

    async def _update_fields(self, dealer_id: int, fields: dict[str, Any]) -> DealerOut | None:
        allowed = {"stripe_customer_id"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unsupported dealer fields: {sorted(unknown)}")
        assignments = [f"{column} = ?" for column in fields]
        params = [*fields.values(), dealer_id]
        async with db.get_connection() as conn:
            await ensure_dealers_schema(conn)
            await conn.execute(
                f"UPDATE dealers SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            await conn.commit()
        return await self.get(dealer_id)


dealer_service = DealerService()
