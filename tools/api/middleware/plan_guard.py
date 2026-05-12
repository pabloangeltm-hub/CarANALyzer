"""Plan-based daily quota guard."""

from __future__ import annotations

import os
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tools.api.dependencies.auth import get_dealer_from_bearer_token
from tools.api.dealer_store import get_dealer_by_id
from tools.api.models.plan import get_plan_limits
from tools.api.services.api_key_service import get_dealer_by_api_key
from tools.api.services.dealer_service import dealer_service
from tools.api.schemas import DealerOut

PUBLIC_PATH_PREFIXES = (
    "/auth",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class PlanGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool | None = None) -> None:
        super().__init__(app)
        self.enabled = enabled if enabled is not None else _env_bool("AGARTHA_PLAN_GUARD_ENABLED", True)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or _should_skip(request):
            return await call_next(request)

        dealer = await _dealer_from_request(request)
        if dealer is None:
            return await call_next(request)

        limits = get_plan_limits(dealer.plan)
        request.state.dealer = dealer
        request.state.plan_limits = limits
        if limits.daily_limit is not None and dealer.calls_today >= limits.daily_limit:
            return JSONResponse(
                status_code=402,
                content={
                    "type": "https://agartha.local/problems/plan-limit-exceeded",
                    "title": "Plan limit exceeded",
                    "status": 402,
                    "detail": f"Daily API call limit exceeded for plan '{dealer.plan}'.",
                    "plan": dealer.plan,
                    "daily_limit": limits.daily_limit,
                    "calls_today": dealer.calls_today,
                },
                media_type="application/problem+json",
                headers={
                    "X-Plan-Name": str(dealer.plan),
                    "X-Plan-Limit": str(limits.daily_limit),
                    "X-Plan-Remaining": "0",
                    "X-Plan-Roi-Max-Pct": (
                        "unlimited" if limits.roi_max_pct is None else str(limits.roi_max_pct)
                    ),
                },
            )

        response = await call_next(request)
        if response.status_code < 500:
            updated = await dealer_service.increment_calls_today(dealer.id)
            calls_today = updated.calls_today if updated else dealer.calls_today
            response.headers["X-Plan-Name"] = str(dealer.plan)
            response.headers["X-Plan-Roi-Max-Pct"] = (
                "unlimited" if limits.roi_max_pct is None else str(limits.roi_max_pct)
            )
            if limits.daily_limit is not None:
                response.headers["X-Plan-Limit"] = str(limits.daily_limit)
                response.headers["X-Plan-Remaining"] = str(
                    max(0, limits.daily_limit - calls_today)
                )
            else:
                response.headers["X-Plan-Limit"] = "unlimited"
                response.headers["X-Plan-Remaining"] = "unlimited"
        return response


def _should_skip(request: Request) -> bool:
    if request.method == "OPTIONS":
        return True
    path = request.url.path
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in PUBLIC_PATH_PREFIXES)


async def _dealer_from_request(request: Request) -> DealerOut | None:
    authorization = request.headers.get("Authorization")
    dealer = await get_dealer_from_bearer_token(authorization, token_type="access")
    if dealer is not None:
        return dealer

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await get_dealer_by_api_key(api_key)

    dealer_id = request.headers.get("X-Dealer-ID")
    if dealer_id:
        try:
            return await get_dealer_by_id(int(dealer_id))
        except ValueError:
            return None
    return None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}
