"""Pydantic schemas for listing API responses."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class PriceHistoryPoint(BaseModel):
    price: float
    scraped_at: datetime | str


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    portal: str
    ad_id: str
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    mileage: int | None = None
    price: float | None = None
    market_price: float | None = None
    roi_bruto: float | None = None
    roi_neto: float | None = None
    repair_cost: float | None = None
    condition_score: float | None = None
    images_count: int | None = None
    seller_type: str | None = None
    location: str | None = None
    price_history: list[PriceHistoryPoint] = Field(
        default_factory=list,
        validation_alias=AliasChoices("price_history", "price_history_json"),
    )
    forensic_status: str | None = None
    forensic_summary: str | None = None
    url: str | None = None
    scraped_at: datetime | str | None = None
    roi_redacted: bool = False

    @field_validator("price_history", mode="before")
    @classmethod
    def parse_price_history(cls, value: Any) -> Any:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return value


class ListingFilter(BaseModel):
    q: str | None = None
    brand: str | None = None
    model: str | None = None
    portal: str | None = None
    seller_type: str | None = None
    forensic_status: str | None = None
    year_min: int | None = Field(default=None, ge=1900, le=2099)
    year_max: int | None = Field(default=None, ge=1900, le=2099)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    roi_min: float | None = None

    @field_validator("q", "brand", "model", "portal", "seller_type", "forensic_status", mode="before")
    @classmethod
    def clean_text_filter(cls, value: Any) -> Any:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_ranges(self) -> "ListingFilter":
        if (
            self.year_min is not None
            and self.year_max is not None
            and self.year_min > self.year_max
        ):
            raise ValueError("year_min cannot be greater than year_max")
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min cannot be greater than price_max")
        return self


class PaginatedListings(BaseModel):
    items: list[ListingOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
