from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.routers.webhooks import get_webhook_billing_service
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import StripeServiceError


class FakeWebhookBillingService:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls = []

    def construct_webhook_event(self, payload, signature):
        self.calls.append((payload, signature))
        if self.error:
            raise self.error
        return {"id": "evt_test_123", "type": "customer.created"}


def _client_with_billing(fake_billing: FakeWebhookBillingService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_webhook_billing_service] = lambda: fake_billing
    return TestClient(app)


def test_stripe_webhook_validates_raw_payload_and_signature(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    fake_billing = FakeWebhookBillingService()
    client = _client_with_billing(fake_billing)
    payload = b'{"id":"evt_test_123","type":"customer.created"}'

    response = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": "t=123,v1=sig"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "id": "evt_test_123",
        "type": "customer.created",
    }
    assert fake_billing.calls == [(payload, "t=123,v1=sig")]


def test_stripe_webhook_is_public_without_dealer_credentials(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    fake_billing = FakeWebhookBillingService()
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert fake_billing.calls == [(b"{}", "sig")]


def test_stripe_webhook_maps_missing_or_invalid_signature(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    fake_billing = FakeWebhookBillingService(error=StripeServiceError("Stripe signature header is required"))
    client = _client_with_billing(fake_billing)

    response = client.post("/webhooks/stripe", content=b"{}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Stripe signature header is required"
    assert fake_billing.calls == [(b"{}", None)]


def test_stripe_webhook_maps_configuration_error(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    fake_billing = FakeWebhookBillingService(error=StripeConfigurationError("STRIPE_WEBHOOK_SECRET is required"))
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "STRIPE_WEBHOOK_SECRET is required"
