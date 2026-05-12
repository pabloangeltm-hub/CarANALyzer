from collections.abc import AsyncIterator

import aiosqlite
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.dependencies import get_db


def test_health_is_public_and_fast(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["uptime_s"] >= 0


def test_ready_returns_ok_when_db_ping_succeeds(tmp_path, monkeypatch):
    db_path = tmp_path / "ready.db"
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    app = create_app()

    async def override_get_db() -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(db_path)
        try:
            yield conn
        finally:
            await conn.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["latency_ms"] >= 0


def test_ready_returns_503_when_db_ping_fails(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    app = create_app()

    class BrokenConnection:
        async def execute(self, _query: str):
            raise aiosqlite.OperationalError("database is down")

    async def override_get_db():
        yield BrokenConnection()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"
