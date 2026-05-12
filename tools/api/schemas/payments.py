"""Pydantic schemas for payments and billing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from tools.api.models.plan import PlanName, normalize_plan


class CheckoutSessionCreate(BaseModel):
    plan: PlanName = Field(description="Target paid plan for the Stripe subscription.")
    success_url: str | None = Field(
        default=None,
        description="Optional absolute redirect URL after successful checkout.",
    )
    cancel_url: str | None = Field(
        default=None,
        description="Optional absolute redirect URL when checkout is cancelled.",
    )

    @field_validator("plan", mode="before")
    @classmethod
    def normalize_plan_name(cls, value: PlanName | str) -> PlanName:
        return normalize_plan(value)


class CheckoutSessionOut(BaseModel):
    id: str
    url: str
    customer_id: str
    plan: PlanName


class BillingPortalSessionCreate(BaseModel):
    return_url: str | None = Field(
        default=None,
        description="Optional absolute redirect URL after the customer leaves the billing portal.",
    )


class BillingPortalSessionOut(BaseModel):
    id: str
    url: str
    customer_id: str
