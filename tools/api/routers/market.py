"""Market analysis router."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Depends, Query

from tools.api.dependencies import get_db
from tools.api.schemas import (
    BrandMetrics,
    MarketStatsOut,
    PriceTrend,
    PriceTrendPoint,
    ROIHistogram,
    ROIHistogramBucket,
)

router = APIRouter(prefix="/market", tags=["market"])


async def _fetch_all(
    conn: aiosqlite.Connection,
    query: str,
    params: list[Any] | tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    try:
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
    except aiosqlite.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return []
        raise
    return [dict(row) for row in rows]


def _avg(value: Any) -> float | None:
    return round(float(value), 2) if value is not None else None


async def _market_by_brand(conn: aiosqlite.Connection, limit: int) -> list[BrandMetrics]:
    rows = await _fetch_all(
        conn,
        """
        SELECT
            COALESCE(NULLIF(TRIM(brand), ''), 'unknown') AS brand,
            COUNT(*) AS listings_count,
            AVG(price) AS avg_price,
            AVG(market_price) AS avg_market_price,
            AVG(roi_neto) AS avg_roi_neto,
            SUM(CASE WHEN roi_neto > 0 THEN 1 ELSE 0 END) AS opportunities_count
        FROM listings
        GROUP BY COALESCE(NULLIF(TRIM(brand), ''), 'unknown')
        ORDER BY opportunities_count DESC, listings_count DESC, brand ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        BrandMetrics(
            brand=str(row["brand"]),
            listings_count=int(row["listings_count"] or 0),
            avg_price=_avg(row["avg_price"]),
            avg_market_price=_avg(row["avg_market_price"]),
            avg_roi_neto=_avg(row["avg_roi_neto"]),
            opportunities_count=int(row["opportunities_count"] or 0),
        )
        for row in rows
    ]


@router.get(
    "/stats",
    response_model=MarketStatsOut,
    summary="KPIs globales del mercado",
    description=(
        "Agrega el total de vehiculos, oportunidades (ROI > 0), ROI medio neto, "
        "precio medio de lista y precio medio de mercado. "
        "Incluye el top-20 de marcas por oportunidades en `by_brand`."
    ),
)
async def market_stats(
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> MarketStatsOut:
    rows = await _fetch_all(
        conn,
        """
        SELECT
            COUNT(*) AS total_listings,
            SUM(CASE WHEN roi_neto > 0 THEN 1 ELSE 0 END) AS total_opportunities,
            AVG(roi_neto) AS avg_roi_neto,
            AVG(price) AS avg_price,
            AVG(market_price) AS avg_market_price
        FROM listings
        """,
    )
    stats = rows[0] if rows else {}
    return MarketStatsOut(
        total_listings=int(stats.get("total_listings") or 0),
        total_opportunities=int(stats.get("total_opportunities") or 0),
        avg_roi_neto=_avg(stats.get("avg_roi_neto")),
        avg_price=_avg(stats.get("avg_price")),
        avg_market_price=_avg(stats.get("avg_market_price")),
        by_brand=await _market_by_brand(conn, limit=20),
    )


@router.get(
    "/by-brand",
    response_model=list[BrandMetrics],
    summary="Metricas por marca",
    description=(
        "Retorna metricas agregadas por marca: numero de anuncios, precios medios, "
        "ROI neto medio y numero de oportunidades. "
        "Ordenado por oportunidades DESC. Maximo `limit` marcas (1-100, default 20)."
    ),
)
async def market_by_brand(
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BrandMetrics]:
    return await _market_by_brand(conn, limit=limit)


@router.get(
    "/roi-histogram",
    response_model=ROIHistogram,
    summary="Histograma de distribucion de ROI",
    description=(
        "Agrupa todos los vehiculos en buckets de `bucket_size` puntos porcentuales de ROI neto. "
        "Util para visualizar la distribucion de rentabilidades del catalogo. "
        "`bucket_size` configurable entre 0.1 y 100 (default 10)."
    ),
)
async def roi_histogram(
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
    bucket_size: float = Query(default=10.0, gt=0, le=100),
) -> ROIHistogram:
    rows = await _fetch_all(conn, "SELECT roi_neto FROM listings WHERE roi_neto IS NOT NULL")
    buckets: dict[float, int] = defaultdict(int)
    for row in rows:
        roi = float(row["roi_neto"])
        bucket_min = (roi // bucket_size) * bucket_size
        buckets[bucket_min] += 1

    histogram_buckets = [
        ROIHistogramBucket(
            min_roi=round(bucket_min, 2),
            max_roi=round(bucket_min + bucket_size, 2),
            count=count,
        )
        for bucket_min, count in sorted(buckets.items())
    ]
    return ROIHistogram(buckets=histogram_buckets, total_count=sum(buckets.values()))


def _history_points(row: dict[str, Any]) -> list[tuple[str, float]]:
    raw_history = row.get("price_history_json")
    history: list[dict[str, Any]] = []
    if raw_history:
        try:
            loaded = json.loads(raw_history)
            if isinstance(loaded, list):
                history = [item for item in loaded if isinstance(item, dict)]
        except json.JSONDecodeError:
            history = []

    if not history and row.get("price") is not None and row.get("scraped_at"):
        history = [{"price": row["price"], "scraped_at": row["scraped_at"]}]

    points: list[tuple[str, float]] = []
    for item in history:
        try:
            price = float(item["price"])
        except (KeyError, TypeError, ValueError):
            continue
        scraped_at = str(item.get("scraped_at") or "").strip()
        if scraped_at:
            points.append((scraped_at[:10], price))
    return points


@router.get(
    "/trends",
    response_model=PriceTrend,
    summary="Tendencia historica de precios",
    description=(
        "Retorna la evolucion temporal del precio medio para una combinacion brand/model/year. "
        "Los datos provienen de `price_history_json` acumulado por el pipeline de scraping. "
        "Sin filtros retorna la tendencia global de todo el catalogo."
    ),
)
async def price_trends(
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
    brand: str | None = None,
    model: str | None = None,
    year: int | None = Query(default=None, ge=1900, le=2099),
) -> PriceTrend:
    conditions: list[str] = []
    params: list[Any] = []
    if brand:
        conditions.append("LOWER(COALESCE(brand, '')) = ?")
        params.append(brand.casefold())
    if model:
        conditions.append("LOWER(COALESCE(model, '')) = ?")
        params.append(model.casefold())
    if year is not None:
        conditions.append("year = ?")
        params.append(year)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    rows = await _fetch_all(
        conn,
        f"""
        SELECT brand, model, year, price, price_history_json, scraped_at
        FROM listings{where}
        """,
        params,
    )

    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for date_key, price in _history_points(row):
            grouped[date_key].append(price)

    points = [
        PriceTrendPoint(
            date=date_key,
            avg_price=round(sum(prices) / len(prices), 2),
            listings_count=len(prices),
        )
        for date_key, prices in sorted(grouped.items())
    ]
    return PriceTrend(brand=brand, model=model, year=year, points=points)
