import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer
from tools.api.routers.admin import get_admin_billing_service
from tools.api.schemas import DealerCreate
from tools.api.services.auth_service import create_jwt
from tools.api.services.dealer_service import DealerService
from tools.utils import db


@pytest.fixture()
def admin_controls_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "admin_controls.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-admin-controls-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, plan: str = "trial"):
    dealer, api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
                plan=plan,
            )
        )
    )
    asyncio.run(db.close_pool())
    return dealer, api_key


def _auth_headers(dealer_id: int) -> dict[str, str]:
    token = create_jwt(str(dealer_id), expires_in=3600, token_type="access")
    return {"Authorization": f"Bearer {token}"}


class FakeAdminBillingService:
    def __init__(self):
        self.calls = []

    async def ensure_customer(self, dealer):
        self.calls.append(dealer.id)
        customer_id = f"cus_admin_{dealer.id}"
        await DealerService().set_stripe_customer_id(dealer.id, customer_id)
        return customer_id


def _client_with_billing(fake_billing: FakeAdminBillingService | None = None) -> TestClient:
    app = create_app()
    if fake_billing is not None:
        app.dependency_overrides[get_admin_billing_service] = lambda: fake_billing
    return TestClient(app)


def test_admin_can_activate_and_suspend_dealer(admin_controls_db):
    admin, _key = _create_dealer("admin-controls@example.com", plan="admin")
    dealer, _dealer_key = _create_dealer("active-control@example.com")
    client = _client_with_billing()

    suspended = client.patch(
        f"/admin/dealers/{dealer.id}/active",
        json={"active": False},
        headers=_auth_headers(admin.id),
    )
    reactivated = client.patch(
        f"/admin/dealers/{dealer.id}/active",
        json={"active": True},
        headers=_auth_headers(admin.id),
    )

    assert suspended.status_code == 200
    assert suspended.json()["active"] is False
    assert reactivated.status_code == 200
    assert reactivated.json()["active"] is True


def test_admin_can_reset_dealer_usage(admin_controls_db):
    admin, _key = _create_dealer("admin-usage@example.com", plan="admin")
    dealer, _dealer_key = _create_dealer("usage-control@example.com")
    asyncio.run(DealerService().increment_calls_today(dealer.id, amount=5))
    asyncio.run(db.close_pool())
    client = _client_with_billing()

    response = client.post(
        f"/admin/dealers/{dealer.id}/usage/reset",
        headers=_auth_headers(admin.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reset_count"] == 1
    assert body["dealer"]["id"] == dealer.id
    assert body["dealer"]["calls_today"] == 0


def test_admin_can_ensure_stripe_customer(admin_controls_db):
    admin, _key = _create_dealer("admin-stripe@example.com", plan="admin")
    dealer, _dealer_key = _create_dealer("stripe-control@example.com")
    fake_billing = FakeAdminBillingService()
    client = _client_with_billing(fake_billing)

    response = client.post(
        f"/admin/dealers/{dealer.id}/stripe/customer",
        headers=_auth_headers(admin.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stripe_customer_id"] == f"cus_admin_{dealer.id}"
    assert body["dealer"]["stripe_customer_id"] == f"cus_admin_{dealer.id}"
    assert fake_billing.calls == [dealer.id]


def test_admin_controls_reject_non_admin(admin_controls_db):
    dealer, _key = _create_dealer("not-admin-control@example.com")
    client = _client_with_billing()

    response = client.patch(
        f"/admin/dealers/{dealer.id}/active",
        json={"active": False},
        headers=_auth_headers(dealer.id),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin plan required"

