import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, get_dealer_by_id
from tools.api.routers import webhooks
from tools.api.routers.webhooks import get_webhook_billing_service
from tools.api.schemas import DealerCreate
from tools.utils import db


@pytest.fixture()
def stripe_webhooks_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "stripe_webhooks_integration.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_trial_dealer(email: str):
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


class QueueWebhookBillingService:
    def __init__(self, events):
        self.events = list(events)
        self.calls = []

    def construct_webhook_event(self, payload, signature):
        self.calls.append((payload, signature))
        return self.events.pop(0)


def _checkout_completed_event(dealer_id: int, customer_id: str):
    return {
        "id": "evt_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "client_reference_id": str(dealer_id),
                "metadata": {"dealer_id": str(dealer_id), "target_plan": "elite"},
            }
        },
    }


def _invoice_failed_event(customer_id: str):
    return {
        "id": "evt_invoice_failed",
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": customer_id}},
    }


def _subscription_deleted_event(customer_id: str):
    return {
        "id": "evt_subscription_deleted",
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": customer_id}},
    }


def test_stripe_webhook_lifecycle_upgrade_email_and_downgrade(stripe_webhooks_db, monkeypatch):
    dealer = _create_trial_dealer("lifecycle@example.com")
    customer_id = "cus_lifecycle_123"
    fake_billing = QueueWebhookBillingService(
        [
            _checkout_completed_event(dealer.id, customer_id),
            _invoice_failed_event(customer_id),
            _subscription_deleted_event(customer_id),
        ]
    )
    sent = []

    async def fake_send_payment_failed_email(*, to, dealer_name, settings=None):
        sent.append({"to": to, "dealer_name": dealer_name, "settings": settings})
        return {"id": "email_lifecycle"}

    monkeypatch.setattr(webhooks, "send_payment_failed_email", fake_send_payment_failed_email)
    app = create_app()
    app.dependency_overrides[get_webhook_billing_service] = lambda: fake_billing
    client = TestClient(app)

    checkout = client.post("/webhooks/stripe", content=b"checkout", headers={"Stripe-Signature": "sig-1"})
    after_checkout = _reload_dealer(dealer.id)
    payment_failed = client.post("/webhooks/stripe", content=b"invoice", headers={"Stripe-Signature": "sig-2"})
    after_failed = _reload_dealer(dealer.id)
    deleted = client.post("/webhooks/stripe", content=b"deleted", headers={"Stripe-Signature": "sig-3"})
    after_deleted = _reload_dealer(dealer.id)

    assert checkout.status_code == 200
    assert checkout.json()["type"] == "checkout.session.completed"
    assert after_checkout.plan == "elite"
    assert after_checkout.stripe_customer_id == customer_id

    assert payment_failed.status_code == 200
    assert payment_failed.json()["type"] == "invoice.payment_failed"
    assert after_failed.plan == "elite"
    assert sent == [{"to": dealer.email, "dealer_name": dealer.name, "settings": None}]

    assert deleted.status_code == 200
    assert deleted.json()["type"] == "customer.subscription.deleted"
    assert after_deleted.plan == "free"
    assert after_deleted.stripe_customer_id == customer_id
    assert fake_billing.calls == [
        (b"checkout", "sig-1"),
        (b"invoice", "sig-2"),
        (b"deleted", "sig-3"),
    ]
