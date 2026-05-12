"""Application factory for the Agartha B2B API."""

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from tools.api.app_meta import API_TITLE, API_VERSION
from tools.api.errors import register_error_handlers
from tools.api.logging import configure_json_logging
from tools.api.middleware import (
    AuditLoggerMiddleware,
    InMemoryRateLimiterMiddleware,
    PlanGuardMiddleware,
    PrometheusMetricsMiddleware,
)
from tools.api.routers.admin import router as admin_router
from tools.api.routers.auth import router as auth_router
from tools.api.routers.dealers import router as dealers_router
from tools.api.routers.health import router as health_router
from tools.api.routers.listings import router as listings_router
from tools.api.routers.market import router as market_router
from tools.api.routers.metrics import router as metrics_router
from tools.api.routers.payments import router as payments_router
from tools.api.routers.webhooks import router as webhooks_router

API_DESCRIPTION = """\
Agartha B2B API — acceso programático al catálogo de vehículos de segunda mano \
con análisis de arbitraje, diagnóstico forense y métricas de mercado.

## Autenticación

Los endpoints protegidos requieren un **Bearer token** en la cabecera `Authorization`:

```
Authorization: Bearer <access_token>
```

Obtén el token con `POST /auth/login`. El token expira en **1 hora**; renuévalo \
con `POST /auth/refresh`. Los endpoints de perfil de dealer también aceptan \
`X-API-Key` en lugar del Bearer token.

## Rate Limiting

Las respuestas incluyen las cabeceras:
- `X-RateLimit-Limit` — requests permitidos por ventana
- `X-RateLimit-Remaining` — requests restantes en la ventana actual
- `Retry-After` — segundos hasta el reset del límite (solo en 429)
"""

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Login con email/contraseña, renovación de access token mediante refresh token "
            "y rotación de API key de larga duración."
        ),
    },
    {
        "name": "dealers",
        "description": (
            "Registro de concesionarios B2B, listado de cuentas y gestión del perfil propio. "
            "Autenticación temporal vía `X-Dealer-ID` / `X-API-Key` hasta que F4 implemente JWT completo."
        ),
    },
    {
        "name": "listings",
        "description": (
            "Catálogo de vehículos analizados. Soporta filtros por marca, modelo, portal, "
            "tipo de vendedor, estado forense, rango de año/precio y ROI mínimo. "
            "Paginación con `page` y `size` (máx. 100)."
        ),
    },
    {
        "name": "market",
        "description": (
            "Estadísticas agregadas del mercado: KPIs globales, métricas por marca, "
            "histograma de distribución de ROI y tendencia histórica de precios."
        ),
    },
    {
        "name": "admin",
        "description": (
            "Operaciones administrativas para KPIs internos, salud de base de datos "
            "y cambios de plan de dealers."
        ),
    },
    {
        "name": "payments",
        "description": (
            "Flujos de monetizacion Stripe para checkout de suscripciones y gestion de billing."
        ),
    },
    {
        "name": "webhooks",
        "description": "Entrypoints publicos para eventos firmados de proveedores externos.",
    },
    {
        "name": "metrics",
        "description": "Exposicion Prometheus para scraping operacional.",
    },
]


def _cors_origins() -> list[str]:
    raw = os.getenv("AGARTHA_CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


def _custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        contact={"name": "Agartha SaaS", "email": "pabloangel.tm@gmail.com"},
        tags=_OPENAPI_TAGS,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "HMAC-SHA256",
        "description": "Access token obtenido en POST /auth/login.",
    }
    schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key de larga duración para integraciones server-to-server.",
    }
    # Apply BearerAuth globally; individual public endpoints override with security=[]
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


def create_app() -> FastAPI:
    configure_json_logging()
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        openapi_tags=_OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    origins = _cors_origins()
    app.add_middleware(PrometheusMetricsMiddleware)
    app.add_middleware(InMemoryRateLimiterMiddleware)
    app.add_middleware(PlanGuardMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditLoggerMiddleware)
    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(dealers_router)
    app.include_router(health_router)
    app.include_router(listings_router)
    app.include_router(market_router)
    app.include_router(metrics_router)
    app.include_router(payments_router)
    app.include_router(webhooks_router)
    app.include_router(admin_router)
    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]
    return app


app = create_app()
