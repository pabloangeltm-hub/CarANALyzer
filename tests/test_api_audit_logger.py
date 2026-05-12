import json

from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.security import create_token


def test_audit_logger_writes_jsonl_event(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_PATH", str(log_path))
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")

    client = TestClient(create_app())
    token = create_token("42", expires_in=3600, token_type="access")

    response = client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-ID": "req-test-1",
            "X-Forwarded-For": "203.0.113.10, 10.0.0.1",
            "User-Agent": "pytest",
        },
    )

    assert response.status_code == 204
    assert response.headers["X-Request-ID"] == "req-test-1"

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["request_id"] == "req-test-1"
    assert event["dealer_id"] == 42
    assert event["method"] == "POST"
    assert event["path"] == "/auth/logout"
    assert event["endpoint"] == "/auth/logout"
    assert event["status_code"] == 204
    assert event["client_ip"] == "203.0.113.10"
    assert event["user_agent"] == "pytest"
    assert event["latency_ms"] >= 0
    assert event["error"] is False
    assert "Authorization" not in event
