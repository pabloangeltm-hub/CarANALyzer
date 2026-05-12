import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.routers import auth
from tools.api.routers.auth import get_register_billing_service
from tools.utils import db


@pytest.fixture()
def register_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "auth_register.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-register-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


class FakeRegisterBillingService:
    def __init__(self):
        self.calls = []

    async def ensure_customer(self, dealer):
        self.calls.append(dealer)
        return f"cus_register_{dealer.id}"


def _client_with_billing(fake_billing: FakeRegisterBillingService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_register_billing_service] = lambda: fake_billing
    return TestClient(app)


def test_register_creates_dealer_customer_tokens_api_key_and_welcome_email(register_db, monkeypatch):
    fake_billing = FakeRegisterBillingService()
    sent = []

    async def fake_send_welcome_email(*, to, dealer_name, settings=None):
        sent.append({"to": to, "dealer_name": dealer_name, "settings": settings})
        return {"id": "email_register_123"}

    monkeypatch.setattr(auth, "send_welcome_email", fake_send_welcome_email)
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/auth/register",
        json={
            "name": "Nuevo Dealer",
            "email": "Nuevo@Example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"] != body["refresh_token"]
    assert body["api_key"].startswith("agrt_")
    assert body["dealer"]["email"] == "nuevo@example.com"
    assert body["dealer"]["name"] == "Nuevo Dealer"
    assert body["dealer"]["plan"] == "free"
    assert body["dealer"]["stripe_customer_id"] == f"cus_register_{body['dealer']['id']}"
    assert len(fake_billing.calls) == 1
    assert sent == [
        {"to": "nuevo@example.com", "dealer_name": "Nuevo Dealer", "settings": None}
    ]

    me = client.get("/dealers/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    api_key_me = client.get("/dealers/me", headers={"X-API-Key": body["api_key"]})
    assert me.status_code == 200
    assert me.json()["id"] == body["dealer"]["id"]
    assert api_key_me.status_code == 200
    assert api_key_me.json()["id"] == body["dealer"]["id"]


def test_register_rejects_duplicate_email(register_db, monkeypatch):
    fake_billing = FakeRegisterBillingService()

    async def fake_send_welcome_email(**kwargs):
        return {"id": "email"}

    monkeypatch.setattr(auth, "send_welcome_email", fake_send_welcome_email)
    client = _client_with_billing(fake_billing)
    payload = {
        "name": "Dup Dealer",
        "email": "dup@example.com",
        "password": "password123",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Dealer email already exists"


def test_register_requires_stripe_configuration(register_db, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    client = TestClient(create_app())

    response = client.post(
        "/auth/register",
        json={
            "name": "No Stripe",
            "email": "nostripe@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "STRIPE_SECRET_KEY is required"
