import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, update_dealer
from tools.api.models.plan import PlanName
from tools.api.routers.payments import get_billing_service
from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.auth_service import create_jwt
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import CheckoutSessionResult, StripeServiceError
from tools.utils import db


@pytest.fixture()
def payments_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "payments_checkout.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-payments-secret-with-at-least-32-bytes")
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

    async def create_checkout_session(
        self,
        *,
        dealer,
        target_plan,
        success_url=None,
        cancel_url=None,
    ):
        self.calls.append(
            {
                "dealer_id": dealer.id,
                "target_plan": target_plan,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        if self.error:
            raise self.error
        plan = target_plan if isinstance(target_plan, PlanName) else PlanName(target_plan)
        return CheckoutSessionResult(
            id="cs_test_123",
            url="https://checkout.stripe.test/cs_test_123",
            customer_id="cus_test_123",
            plan=plan,
        )


def _client_with_billing(fake_billing: FakeBillingService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_billing_service] = lambda: fake_billing
    return TestClient(app)


def test_checkout_creates_stripe_session_for_active_dealer(payments_db):
    dealer, _api_key = _create_dealer("checkout@example.com")
    fake_billing = FakeBillingService()
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/checkout",
        json={
            "plan": "elite",
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.test/cs_test_123",
        "customer_id": "cus_test_123",
        "plan": "elite",
    }
    assert fake_billing.calls == [
        {
            "dealer_id": dealer.id,
            "target_plan": PlanName.ELITE,
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        }
    ]


def test_checkout_requires_authenticated_dealer(payments_db):
    client = _client_with_billing(FakeBillingService())

    response = client.post("/payments/checkout", json={"plan": "starter"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Dealer credentials required"


def test_checkout_rejects_inactive_dealer(payments_db):
    dealer, _api_key = _create_dealer("inactive-checkout@example.com", active=False)
    client = _client_with_billing(FakeBillingService())

    response = client.post(
        "/payments/checkout",
        json={"plan": "starter"},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Dealer account is inactive"


def test_checkout_maps_non_billable_plan_to_bad_request(payments_db):
    dealer, _api_key = _create_dealer("trial-checkout@example.com")
    fake_billing = FakeBillingService(error=StripeServiceError("plan 'free' is not billable"))
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/checkout",
        json={"plan": "free"},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "plan 'free' is not billable"


def test_checkout_maps_stripe_configuration_error(payments_db):
    dealer, _api_key = _create_dealer("config-checkout@example.com")
    fake_billing = FakeBillingService(error=StripeConfigurationError("STRIPE_PRICE_PRO is required"))
    client = _client_with_billing(fake_billing)

    response = client.post(
        "/payments/checkout",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "STRIPE_PRICE_PRO is required"
