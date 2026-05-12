import asyncio

import pytest
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dealer_store import get_dealer_row_by_email
from tools.api.services.api_key_service import get_dealer_by_api_key
from tools.api.services.auth_service import decode_jwt, verify_jwt
from tools.utils import db


@pytest.fixture()
def auth_hardening_db(tmp_path, monkeypatch):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "auth_hardening.db")
    db._backup_done = False
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("JWT_SECRET", "auth-hardening-secret-with-at-least-32-bytes")
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def test_registering_dealer_stores_bcrypt_hash_and_login_returns_jwt(auth_hardening_db):
    client = TestClient(create_app())
    created = client.post(
        "/dealers",
        json={
            "name": "Hardening Dealer",
            "email": "hardening@example.com",
            "password": "password123",
            "plan": "trial",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "hardening@example.com", "password": "password123"},
    )

    row = asyncio.run(get_dealer_row_by_email("hardening@example.com"))
    payload = decode_jwt(login.json()["access_token"], token_type="access")

    assert created.status_code == 201
    assert row is not None
    assert row["password_hash"].startswith("$2")
    assert login.status_code == 200
    assert payload is not None
    assert payload["sub"] == str(created.json()["id"])
    assert payload["jti"]


def test_logout_blacklists_access_token(auth_hardening_db):
    client = TestClient(create_app())
    client.post(
        "/dealers",
        json={
            "name": "Logout Dealer",
            "email": "logout-hardening@example.com",
            "password": "password123",
            "plan": "trial",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "logout-hardening@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    before = asyncio.run(verify_jwt(token, token_type="access"))
    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    after = asyncio.run(verify_jwt(token, token_type="access"))

    assert before is not None
    assert logout.status_code == 204
    assert after is None


def test_api_key_route_uses_service_generated_key(auth_hardening_db):
    client = TestClient(create_app())
    client.post(
        "/dealers",
        json={
            "name": "Key Dealer",
            "email": "key-hardening@example.com",
            "password": "password123",
            "plan": "trial",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "key-hardening@example.com", "password": "password123"},
    )
    response = client.post(
        "/auth/api-key",
        json={"name": "server"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    body = response.json()
    dealer = asyncio.run(get_dealer_by_api_key(body["api_key"]))

    assert response.status_code == 200
    assert body["api_key"].startswith("agrt_")
    assert body["prefix"] == body["api_key"][:10]
    assert dealer is not None
    assert dealer.email == "key-hardening@example.com"
