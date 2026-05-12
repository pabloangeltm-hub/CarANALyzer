import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, get_dealer_by_id
from tools.api.routers.webhooks import get_webhook_billing_service
from tools.api.schemas import DealerCreate
from tools.utils import db


@pytest.fixture()
def checkout_webhook_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "checkout_webhook.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str):
    dealer, _api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
            )
        )
    )
    asyncio.run(db.close_pool())
    return dealer


def _reload_dealer(dealer_id: int):
    dealer = asyncio.run(get_dealer_by_id(dealer_id))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer


class FakeCheckoutBillingService:
    def __init__(self, event):
        self.event = event

    def construct_webhook_event(self, payload, signature):
        return self.event


def _client_with_event(event) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_webhook_billing_service] = lambda: FakeCheckoutBillingService(event)
    return TestClient(app)


def _checkout_event(*, dealer_id, target_plan="elite", customer="cus_checkout_123"):
    return {
        "id": "evt_checkout_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": customer,
                "client_reference_id": str(dealer_id),
                "metadata": {
                    "dealer_id": str(dealer_id),
                    "target_plan": target_plan,
                },
            }
        },
    }


def test_checkout_completed_webhook_updates_dealer_plan_and_customer(checkout_webhook_db):
    dealer = _create_dealer("completed@example.com")
    client = _client_with_event(_checkout_event(dealer_id=dealer.id))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "id": "evt_checkout_123",
        "type": "checkout.session.completed",
    }
    updated = _reload_dealer(dealer.id)
    assert updated.plan == "elite"
    assert updated.stripe_customer_id == "cus_checkout_123"


def test_checkout_completed_uses_client_reference_id_fallback(checkout_webhook_db):
    dealer = _create_dealer("fallback@example.com")
    event = _checkout_event(dealer_id=dealer.id, target_plan="pro", customer=None)
    del event["data"]["object"]["metadata"]["dealer_id"]
    client = _client_with_event(event)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    updated = _reload_dealer(dealer.id)
    assert updated.plan == "pro"
    assert updated.stripe_customer_id is None


def test_checkout_completed_rejects_missing_plan_metadata(checkout_webhook_db):
    dealer = _create_dealer("missing-plan@example.com")
    event = _checkout_event(dealer_id=dealer.id)
    del event["data"]["object"]["metadata"]["target_plan"]
    client = _client_with_event(event)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "checkout session missing target_plan"


def test_checkout_completed_returns_404_for_unknown_dealer(checkout_webhook_db):
    client = _client_with_event(_checkout_event(dealer_id=999))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dealer not found"
