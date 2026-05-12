"""Prometheus instrumentation middleware for the B2B API."""

from __future__ import annotations

import os
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tools.api.metrics import REQUEST_DURATION, REQUESTS, REQUESTS_IN_PROGRESS


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool | None = None) -> None:
        super().__init__(app)
        self.enabled = enabled if enabled is not None else _env_bool("AGARTHA_PROMETHEUS_ENABLED", True)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        status_code = 500
        started = time.perf_counter()
        REQUESTS_IN_PROGRESS.labels(method=method).inc()
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            path = _route_path(request)
            duration = time.perf_counter() - started
            REQUESTS.labels(method=method, path=path, status_code=str(status_code)).inc()
            REQUEST_DURATION.labels(method=method, path=path).observe(duration)
            REQUESTS_IN_PROGRESS.labels(method=method).dec()


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return str(getattr(route, "path", request.url.path))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}
