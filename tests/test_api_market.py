import asyncio
from collections.abc import AsyncIterator

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dependencies import get_db


async def _seed_market_db(path: str, *, with_table: bool = True) -> None:
    conn = await aiosqlite.connect(path)
    try:
        if not with_table:
            return
        await conn.executescript(
            """
            CREATE TABLE listings (
                id                 INTEGER PRIMARY KEY,
                portal             TEXT,
                ad_id              TEXT,
                brand              TEXT,
                model              TEXT,
                year               INTEGER,
                mileage            INTEGER,
                price              REAL,
                market_price       REAL,
                roi_bruto          REAL,
                roi_neto           REAL,
                repair_cost        REAL,
                condition_score    REAL,
                images_count       INTEGER,
                seller_type        TEXT,
                location           TEXT,
                price_history_json TEXT,
                forensic_status    TEXT,
                forensic_summary   TEXT,
                url                TEXT,
                scraped_at         TEXT
            );
            INSERT INTO listings
                (id, portal, ad_id, brand, model, year, mileage, price,
                 market_price, roi_bruto, roi_neto, repair_cost,
                 condition_score, images_count, seller_type, location,
                 price_history_json, forensic_status, forensic_summary, url, scraped_at)
            VALUES
                (1, 'wallapop', 'toy-1', 'Toyota', 'Yaris', 2020, 40000, 9000,
                 12000, 33.3, 22.0, 500, 0.9, 6, 'private', 'Madrid',
                 '[{"price":9500,"scraped_at":"2026-05-01T10:00:00"},{"price":9000,"scraped_at":"2026-05-09T10:00:00"}]',
                 'clean', 'Sin incidencias', 'https://example.test/1', '2026-05-09T10:00:00'),
                (2, 'milanuncios', 'toy-2', 'Toyota', 'Yaris', 2020, 45000, 10000,
                 12500, 25.0, 10.0, 700, 0.8, 7, 'dealer', 'Madrid',
                 '[{"price":10200,"scraped_at":"2026-05-01T12:00:00"},{"price":10000,"scraped_at":"2026-05-09T12:00:00"}]',
                 'clean', 'OK', 'https://example.test/2', '2026-05-09T12:00:00'),
                (3, 'wallapop', 'ford-1', 'Ford', 'Focus', 2018, 90000, 8000,
                 8200, 2.5, -5.0, 600, 0.6, 4, 'private', 'Valencia',
                 NULL, 'review', 'Revisar', 'https://example.test/3', '2026-05-08T09:00:00');
            """
        )
        await conn.commit()
    finally:
        await conn.close()


@pytest.fixture(params=[True])
def market_client(tmp_path, monkeypatch, request) -> TestClient:
    db_path = tmp_path / "market.db"
    asyncio.run(_seed_market_db(str(db_path), with_table=request.param))
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    app = create_app()

    async def override_get_db() -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_market_stats_includes_global_kpis_and_top_brands(market_client: TestClient):
    response = market_client.get("/market/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_listings"] == 3
    assert body["total_opportunities"] == 2
    assert body["avg_roi_neto"] == 9.0
    assert body["avg_price"] == 9000.0
    assert body["by_brand"][0]["brand"] == "Toyota"
    assert body["by_brand"][0]["opportunities_count"] == 2


def test_market_by_brand_respects_limit(market_client: TestClient):
    response = market_client.get("/market/by-brand", params={"limit": 1})

    assert response.status_code == 200
    assert response.json() == [
        {
            "brand": "Toyota",
            "listings_count": 2,
            "avg_price": 9500.0,
            "avg_market_price": 12250.0,
            "avg_roi_neto": 16.0,
            "opportunities_count": 2,
        }
    ]


def test_roi_histogram_groups_by_bucket(market_client: TestClient):
    response = market_client.get("/market/roi-histogram", params={"bucket_size": 10})

    assert response.status_code == 200
    assert response.json() == {
        "buckets": [
            {"min_roi": -10.0, "max_roi": 0.0, "count": 1},
            {"min_roi": 10.0, "max_roi": 20.0, "count": 1},
            {"min_roi": 20.0, "max_roi": 30.0, "count": 1},
        ],
        "total_count": 3,
    }


def test_price_trends_filters_and_averages_history(market_client: TestClient):
    response = market_client.get(
        "/market/trends",
        params={"brand": "Toyota", "model": "Yaris", "year": 2020},
    )

    assert response.status_code == 200
    assert response.json() == {
        "brand": "Toyota",
        "model": "Yaris",
        "year": 2020,
        "points": [
            {"date": "2026-05-01", "avg_price": 9850.0, "listings_count": 2},
            {"date": "2026-05-09", "avg_price": 9500.0, "listings_count": 2},
        ],
    }


def test_market_endpoints_return_empty_shapes_when_table_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "missing.db"
    asyncio.run(_seed_market_db(str(db_path), with_table=False))
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    app = create_app()

    async def override_get_db() -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    stats = client.get("/market/stats")
    by_brand = client.get("/market/by-brand")
    histogram = client.get("/market/roi-histogram")
    trends = client.get("/market/trends")

    assert stats.status_code == 200
    assert stats.json()["total_listings"] == 0
    assert stats.json()["by_brand"] == []
    assert by_brand.json() == []
    assert histogram.json() == {"buckets": [], "total_count": 0}
    assert trends.json() == {"brand": None, "model": None, "year": None, "points": []}
