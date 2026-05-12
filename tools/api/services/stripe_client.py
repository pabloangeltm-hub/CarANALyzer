"""Stripe SDK configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from types import ModuleType

import stripe

from tools.api.app_meta import API_VERSION


class StripeConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class StripeSettings:
    secret_key: str
    webhook_secret: str | None = None
    starter_price_id: str | None = None
    pro_price_id: str | None = None
    elite_price_id: str | None = None
    basic_price_id: str | None = None
    premium_price_id: str | None = None
    public_url: str | None = None
    max_network_retries: int = 2


def load_stripe_settings(*, require_secret: bool = True) -> StripeSettings:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if require_secret and not secret_key:
        raise StripeConfigurationError("STRIPE_SECRET_KEY is required")

    return StripeSettings(
        secret_key=secret_key,
        webhook_secret=_optional_env("STRIPE_WEBHOOK_SECRET"),
        starter_price_id=_optional_env("STRIPE_PRICE_STARTER"),
        pro_price_id=_optional_env("STRIPE_PRICE_PRO") or _optional_env("STRIPE_PRICE_BASIC"),
        elite_price_id=_optional_env("STRIPE_PRICE_ELITE") or _optional_env("STRIPE_PRICE_PREMIUM"),
        basic_price_id=_optional_env("STRIPE_PRICE_BASIC"),
        premium_price_id=_optional_env("STRIPE_PRICE_PREMIUM"),
        public_url=_optional_env("AGARTHA_PUBLIC_URL"),
        max_network_retries=int(os.getenv("STRIPE_MAX_NETWORK_RETRIES", "2")),
    )


def configure_stripe(settings: StripeSettings | None = None) -> ModuleType:
    settings = settings or load_stripe_settings()
    stripe.api_key = settings.secret_key
    stripe.max_network_retries = settings.max_network_retries
    stripe.set_app_info("Agartha", version=API_VERSION)
    return stripe


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None
