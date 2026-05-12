"""Listings router."""

from __future__ import annotations

import re
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from tools.api.dependencies import get_db, get_optional_current_dealer
from tools.api.models.plan import get_plan_limits
from tools.api.schemas import DealerOut, ListingFilter, ListingOut, PaginatedListings

router = APIRouter(prefix="/listings", tags=["listings"])


def _like(value: str | None) -> str | None:
    return f"%{value.casefold()}%" if value else None


def _exact(value: str | None) -> str | None:
    return value.casefold() if value else None


def _column(name: str, alias: str) -> str:
    return f"{alias}.{name}" if alias else name


_PUBLIC_LISTING_COLUMNS = (
    "id",
    "portal",
    "ad_id",
    "brand",
    "model",
    "year",
    "mileage",
    "price",
    "images_count",
    "seller_type",
    "location",
    "url",
    "scraped_at",
)

_PREMIUM_LISTING_COLUMNS = (
    "market_price",
    "roi_bruto",
    "roi_neto",
    "repair_cost",
    "condition_score",
    "price_history_json",
    "forensic_status",
    "forensic_summary",
)


def _roi_limit_for_dealer(dealer: DealerOut | None) -> float | None:
    return get_plan_limits(dealer.plan).roi_max_pct if dealer is not None else None


def _redaction_expr(alias: str) -> str:
    roi_column = _column("roi_neto", alias)
    return f"({roi_column} IS NOT NULL AND {roi_column} > ?)"


def _select_columns(*, alias: str = "", roi_max_pct: float | None = None) -> tuple[str, list[object]]:
    if roi_max_pct is None:
        wildcard = f"{alias}.*" if alias else "*"
        return f"{wildcard}, 0 AS roi_redacted", []

    params: list[object] = []
    redaction_expr = _redaction_expr(alias)
    columns = [f"{_column(column, alias)} AS {column}" for column in _PUBLIC_LISTING_COLUMNS]
    for column in _PREMIUM_LISTING_COLUMNS:
        columns.append(
            f"CASE WHEN {redaction_expr} THEN NULL ELSE {_column(column, alias)} END AS {column}"
        )
        params.append(roi_max_pct)
    columns.append(f"CASE WHEN {redaction_expr} THEN 1 ELSE 0 END AS roi_redacted")
    params.append(roi_max_pct)
    return ",\n                    ".join(columns), params


def _filter_conditions(filters: ListingFilter, *, alias: str = "") -> tuple[list[str], list[object]]:
    conditions: list[str] = []
    params: list[object] = []

    for field_name, value, matcher in (
        ("brand", filters.brand, _like),
        ("model", filters.model, _like),
        ("portal", filters.portal, _exact),
        ("seller_type", filters.seller_type, _exact),
        ("forensic_status", filters.forensic_status, _exact),
    ):
        if value:
            operator = "LIKE" if matcher is _like else "="
            conditions.append(f"LOWER(COALESCE({_column(field_name, alias)}, '')) {operator} ?")
            params.append(matcher(value))

    for field_name, operator, value in (
        ("year", ">=", filters.year_min),
        ("year", "<=", filters.year_max),
        ("price", ">=", filters.price_min),
        ("price", "<=", filters.price_max),
        ("roi_neto", ">=", filters.roi_min),
    ):
        if value is not None:
            conditions.append(f"{_column(field_name, alias)} {operator} ?")
            params.append(value)

    return conditions, params


def _where_sql(conditions: list[str]) -> str:
    return "WHERE " + " AND ".join(conditions) if conditions else ""


def _fts_query(value: str | None) -> str | None:
    if not value:
        return None
    tokens = re.findall(r"\w+", value.casefold(), flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join(f"{token}*" for token in tokens)


async def _has_fts_index(conn: aiosqlite.Connection) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'listings_fts'"
    )
    return await cursor.fetchone() is not None


def _add_q_like_condition(
    conditions: list[str],
    params: list[object],
    q: str | None,
    *,
    alias: str = "",
) -> None:
    q_like = _like(q)
    if q_like is None:
        return
    conditions.append(
        "("
        f"LOWER(COALESCE({_column('brand', alias)}, '')) LIKE ? "
        f"OR LOWER(COALESCE({_column('model', alias)}, '')) LIKE ? "
        f"OR LOWER(COALESCE({_column('location', alias)}, '')) LIKE ? "
        f"OR LOWER(COALESCE({_column('forensic_summary', alias)}, '')) LIKE ? "
        f"OR LOWER(COALESCE({_column('url', alias)}, '')) LIKE ?"
        ")"
    )
    params.extend([q_like, q_like, q_like, q_like, q_like])


