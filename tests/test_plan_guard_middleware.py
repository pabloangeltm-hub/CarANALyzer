import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer
from tools.api.schemas import DealerCreate
from tools.api.services.auth_service import create_jwt
from tools.api.services.dealer_service import dealer_service
from tools.utils import db


@pytest.fixture()
def plan_guard_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "plan_guard.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "plan-guard-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, plan: str = "trial", calls_today: int = 0):
    async def _run():
        dealer, api_key = await create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
                plan=plan,  # type: ignore[arg-type]
            )
        )
        if calls_today:
            dealer = await dealer_service.increment_calls_today(dealer.id, calls_today)
        await db.close_pool()
        assert dealer is not None
        return dealer, api_key

    return asyncio.run(_run())


def test_plan_guard_increments_authenticated_usage(plan_guard_db):
    dealer, _api_key = _create_dealer("quota-ok@example.com", calls_today=49)
    client = TestClient(create_app())
    token = create_jwt(str(dealer.id), token_type="access")

    response = client.get("/dealers/me", headers={"Authorization": f"Bearer {token}"})
    updated = asyncio.run(dealer_service.get(dealer.id))

    assert response.status_code == 200
    assert response.headers["X-Plan-Name"] == "free"
    assert response.headers["X-Plan-Limit"] == "50"
    assert response.headers["X-Plan-Remaining"] == "0"
    assert response.headers["X-Plan-Roi-Max-Pct"] == "10.0"
    assert updated is not None
    assert updated.calls_today == 50


def test_plan_guard_blocks_trial_after_daily_limit(plan_guard_db):
    dealer, _api_key = _create_dealer("quota-block@example.com", calls_today=50)
    client = TestClient(create_app())
    token = create_jwt(str(dealer.id), token_type="access")

    response = client.get("/dealers/me", headers={"Authorization": f"Bearer {token}"})
    updated = asyncio.run(dealer_service.get(dealer.id))

    assert response.status_code == 402
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Plan-Remaining"] == "0"
    assert response.json()["type"] == "https://agartha.local/problems/plan-limit-exceeded"
    assert response.json()["daily_limit"] == 50
    assert updated is not None
    assert updated.calls_today == 50


def test_plan_guard_allows_unlimited_premium_plan(plan_guard_db):
    dealer, _api_key = _create_dealer("quota-elite@example.com", plan="elite", calls_today=5000)
    client = TestClient(create_app())
    token = create_jwt(str(dealer.id), token_type="access")

    response = client.get("/dealers/me", headers={"Authorization": f"Bearer {token}"})
    updated = asyncio.run(dealer_service.get(dealer.id))

    assert response.status_code == 200
    assert response.headers["X-Plan-Name"] == "elite"
    assert response.headers["X-Plan-Limit"] == "unlimited"
    assert response.headers["X-Plan-Remaining"] == "unlimited"
    assert response.headers["X-Plan-Roi-Max-Pct"] == "unlimited"
    assert updated is not None
    assert updated.calls_today == 5001


def test_plan_guard_skips_public_health_endpoint(plan_guard_db):
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Plan-Name" not in response.headers
