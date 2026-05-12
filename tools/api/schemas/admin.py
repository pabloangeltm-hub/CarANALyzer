"""Pydantic schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from tools.api.models.plan import PlanName, normalize_plan


class AdminStatsOut(BaseModel):
    total_dealers: int = Field(ge=0)
    active_dealers: int = Field(ge=0)
    free_dealers: int = Field(ge=0)
    starter_dealers: int = Field(ge=0)
    pro_dealers: int = Field(ge=0)
    elite_dealers: int = Field(ge=0)
    admin_dealers: int = Field(ge=0)
    calls_today: int = Field(ge=0)
    total_listings: int = Field(ge=0)
    total_opportunities: int = Field(ge=0)
    avg_roi_neto: float | None = None
    generated_at: datetime


class AdminPlanUpdate(BaseModel):
    plan: PlanName

    @field_validator("plan", mode="before")
    @classmethod
    def normalize_plan_name(cls, value: PlanName | str) -> PlanName:
        return normalize_plan(value)


class AdminActiveUpdate(BaseModel):
    active: bool


class AdminUsageResetOut(BaseModel):
    dealer: "DealerOut"
    reset_count: int = Field(ge=0)


class AdminStripeCustomerOut(BaseModel):
    dealer: "DealerOut"
    stripe_customer_id: str


class AdminHealthOut(BaseModel):
    status: str
    database: str
    dealers_table: bool
    listings_table: bool
    checked_at: datetime


from tools.api.schemas.dealers import DealerOut  # noqa: E402

AdminUsageResetOut.model_rebuild()
AdminStripeCustomerOut.model_rebuild()
