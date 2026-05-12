"""Prometheus metrics for the Agartha API."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


REGISTRY = CollectorRegistry(auto_describe=True)

REQUESTS = Counter(
    "agartha_api_requests",
    "Total HTTP requests handled by the Agartha API.",
    ("method", "path", "status_code"),
    registry=REGISTRY,
)
REQUEST_DURATION = Histogram(
    "agartha_api_request_duration_seconds",
    "HTTP request latency in seconds.",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)
REQUESTS_IN_PROGRESS = Gauge(
    "agartha_api_requests_in_progress",
    "HTTP requests currently being processed by the Agartha API.",
    ("method",),
    registry=REGISTRY,
)


def generate_metrics() -> bytes:
    return generate_latest(REGISTRY)
