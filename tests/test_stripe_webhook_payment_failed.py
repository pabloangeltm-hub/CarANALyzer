import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer
from tools.api.routers import webhooks
from tools.api.routers.webhooks import get_webhook_billing_service
from tools.api.schemas import DealerCreate
from tools.api.services.dealer_service import DealerService
from tools.utils import db


@pytest.fixture()
def payment_failed_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "payment_failed_webhook.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer_with_customer(email: str, customer_id: str):
    dealer, _api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
            )
        )
    )
    dealer = asyncio.run(DealerService().set_stripe_customer_id(dealer.id, customer_id))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer


class FakeInvoiceBillingService:
    def __init__(self, event):
        self.event = event

    def construct_webhook_event(self, payload, signature):
        return self.event


def _client_with_event(event) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_webhook_billing_service] = lambda: FakeInvoiceBillingService(event)
    return TestClient(app)


def _invoice_failed_event(customer="cus_failed_123"):
    return {
        "id": "evt_invoice_failed_123",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_failed_123",
                "customer": customer,
            }
        },
    }


def test_invoice_payment_failed_sends_email_to_dealer(payment_failed_db, monkeypatch):
    dealer = _create_dealer_with_customer("failed@example.com", "cus_failed_123")
    sent = []

    async def fake_send_payment_failed_email(*, to, dealer_name, settings=None):
        sent.append({"to": to, "dealer_name": dealer_name, "settings": settings})
        return {"id": "email_123"}

    monkeypatch.setattr(webhooks, "send_payment_failed_email", fake_send_payment_failed_email)
    client = _client_with_event(_invoice_failed_event())

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "id": "evt_invoice_failed_123",
        "type": "invoice.payment_failed",
    }
    assert sent == [
        {"to": dealer.email, "dealer_name": dealer.name, "settings": None}
    ]


def test_invoice_payment_failed_requires_customer(payment_failed_db, monkeypatch):
    async def fake_send_payment_failed_email(**kwargs):
        raise AssertionError("email should not be sent")

    monkeypatch.setattr(webhooks, "send_payment_failed_email", fake_send_payment_failed_email)
    client = _client_with_event(_invoice_failed_event(customer=None))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invoice missing customer"


def test_invoice_payment_failed_unknown_customer_returns_404(payment_failed_db, monkeypatch):
    async def fake_send_payment_failed_email(**kwargs):
        raise AssertionError("email should not be sent")

    monkeypatch.setattr(webhooks, "send_payment_failed_email", fake_send_payment_failed_email)
    client = _client_with_event(_invoice_failed_event(customer="cus_unknown"))

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dealer not found"

