"""Public health and readiness endpoints."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Response, status

from tools.api.app_meta import API_VERSION
from tools.api.dependencies import get_db
from tools.api.schemas.health import HealthOut, ReadyOut

router = APIRouter(tags=["health"])
_STARTED_AT = time.monotonic()


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Liveness check",
    description="Endpoint publico y rapido para comprobar que el proceso API esta vivo.",
)
async def health() -> HealthOut:
    return HealthOut(version=API_VERSION, uptime_s=round(time.monotonic() - _STARTED_AT, 3))


@router.get(
    "/ready",
    response_model=ReadyOut,
    summary="Readiness check",
    description="Endpoint publico para comprobar que la API puede atender trafico y llegar a SQLite.",
)
async def ready(
    response: Response,
    conn: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> ReadyOut:
    started = time.perf_counter()
    checked_at = datetime.now()
    try:
        await conn.execute("SELECT 1")
    except aiosqlite.Error:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyOut(
            status="degraded",
            database="error",
            checked_at=checked_at,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    return ReadyOut(
        status="ok",
        database="ok",
        checked_at=checked_at,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
