from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.metrics import REGISTRY, REQUESTS_IN_PROGRESS, generate_metrics


def _sample_value(name, labels):
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == name and dict(sample.labels) == labels:
                return float(sample.value)
    return 0.0


def test_prometheus_middleware_records_request_count_and_latency(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())
    count_labels = {"method": "GET", "path": "/health", "status_code": "200"}
    duration_labels = {"method": "GET", "path": "/health"}
    before_count = _sample_value("agartha_api_requests_total", count_labels)
    before_duration_count = _sample_value(
        "agartha_api_request_duration_seconds_count",
        duration_labels,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert _sample_value("agartha_api_requests_total", count_labels) == before_count + 1
    assert (
        _sample_value("agartha_api_request_duration_seconds_count", duration_labels)
        == before_duration_count + 1
    )
    assert _sample_value("agartha_api_requests_in_progress", {"method": "GET"}) == 0


def test_prometheus_middleware_can_be_disabled(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_PROMETHEUS_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())
    labels = {"method": "GET", "path": "/health", "status_code": "200"}
    before = _sample_value("agartha_api_requests_total", labels)

    response = client.get("/health")

    assert response.status_code == 200
    assert _sample_value("agartha_api_requests_total", labels) == before


def test_generate_metrics_returns_prometheus_text(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    TestClient(create_app()).get("/health")

    payload = generate_metrics().decode("utf-8")

    assert "# HELP agartha_api_requests_total" in payload
    assert 'path="/health"' in payload
    assert "# HELP agartha_api_request_duration_seconds" in payload
    REQUESTS_IN_PROGRESS.labels(method="GET").set(0)
