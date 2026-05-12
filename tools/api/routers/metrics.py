"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from tools.api.metrics import generate_metrics

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Endpoint publico para scrapes de Prometheus.",
    openapi_extra={"security": []},
)
async def metrics() -> Response:
    return Response(
        content=generate_metrics(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
