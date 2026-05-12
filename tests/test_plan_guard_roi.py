import asyncio

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer
from tools.api.schemas import DealerCreate
from tools.api.services.auth_service import create_jwt
from tools.utils import db


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
                (1, 'wallapop', 'high-roi', 'Toyota', 'Yaris', 2020, 40000, 9000,
                 12000, 33.3, 22.0, 500, 0.9, 6, 'private', 'Madrid',
                 '[{"price":9100,"scraped_at":"2026-05-01T10:00:00"}]',
                 'clean', 'Sin incidencias premium', 'https://example.test/1', '2026-05-09T10:00:00'),
                (2, 'milanuncios', 'visible-roi', 'BMW', 'Serie 3', 2018, 90000, 18000,
                 22000, 22.2, 12.0, 1500, 0.7, 8, 'dealer', 'Barcelona',
                 NULL, 'review', 'Visible para Starter', 'https://example.test/2', '2026-05-09T09:00:00');
            """
        )
        await conn.commit()
    finally:
        await conn.close()


@pytest.fixture()
def roi_paywall_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "roi_paywall.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "roi-paywall-secret-with-at-least-32-bytes")
    asyncio.run(_seed_listings(db.DB_PATH))
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(plan: str):
    dealer, _api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name="ROI Dealer",
                email=f"{plan}@example.com",
                password="password123",
                plan=plan,
            )
        )
    )
    asyncio.run(db.close_pool())
    return dealer


def _headers(dealer_id: int) -> dict[str, str]:
    token = create_jwt(str(dealer_id), expires_in=3600, token_type="access")
    return {"Authorization": f"Bearer {token}"}


def test_starter_plan_redacts_rows_above_roi_cap(roi_paywall_db):
    dealer = _create_dealer("starter")
    client = TestClient(create_app())

    response = client.get("/listings", headers=_headers(dealer.id))

    assert response.status_code == 200
    items = {item["ad_id"]: item for item in response.json()["items"]}
    redacted = items["high-roi"]
    visible = items["visible-roi"]
    assert redacted["roi_redacted"] is True
    assert redacted["roi_neto"] is None
    assert redacted["roi_bruto"] is None
    assert redacted["market_price"] is None
    assert redacted["repair_cost"] is None
    assert redacted["condition_score"] is None
    assert redacted["forensic_status"] is None
    assert redacted["forensic_summary"] is None
    assert redacted["price_history"] == []
    assert visible["roi_redacted"] is False
    assert visible["roi_neto"] == 12.0
    assert response.headers["X-Plan-Roi-Max-Pct"] == "15.0"


def test_elite_plan_receives_full_roi_payload(roi_paywall_db):
    dealer = _create_dealer("elite")
    client = TestClient(create_app())

    response = client.get("/listings/1", headers=_headers(dealer.id))

    assert response.status_code == 200
    body = response.json()
    assert body["roi_redacted"] is False
    assert body["roi_neto"] == 22.0
    assert body["market_price"] == 12000.0
    assert body["forensic_summary"] == "Sin incidencias premium"
    assert body["price_history"] == [
        {"price": 9100.0, "scraped_at": "2026-05-01T10:00:00"}
    ]
    assert response.headers["X-Plan-Roi-Max-Pct"] == "unlimited"
