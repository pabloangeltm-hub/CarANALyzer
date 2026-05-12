"""Pydantic schemas for request and response contracts."""

from tools.api.schemas.auth import APIKeyCreate, APIKeyOut, LoginIn, RegisterOut, TokenOut
from tools.api.schemas.dealers import DealerCreate, DealerOut, DealerUpdate, PlanInfo
from tools.api.schemas.health import HealthOut, ReadyOut
from tools.api.schemas.listings import (
    ListingFilter,
    ListingOut,
    PaginatedListings,
    PriceHistoryPoint,
)
from tools.api.schemas.market import (
    BrandMetrics,
    MarketStatsOut,
    PriceTrend,
    PriceTrendPoint,
    ROIHistogram,
    ROIHistogramBucket,
)
from tools.api.schemas.payments import (
    BillingPortalSessionCreate,
    BillingPortalSessionOut,
    CheckoutSessionCreate,
    CheckoutSessionOut,
)

__all__ = [
    "BrandMetrics",
    "APIKeyCreate",
    "APIKeyOut",
    "BillingPortalSessionCreate",
    "BillingPortalSessionOut",
    "CheckoutSessionCreate",
    "CheckoutSessionOut",
    "DealerCreate",
    "DealerOut",
    "DealerUpdate",
    "HealthOut",
    "ListingFilter",
    "ListingOut",
    "LoginIn",
    "MarketStatsOut",
    "PlanInfo",
    "PaginatedListings",
    "PriceHistoryPoint",
    "PriceTrend",
    "PriceTrendPoint",
    "ROIHistogram",
    "ROIHistogramBucket",
    "ReadyOut",
    "RegisterOut",
    "TokenOut",
]
