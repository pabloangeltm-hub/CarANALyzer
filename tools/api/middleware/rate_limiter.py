"""In-memory rate limiting middleware for the MVP API."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests or int(os.getenv("AGARTHA_RATE_LIMIT_REQUESTS", "100"))
        self.window_seconds = window_seconds or int(os.getenv("AGARTHA_RATE_LIMIT_WINDOW_SECONDS", "60"))
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

        remaining = max(0, self.max_requests - len(hits))
        if remaining <= 0:
            retry_after = max(1, int(self.window_seconds - (now - hits[0]))) if hits else self.window_seconds
            return JSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Rate limit exceeded.",
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        hits.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        response.headers["X-RateLimit-Reset"] = str(self.window_seconds)
        return response

    @staticmethod
    def _client_key(request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key[:16]}"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"
