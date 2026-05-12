"""Administrative API router."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from tools.api.dependencies import get_current_admin_dealer, get_db
from tools.api.dealer_store import (
    ensure_dealers_schema,
    update_dealer,
)
from tools.api.schemas import DealerOut, DealerUpdate
from tools.api.schemas.admin import (
    AdminActiveUpdate,
    AdminHealthOut,
    AdminPlanUpdate,
    AdminStatsOut,
    AdminStripeCustomerOut,
    AdminUsageResetOut,
)
from tools.api.services.dealer_service import DealerService, dealer_service
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import (
    StripeBillingService,
    StripeServiceError,
    get_stripe_billing_service,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_dealer_service() -> DealerService:
    return dealer_service


def get_admin_billing_service() -> StripeBillingService:
    try:
        return get_stripe_billing_service()
    except StripeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _table_exists(conn: aiosqlite.Connection, table_name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return await cursor.fetchone() is not None


async def _listing_stats(conn: aiosqlite.Connection) -> dict[str, Any]:
    if not await _table_exists(conn, "listings"):
        return {
            "total_listings": 0,
            "total_opportunities": 0,
            "avg_roi_neto": None,
        }
    cursor = await conn.execute(
        """
        SELECT
            COUNT(*) AS total_listings,
            SUM(CASE WHEN roi_neto > 0 THEN 1 ELSE 0 END) AS total_opportunities,
            AVG(roi_neto) AS avg_roi_neto
        FROM listings
        """
    )
    row = await cursor.fetchone()
    return dict(row) if row else {}


@router.get(
    "/stats",
    response_model=AdminStatsOut,
    summary="KPIs administrativos",
    description=(
        "Retorna contadores globales de dealers, uso diario y catalogo. "
        "Requiere dealer activo con plan `admin` mediante Bearer token o `X-API-Key`."
    ),
)
async def admin_stats(
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> AdminStatsOut:
    await ensure_dealers_schema(conn)
    cursor = await conn.execute(
        """
        SELECT
            COUNT(*) AS total_dealers,
            SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_dealers,
            SUM(CASE WHEN plan IN ('free', 'trial') THEN 1 ELSE 0 END) AS free_dealers,
            SUM(CASE WHEN plan = 'starter' THEN 1 ELSE 0 END) AS starter_dealers,
            SUM(CASE WHEN plan IN ('pro', 'basic') THEN 1 ELSE 0 END) AS pro_dealers,
            SUM(CASE WHEN plan IN ('elite', 'premium') THEN 1 ELSE 0 END) AS elite_dealers,
            SUM(CASE WHEN plan = 'admin' THEN 1 ELSE 0 END) AS admin_dealers,
            SUM(COALESCE(calls_today, 0)) AS calls_today
        FROM dealers
        """
    )
    dealer_stats = dict(await cursor.fetchone() or {})
    listing_stats = await _listing_stats(conn)

    avg_roi = listing_stats.get("avg_roi_neto")
    return AdminStatsOut(
        total_dealers=int(dealer_stats.get("total_dealers") or 0),
        active_dealers=int(dealer_stats.get("active_dealers") or 0),
        free_dealers=int(dealer_stats.get("free_dealers") or 0),
        starter_dealers=int(dealer_stats.get("starter_dealers") or 0),
        pro_dealers=int(dealer_stats.get("pro_dealers") or 0),
        elite_dealers=int(dealer_stats.get("elite_dealers") or 0),
        admin_dealers=int(dealer_stats.get("admin_dealers") or 0),
        calls_today=int(dealer_stats.get("calls_today") or 0),
        total_listings=int(listing_stats.get("total_listings") or 0),
        total_opportunities=int(listing_stats.get("total_opportunities") or 0),
        avg_roi_neto=round(float(avg_roi), 2) if avg_roi is not None else None,
        generated_at=datetime.now(),
    )


@router.patch(
    "/dealers/{dealer_id}/plan",
    response_model=DealerOut,
    summary="Actualizar plan de dealer",
    description=(
        "Cambia el plan de un dealer a `free`, `starter`, `pro`, `elite` o `admin`. "
        "Requiere credenciales admin."
    ),
)
async def update_dealer_plan(
    dealer_id: int,
    payload: AdminPlanUpdate,
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
) -> DealerOut:
    updated = await update_dealer(dealer_id, DealerUpdate(plan=payload.plan))
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return updated


@router.patch(
    "/dealers/{dealer_id}/active",
    response_model=DealerOut,
    summary="Activar o suspender dealer",
    description="Actualiza el estado activo de una cuenta de dealer. Requiere credenciales admin.",
)
async def update_dealer_active(
    dealer_id: int,
    payload: AdminActiveUpdate,
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
    dealers: Annotated[DealerService, Depends(get_admin_dealer_service)],
) -> DealerOut:
    updated = await dealers.set_active(dealer_id, payload.active)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return updated


@router.post(
    "/dealers/{dealer_id}/usage/reset",
    response_model=AdminUsageResetOut,
    summary="Resetear uso diario de dealer",
    description="Pone `calls_today` a 0 para un dealer. Requiere credenciales admin.",
)
async def reset_dealer_usage(
    dealer_id: int,
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
    dealers: Annotated[DealerService, Depends(get_admin_dealer_service)],
) -> AdminUsageResetOut:
    reset_count = await dealers.reset_calls_today(dealer_id)
    dealer = await dealers.get(dealer_id)
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return AdminUsageResetOut(dealer=dealer, reset_count=reset_count)


@router.post(
    "/dealers/{dealer_id}/stripe/customer",
    response_model=AdminStripeCustomerOut,
    summary="Asegurar customer Stripe de dealer",
    description=(
        "Crea o reutiliza el Stripe Customer del dealer y persiste `stripe_customer_id`. "
        "Requiere credenciales admin."
    ),
)
async def ensure_dealer_stripe_customer(
    dealer_id: int,
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
    dealers: Annotated[DealerService, Depends(get_admin_dealer_service)],
    billing: Annotated[StripeBillingService, Depends(get_admin_billing_service)],
) -> AdminStripeCustomerOut:
    dealer = await dealers.get(dealer_id)
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    try:
        customer_id = await billing.ensure_customer(dealer)
    except StripeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StripeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated = await dealers.get(dealer_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return AdminStripeCustomerOut(dealer=updated, stripe_customer_id=customer_id)


@router.get(
    "/health",
    response_model=AdminHealthOut,
    summary="Health administrativo",
    description="Verifica conectividad SQLite y presencia de tablas principales. Requiere credenciales admin.",
)
async def admin_health(
    _admin: Annotated[DealerOut, Depends(get_current_admin_dealer)],
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> AdminHealthOut:
    checked_at = datetime.now()
    try:
        await conn.execute("SELECT 1")
        await ensure_dealers_schema(conn)
        dealers_table = await _table_exists(conn, "dealers")
        listings_table = await _table_exists(conn, "listings")
    except aiosqlite.Error:
        return AdminHealthOut(
            status="down",
            database="error",
            dealers_table=False,
            listings_table=False,
            checked_at=checked_at,
        )

    return AdminHealthOut(
        status="ok" if dealers_table else "degraded",
        database="ok",
        dealers_table=dealers_table,
        listings_table=listings_table,
        checked_at=checked_at,
    )
