"""Pydantic schemas for market analysis endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BrandMetrics(BaseModel):
    brand: str
    listings_count: int = Field(ge=0)
    avg_price: float | None = None
    avg_market_price: float | None = None
    avg_roi_neto: float | None = None
    opportunities_count: int = Field(default=0, ge=0)


class ROIHistogramBucket(BaseModel):
    min_roi: float
    max_roi: float
    count: int = Field(ge=0)


class ROIHistogram(BaseModel):
    buckets: list[ROIHistogramBucket] = Field(default_factory=list)
    total_count: int = Field(default=0, ge=0)


class PriceTrendPoint(BaseModel):
    date: datetime | str
    avg_price: float
    listings_count: int = Field(ge=0)


class PriceTrend(BaseModel):
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    points: list[PriceTrendPoint] = Field(default_factory=list)


class MarketStatsOut(BaseModel):
    total_listings: int = Field(ge=0)
    total_opportunities: int = Field(ge=0)
    avg_roi_neto: float | None = None
    avg_price: float | None = None
    avg_market_price: float | None = None
    by_brand: list[BrandMetrics] = Field(default_factory=list)