@router.get(
    "",
    response_model=PaginatedListings,
    summary="Listar vehículos",
    description=(
        "Retorna una página de vehículos que coinciden con los filtros aplicados. "
        "El filtro `q` usa SQLite FTS5 cuando existe `listings_fts`, con fallback LIKE. "
        "Los filtros `brand` y `model` usan búsqueda LIKE case-insensitive. "
        "Los filtros de igualdad (`portal`, `seller_type`, `forensic_status`) son exactos. "
        "Usa `min_roi` o `roi_min` (equivalentes) para filtrar por rentabilidad mínima. "
        "La ordenación es siempre por `scraped_at DESC, id DESC`."
    ),
)
async def list_listings(
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
    dealer: Annotated[DealerOut | None, Depends(get_optional_current_dealer)],
    q: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    portal: str | None = None,
    seller_type: str | None = None,
    forensic_status: str | None = None,
    year_min: int | None = Query(default=None, ge=1900, le=2099),
    year_max: int | None = Query(default=None, ge=1900, le=2099),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    roi_min: float | None = None,
    min_roi: float | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=100),
) -> PaginatedListings:
    filters = ListingFilter(
        q=q,
        brand=brand,
        model=model,
        portal=portal,
        seller_type=seller_type,
        forensic_status=forensic_status,
        year_min=year_min,
        year_max=year_max,
        price_min=price_min,
        price_max=price_max,
        roi_min=min_roi if min_roi is not None else roi_min,
    )
    offset = (page - 1) * size
    roi_max_pct = _roi_limit_for_dealer(dealer)

    try:
        fts_query = _fts_query(filters.q)
        use_fts = fts_query is not None and await _has_fts_index(conn)
        if use_fts:
            conditions, params = _filter_conditions(filters, alias="l")
            select_sql, select_params = _select_columns(alias="l", roi_max_pct=roi_max_pct)
            where_sql = _where_sql(conditions)
            count_cursor = await conn.execute(
                f"""
                WITH fts AS (
                    SELECT rowid
                    FROM listings_fts
                    WHERE listings_fts MATCH ?
                )
                SELECT COUNT(*) AS total
                FROM listings AS l
                JOIN fts ON fts.rowid = l.id
                {where_sql}
                """,
                [fts_query, *params],
            )
            total_row = await count_cursor.fetchone()
            cursor = await conn.execute(
                f"""
                WITH fts AS (
                    SELECT rowid, bm25(listings_fts) AS rank
                    FROM listings_fts
                    WHERE listings_fts MATCH ?
                )
                SELECT {select_sql}
                FROM listings AS l
                JOIN fts ON fts.rowid = l.id
                {where_sql}
                ORDER BY fts.rank ASC, l.scraped_at DESC, l.id DESC
                LIMIT ? OFFSET ?
                """,
                [fts_query, *select_params, *params, size, offset],
            )
        else:
            conditions, params = _filter_conditions(filters)
            _add_q_like_condition(conditions, params, filters.q)
            select_sql, select_params = _select_columns(roi_max_pct=roi_max_pct)
            where_sql = _where_sql(conditions)
            count_cursor = await conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM listings
                {where_sql}
                """,
                params,
            )
            total_row = await count_cursor.fetchone()
            cursor = await conn.execute(
                f"""
                SELECT {select_sql}
                FROM listings
                {where_sql}
                ORDER BY scraped_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*select_params, *params, size, offset],
            )
        rows = await cursor.fetchall()
    except aiosqlite.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return PaginatedListings(items=[], total=0, page=page, size=size)
        raise

    return PaginatedListings(
        items=[ListingOut.model_validate(dict(row)) for row in rows],
        total=int(total_row["total"] if total_row else 0),
        page=page,
        size=size,
    )


@router.get(
    "/{listing_id}",
    response_model=ListingOut,
    summary="Detalle de vehículo",
    description="Retorna todos los campos de un vehículo por su `id` interno de base de datos.",
)
async def get_listing(
    listing_id: int,
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
    dealer: Annotated[DealerOut | None, Depends(get_optional_current_dealer)],
) -> ListingOut:
    try:
        select_sql, select_params = _select_columns(roi_max_pct=_roi_limit_for_dealer(dealer))
        cursor = await conn.execute(
            f"SELECT {select_sql} FROM listings WHERE id = ?",
            [*select_params, listing_id],
        )
        row = await cursor.fetchone()
    except aiosqlite.OperationalError as exc:
        if "no such table" in str(exc).lower():
            row = None
        else:
            raise

    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return ListingOut.model_validate(dict(row))
