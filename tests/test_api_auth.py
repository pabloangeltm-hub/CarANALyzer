import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import create_dealer, update_dealer
from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.auth_service import create_jwt
from tools.utils import db


@pytest.fixture()
def auth_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "agartha_auth_test.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "test-auth-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, password: str = "password123", active: bool = True):
    dealer, api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password=password,
                plan="trial",
            )
        )
    )
    if not active:
        dealer = asyncio.run(update_dealer(dealer.id, DealerUpdate(active=False)))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer, api_key


def test_login_returns_access_and_refresh_tokens(auth_db):
    dealer, _api_key = _create_dealer("login@example.com")
    client = TestClient(create_app())

    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"] != body["refresh_token"]

    me = client.get("/dealers/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == dealer.id


def test_login_rejects_invalid_credentials_and_inactive_dealer(auth_db):
    _dealer, _api_key = _create_dealer("invalid@example.com", active=False)
    client = TestClient(create_app())

    wrong_password = client.post(
        "/auth/login",
        json={"email": "invalid@example.com", "password": "wrong-password"},
    )
    inactive = client.post(
        "/auth/login",
        json={"email": "invalid@example.com", "password": "password123"},
    )

    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Invalid email or password"
    assert inactive.status_code == 403
    assert inactive.json()["detail"] == "Dealer account is inactive"


def test_refresh_requires_refresh_token_and_returns_usable_pair(auth_db):
    dealer, _api_key = _create_dealer("refresh@example.com")
    client = TestClient(create_app())
    login = client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    tokens = login.json()

    rejected = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    refreshed = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )

    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Invalid refresh token"
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    me = client.get("/dealers/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == dealer.id


def test_refresh_rejects_inactive_dealer(auth_db):
    dealer, _api_key = _create_dealer("inactive-refresh@example.com", active=False)
    client = TestClient(create_app())
    refresh_token = create_jwt(str(dealer.id), expires_in=3600, token_type="refresh")

    response = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Dealer account is inactive"


def test_api_key_rotation_invalidates_previous_key(auth_db):
    dealer, old_api_key = _create_dealer("apikey@example.com")
    client = TestClient(create_app())
    login = client.post(
        "/auth/login",
        json={"email": "apikey@example.com", "password": "password123"},
    )

    response = client.post(
        "/auth/api-key",
        json={"name": "server-integration"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == dealer.id
    assert body["name"] == "server-integration"
    assert body["api_key"].startswith("agrt_")
    assert body["prefix"] == body["api_key"][:10]
    assert body["api_key"] != old_api_key

    old_key_response = client.get("/dealers/me", headers={"X-API-Key": old_api_key})
    new_key_response = client.get("/dealers/me", headers={"X-API-Key": body["api_key"]})
    assert old_key_response.status_code == 401
    assert new_key_response.status_code == 200
    assert new_key_response.json()["id"] == dealer.id


def test_logout_revokes_bearer_token(auth_db):
    dealer, _api_key = _create_dealer("logout@example.com")
    client = TestClient(create_app())
    access_token = create_jwt(str(dealer.id), expires_in=3600, token_type="access")

    before = client.get("/dealers/me", headers={"Authorization": f"Bearer {access_token}"})
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    after = client.get("/dealers/me", headers={"Authorization": f"Bearer {access_token}"})

    assert before.status_code == 200
    assert response.status_code == 204
    assert response.content == b""
    assert after.status_code == 401
