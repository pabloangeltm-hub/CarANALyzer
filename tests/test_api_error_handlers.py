from fastapi import FastAPI
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.errors import register_error_handlers


def test_http_exception_returns_problem_details(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())

    response = client.get("/listings/999", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Listing not found",
        "instance": "/listings/999",
        "request_id": "req-404",
    }


def test_validation_error_returns_problem_details(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())

    response = client.get("/listings", params={"year_min": "1800"})

    assert response.status_code == 422
    body = response.json()
    assert response.headers["content-type"].startswith("application/problem+json")
    assert body["type"] == "about:blank"
    assert body["title"] == "Unprocessable Entity"
    assert body["status"] == 422
    assert body["detail"] == "Request validation failed."
    assert body["instance"] == "/listings"
    assert body["errors"][0]["loc"] == ["query", "year_min"]


def test_unhandled_exception_returns_safe_problem_details():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret traceback detail")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "/boom",
    }
