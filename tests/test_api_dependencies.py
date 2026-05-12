import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, update_dealer
from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.auth_service import create_jwt
from tools.utils import db


@pytest.fixture()
def api_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "agartha_test.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-dependency-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, plan: str = "trial", active: bool = True):
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
    if not active:
        dealer = asyncio.run(update_dealer(dealer.id, DealerUpdate(active=False)))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer, api_key


def _access_token(dealer_id: int) -> str:
    return create_jwt(str(dealer_id), expires_in=3600, token_type="access")


def test_get_current_dealer_accepts_bearer_token(api_db):
    dealer, _api_key = _create_dealer("bearer@example.com")
    client = TestClient(create_app())

    response = client.get(
        "/dealers/me",
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == dealer.id
    assert response.json()["email"] == "bearer@example.com"


def test_get_current_dealer_accepts_api_key(api_db):
    dealer, api_key = _create_dealer("api-key@example.com")
    client = TestClient(create_app())

    response = client.get("/dealers/me", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    assert response.json()["id"] == dealer.id


def test_current_active_dealer_rejects_inactive_account(api_db):
    dealer, _api_key = _create_dealer("inactive@example.com", active=False)
    client = TestClient(create_app())

    response = client.get(
        "/dealers/me",
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Dealer account is inactive"


def test_auth_api_key_uses_current_dealer_dependency(api_db):
    dealer, _api_key = _create_dealer("rotate@example.com")
    client = TestClient(create_app())

    response = client.post(
        "/auth/api-key",
        json={"name": "ci-key"},
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == dealer.id
    assert body["name"] == "ci-key"
    assert body["api_key"].startswith("agrt_")
    assert body["prefix"] == body["api_key"][:10]


def test_admin_dependency_accepts_admin_bearer_token(api_db):
    admin, _api_key = _create_dealer("admin@example.com", plan="admin")
    dealer, _dealer_key = _create_dealer("basic@example.com")
    client = TestClient(create_app())

    denied = client.get(
        "/admin/health",
        headers={"Authorization": f"Bearer {_access_token(dealer.id)}"},
    )
    allowed = client.get(
        "/admin/health",
        headers={"Authorization": f"Bearer {_access_token(admin.id)}"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Admin plan required"
    assert allowed.status_code == 200
    assert allowed.json()["database"] == "ok"
