"""
One-time setup script - create Stripe Products and Prices for Agartha B2B plans.

Run once per environment (test mode first, then production):

    python tools/api/setup_stripe_products.py

Prerequisites:
    STRIPE_SECRET_KEY must be set in .env (sk_test_... for test, sk_live_... for prod).

Output:
    Prints STRIPE_PRICE_STARTER, STRIPE_PRICE_PRO and STRIPE_PRICE_ELITE values to add to .env.
    Idempotent: safe to re-run; existing products/prices are reused.
"""

from __future__ import annotations

import sys
from typing import Optional

import stripe

from tools.api.services.stripe_client import configure_stripe, load_stripe_settings


_PLANS = [
    {
        "env_var": "STRIPE_PRICE_STARTER",
        "product_name": "Agartha Starter",
        "product_description": (
            "500 API calls/day - ROI visible up to 15% - Real-time arbitrage alerts"
        ),
        "metadata_plan": "starter",
        "unit_amount": 4900,
        "currency": "eur",
    },
    {
        "env_var": "STRIPE_PRICE_PRO",
        "product_name": "Agartha Pro",
        "product_description": (
            "2,000 API calls/day - ROI visible up to 30% - Exports and full forensic detail"
        ),
        "metadata_plan": "pro",
        "unit_amount": 9900,
        "currency": "eur",
    },
    {
        "env_var": "STRIPE_PRICE_ELITE",
        "product_name": "Agartha Elite",
        "product_description": (
            "Unlimited API calls - Full ROI visibility - Priority support"
        ),
        "metadata_plan": "elite",
        "unit_amount": 19900,
        "currency": "eur",
    },
]

_APP_METADATA_KEY = "agartha_plan"


def _find_product(plan: str) -> Optional[stripe.Product]:
    """Return active Agartha product for *plan*, or None."""
    results = stripe.Product.search(
        query=f'metadata["{_APP_METADATA_KEY}"]:"{plan}"',
        limit=10,
    )
    for product in results.auto_paging_iter():
        if product.active:
            return product
    return None


def _find_price(product_id: str, currency: str, unit_amount: int) -> Optional[stripe.Price]:
    """Return active recurring monthly price for *product_id*, or None."""
    prices = stripe.Price.list(
        product=product_id,
        active=True,
        currency=currency,
        type="recurring",
        limit=20,
    )
    for price in prices.auto_paging_iter():
        if (
            price.recurring
            and price.recurring.interval == "month"
            and price.unit_amount == unit_amount
        ):
            return price
    return None


def _upsert_plan(spec: dict) -> str:
    """Ensure product + price exist; return price_id."""
    plan = spec["metadata_plan"]
    name = spec["product_name"]
    currency = spec["currency"]
    unit_amount = spec["unit_amount"]

    existing_product = _find_product(plan)
    if existing_product:
        product = existing_product
        print(f"  product  [exists]  {product.id}  ({name})")
    else:
        product = stripe.Product.create(
            name=name,
            description=spec["product_description"],
            metadata={_APP_METADATA_KEY: plan},
        )
        print(f"  product  [created] {product.id}  ({name})")

    existing_price = _find_price(product.id, currency, unit_amount)
    if existing_price:
        price = existing_price
        amount_fmt = f"EUR {price.unit_amount / 100:.2f}/mo"
        print(f"  price    [exists]  {price.id}  ({amount_fmt})")
    else:
        price = stripe.Price.create(
            product=product.id,
            unit_amount=unit_amount,
            currency=currency,
            recurring={"interval": "month"},
            metadata={_APP_METADATA_KEY: plan},
        )
        amount_fmt = f"EUR {price.unit_amount / 100:.2f}/mo"
        print(f"  price    [created] {price.id}  ({amount_fmt})")

    return price.id


def main() -> None:
    try:
        settings = load_stripe_settings()
    except Exception as exc:
        print(f"\n[error] {exc}", file=sys.stderr)
        print("Set STRIPE_SECRET_KEY in your .env file and retry.", file=sys.stderr)
        sys.exit(1)

    configure_stripe(settings)

    mode = "TEST" if settings.secret_key.startswith("sk_test_") else "LIVE"
    print(f"\n=== Agartha - Stripe product setup ({mode} mode) ===\n")

    results: dict[str, str] = {}
    for spec in _PLANS:
        print(f"[{spec['metadata_plan'].upper()}]")
        results[spec["env_var"]] = _upsert_plan(spec)
        print()

    print("=== Add to .env ===\n")
    for env_var, price_id in results.items():
        print(f"{env_var}={price_id}")
    print()

    if mode == "TEST":
        print(
            "NOTE: These are TEST mode IDs. Re-run with a sk_live_... key when "
            "ready for production to generate live price IDs."
        )


if __name__ == "__main__":
    main()
