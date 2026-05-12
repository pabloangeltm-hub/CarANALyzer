from fastapi.testclient import TestClient
from prometheus_client import CONTENT_TYPE_LATEST

from tools.api.app import create_app
from tools.api.metrics import REGISTRY


def _sample_value(name, labels):
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == name and dict(sample.labels) == labels:
                return float(sample.value)
    return 0.0


def test_metrics_endpoint_returns_prometheus_text(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST
    assert "# HELP agartha_api_requests_total" in response.text
    assert 'path="/health"' in response.text


def test_metrics_endpoint_is_not_counted_by_metrics_middleware(monkeypatch):
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_ENABLED", "0")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")
    client = TestClient(create_app())
    labels = {"method": "GET", "path": "/metrics", "status_code": "200"}
    before = _sample_value("agartha_api_requests_total", labels)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert _sample_value("agartha_api_requests_total", labels) == before
