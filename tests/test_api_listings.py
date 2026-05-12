import asyncio
from collections.abc import AsyncIterator

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dependencies import get_db


async def _seed_listings(path: str) -> None:
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
                (1, 'wallapop', 'toy-1', 'Toyota', 'Yaris', 2020, 40000, 9000,
                 12000, 33.3, 22.0, 500, 0.9, 6, 'private', 'Madrid',
                 '[{"price":9100,"scraped_at":"2026-05-01T10:00:00"},{"price":9000,"scraped_at":"2026-05-09T10:00:00"}]',
                 'clean', 'Sin incidencias', 'https://example.test/1', '2026-05-09T10:00:00'),
                (2, 'milanuncios', 'bmw-1', 'BMW', 'Serie 3', 2018, 90000, 18000,
                 22000, 22.2, 12.0, 1500, 0.7, 8, 'dealer', 'Barcelona',
                 NULL, 'review', 'Necesita revisar paragolpes', 'https://example.test/2', '2026-05-09T09:00:00'),
                (3, 'wallapop', 'toy-2', 'Toyota', 'Corolla', 2017, 120000, 7000,
                 7600, 8.6, -2.0, 800, 0.5, 3, 'private', 'Valencia',
                 NULL, 'damaged', 'Golpe lateral', 'https://example.test/3', '2026-05-08T08:00:00');
            """
        )
        await conn.commit()
    finally:
        await conn.close()


@pytest.fixture()
def listings_client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "listings.db"
    asyncio.run(_seed_listings(str(db_path)))
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


def test_listings_filters_and_paginates(listings_client: TestClient):
    response = listings_client.get(
        "/listings",
        params={"brand": "toy", "seller_type": "private", "size": 1, "page": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["ad_id"] == "toy-1"


def test_listings_q_filter_uses_like_fallback_without_fts(listings_client: TestClient):
    response = listings_client.get("/listings", params={"q": "paragolpes"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["brand"] == "BMW"


def test_listing_detail_parses_price_history(listings_client: TestClient):
    response = listings_client.get("/listings/1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["price_history"] == [
        {"price": 9100.0, "scraped_at": "2026-05-01T10:00:00"},
        {"price": 9000.0, "scraped_at": "2026-05-09T10:00:00"},
    ]


def test_listings_returns_empty_page_when_table_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
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

    response = client.get("/listings")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 25}


def test_listing_detail_missing_returns_problem_details(listings_client: TestClient):
    response = listings_client.get("/listings/999")

    assert response.status_code == 404
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["detail"] == "Listing not found"
    assert body["instance"] == "/listings/999"
