import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, get_dealer_by_id
from tools.api.routers.webhooks import get_webhook_billing_service
from tools.api.schemas import DealerCreate
from tools.api.services.dealer_service import DealerService
from tools.utils import db


@pytest.fixture()
def subscription_deleted_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "subscription_deleted_webhook.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_elite_dealer_with_customer(email: str, customer_id: str):
    dealer, _api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
            )
        )
    )
    service = DealerService()
    dealer = asyncio.run(service.set_plan(dealer.id, "elite"))
    assert dealer is not None
    dealer = asyncio.run(service.set_stripe_customer_id(dealer.id, customer_id))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer


def _reload_dealer(dealer_id: int):
    dealer = asyncio.run(get_dealer_by_id(dealer_id))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer


class FakeSubscriptionBillingService:
    def __init__(self, event):
        self.event = event

    def construct_webhook_event(self, payload, signature):
        return self.event


def _client_with_event(event) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_webhook_billing_service] = lambda: FakeSubscriptionBillingService(event)
    return TestClient(app)


def _subscription_deleted_event(customer="cus_deleted_123"):
    return {
        "id": "evt_sub_deleted_123",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_deleted_123",
                "customer": customer,
            }
        },
    }


def test_subscription_deleted_downgrades_dealer_to_free(subscription_deleted_db):
    dealer = _create_elite_dealer_with_customer("deleted@example.com", "cus_deleted_123")
    client = _client_with_event(_subscription_deleted_event())

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "id": "evt_sub_deleted_123",
        "type": "customer.subscription.deleted",
    }
    updated = _reload_dealer(dealer.id)
    assert updated.plan == "free"
    assert updated.stripe_customer_id == "cus_deleted_123"


def test_subscription_deleted_requires_customer(subscription_deleted_db):
    client = _client_with_event(_subscription_deleted_event(customer=None))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "subscription missing customer"


def test_subscription_deleted_unknown_customer_returns_404(subscription_deleted_db):
    client = _client_with_event(_subscription_deleted_event(customer="cus_unknown"))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dealer not found"
