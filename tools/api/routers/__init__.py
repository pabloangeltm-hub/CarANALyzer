"""API routers."""

from tools.api.routers.auth import router as auth_router
from tools.api.routers.dealers import router as dealers_router
from tools.api.routers.health import router as health_router
from tools.api.routers.listings import router as listings_router
from tools.api.routers.market import router as market_router
from tools.api.routers.metrics import router as metrics_router
from tools.api.routers.payments import router as payments_router
from tools.api.routers.webhooks import router as webhooks_router

__all__ = [
    "auth_router",
    "dealers_router",
    "health_router",
    "listings_router",
    "market_router",
    "metrics_router",
    "payments_router",
    "webhooks_router",
]
