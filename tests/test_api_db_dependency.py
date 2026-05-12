import asyncio
from collections.abc import AsyncIterator

import aiosqlite
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dependencies import get_current_admin_dealer, get_db
from tools.api.schemas import DealerOut


async def _seed_listings_db(path: str) -> None:
    conn = await aiosqlite.connect(path)
    try:
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
                (1, 'wallapop', 'ad-1', 'Toyota', 'Yaris', 2020, 40000, 9000,
                 12000, 33.3, 22.0, 500, 0.9, 6, 'private', 'Madrid',
                 '[{"price":9000,"scraped_at":"2026-05-09T10:00:00"}]',
                 'clean', 'Sin incidencias', 'https://example.test/1', '2026-05-09T10:00:00'),
                (2, 'milanuncios', 'ad-2', 'Ford', 'Focus', 2019, 70000, 8000,
                 8500, 6.2, -1.0, 450, 0.7, 4, 'dealer', 'Valencia',
                 NULL, 'review', 'Revisar', 'https://example.test/2', '2026-05-09T09:00:00');
            """
        )
        await conn.commit()
    finally:
        await conn.close()


def _client_with_db_override(db_path: str) -> TestClient:
    app = create_app()

    async def override_get_db() -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin_dealer] = lambda: DealerOut(
        id=999,
        name="Admin",
        email="admin@example.com",
        plan="admin",
        active=True,
    )
    return TestClient(app)


def test_get_db_dependency_can_be_overridden_for_listings_and_market(tmp_path, monkeypatch):
    db_path = str(tmp_path / "override.db")
    asyncio.run(_seed_listings_db(db_path))
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = _client_with_db_override(db_path)

    listings = client.get("/listings", params={"brand": "toyota"})
    market = client.get("/market/stats")

    assert listings.status_code == 200
    assert listings.json()["total"] == 1
    assert listings.json()["items"][0]["brand"] == "Toyota"
    assert market.status_code == 200
    assert market.json()["total_listings"] == 2
    assert market.json()["total_opportunities"] == 1


def test_admin_stats_uses_injected_db_connection(tmp_path, monkeypatch):
    db_path = str(tmp_path / "admin_override.db")
    asyncio.run(_seed_listings_db(db_path))
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = _client_with_db_override(db_path)

    response = client.get("/admin/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_listings"] == 2
    assert body["total_opportunities"] == 1
    assert body["admin_dealers"] == 0
