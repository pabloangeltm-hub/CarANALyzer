import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, update_dealer
from tools.api.routers.payments import get_billing_service
from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.auth_service import create_jwt
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import BillingPortalSessionResult, StripeServiceError
from tools.utils import db


@pytest.fixture()
def portal_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "payments_portal.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-portal-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, active: bool = True):
    dealer, api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
            )
        )
    )
    if not active:
        dealer = asyncio.run(update_dealer(dealer.id, DealerUpdate(active=False)))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer, api_key


def _access_token(dealer_id: int) -> str:
    return create_jwt(str(dealer_id), expires_in=3600, token_type="access")


class FakeBillingService:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls = []

    async def create_billing_portal_session(
        self,
        *,
        dealer,
        return_url=None,
    ):
        self.calls.append({"dealer_id": dealer.id, "return_url": return_url})
        if self.error:
            raise self.error
        return BillingPortalSessionResult(
            id="bps_test_123",
            url="https://billing.stripe.test/bps_test_123",
            customer_id=dealer.stripe_customer_id or "cus_created_123",
        )


def _client_with_billing(fake_billing: FakeBillingService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_billing_service] = lambda: fake_billing
    return TestClient(app)


def test_portal_creates_billing_session_for_active_dealer(portal_db):
    dealer, _api_key = _create_dealer("portal@example.com")
    fake_billing = FakeBillingService()
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/portal",
        json={"return_url": "https://app.example.com/account"},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "bps_test_123",
        "url": "https://billing.stripe.test/bps_test_123",
        "customer_id": "cus_created_123",
    }
    assert fake_billing.calls == [
        {"dealer_id": dealer.id, "return_url": "https://app.example.com/account"}
    ]


def test_portal_requires_authenticated_dealer(portal_db):
    client = _client_with_billing(FakeBillingService())

    response = client.post("/payments/portal", json={})

    assert response.status_code == 401
    assert response.json()["detail"] == "Dealer credentials required"


def test_portal_rejects_inactive_dealer(portal_db):
    dealer, _api_key = _create_dealer("inactive-portal@example.com", active=False)
    client = _client_with_billing(FakeBillingService())

    response = client.post(
        "/payments/portal",
        json={},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Dealer account is inactive"


def test_portal_maps_stripe_configuration_error(portal_db):
    dealer, _api_key = _create_dealer("config-portal@example.com")
    fake_billing = FakeBillingService(error=StripeConfigurationError("AGARTHA_PUBLIC_URL is required"))
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/portal",
        json={},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AGARTHA_PUBLIC_URL is required"


def test_portal_maps_stripe_service_error(portal_db):
    dealer, _api_key = _create_dealer("service-portal@example.com")
    fake_billing = FakeBillingService(error=StripeServiceError("Stripe response missing 'url'"))
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/portal",
        json={},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Stripe response missing 'url'"

