"""Health check response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    uptime_s: float = Field(ge=0)


class ReadyOut(BaseModel):
    status: str
    database: str
    checked_at: datetime
    latency_ms: float = Field(ge=0)
