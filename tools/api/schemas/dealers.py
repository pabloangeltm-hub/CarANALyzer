"""Pydantic schemas for dealer management endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from tools.api.models.plan import PlanName, get_plan_limits, normalize_plan


class DealerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)
    plan: PlanName = "free"

    @field_validator("plan", mode="before")
    @classmethod
    def normalize_plan_name(cls, value: PlanName | str) -> PlanName:
        return normalize_plan(value)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class DealerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    plan: PlanName | None = None
    active: bool | None = None

    @field_validator("plan", mode="before")
    @classmethod
    def normalize_plan_name(cls, value: PlanName | str | None) -> PlanName | None:
        return normalize_plan(value) if value is not None else None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value is not None else None


class PlanInfo(BaseModel):
    plan: PlanName
    daily_limit: int | None
    alerts_enabled: bool
    roi_max_pct: float | None
    history_days: int | None
    api_key_access: bool
    forensic_full: bool
    export_enabled: bool
    poll_interval_minutes: int | None


class DealerOut(BaseModel):
    id: int
    name: str
    email: str
    plan: PlanName
    active: bool = True
    calls_today: int = Field(default=0, ge=0)
    api_key_prefix: str | None = None
    stripe_customer_id: str | None = None
    created_at: datetime | str | None = None

    @field_validator("plan", mode="before")
    @classmethod
    def normalize_plan_name(cls, value: PlanName | str) -> PlanName:
        return normalize_plan(value)

    @property
    def plan_info(self) -> PlanInfo:
        limits = get_plan_limits(self.plan)
        return PlanInfo(
            plan=limits.plan,
            daily_limit=limits.daily_limit,
            alerts_enabled=limits.alerts_enabled,
            roi_max_pct=limits.roi_max_pct,
            history_days=limits.history_days,
            api_key_access=limits.api_key_access,
            forensic_full=limits.forensic_full,
            export_enabled=limits.export_enabled,
            poll_interval_minutes=limits.poll_interval_minutes,
        )
