"""Billing service built on top of Stripe."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any, Protocol

from tools.api.models.plan import PlanName, normalize_plan
from tools.api.schemas import DealerOut
from tools.api.services.dealer_service import DealerService, dealer_service
from tools.api.services.stripe_client import (
    StripeConfigurationError,
    StripeSettings,
    configure_stripe,
    load_stripe_settings,
)


_PLAN_PRICE_FIELDS = {
    PlanName.STARTER: ("starter_price_id", "STRIPE_PRICE_STARTER"),
    PlanName.PRO: ("pro_price_id", "STRIPE_PRICE_PRO"),
    PlanName.ELITE: ("elite_price_id", "STRIPE_PRICE_ELITE"),
}


class StripeServiceError(RuntimeError):
    pass


class DealerBillingStore(Protocol):
    async def set_stripe_customer_id(
        self,
        dealer_id: int,
        stripe_customer_id: str | None,
    ) -> DealerOut | None:
        ...


@dataclass(frozen=True)
class CheckoutSessionResult:
    id: str
    url: str
    customer_id: str
    plan: PlanName


@dataclass(frozen=True)
class BillingPortalSessionResult:
    id: str
    url: str
    customer_id: str


class StripeBillingService:
    """Create Stripe billing objects for dealers.

    The Stripe SDK is synchronous. The service methods are async because account
    state persistence is async and routers can await one boundary consistently.
    """

    def __init__(
        self,
        *,
        settings: StripeSettings | None = None,
        stripe_api: ModuleType | Any | None = None,
        dealers: DealerBillingStore | None = None,
    ) -> None:
        self.settings = settings or load_stripe_settings()
        self.stripe = stripe_api or configure_stripe(self.settings)
        self.dealers = dealers or dealer_service

    def price_id_for_plan(self, plan: PlanName | str) -> str:
        normalized = normalize_plan(plan)
        price_field = _PLAN_PRICE_FIELDS.get(normalized)
        if price_field is None:
            raise StripeServiceError(f"plan {normalized.value!r} is not billable")
        field_name, env_var = price_field
        price_id = getattr(self.settings, field_name)

        if not price_id:
            raise StripeConfigurationError(f"{env_var} is required")
        return price_id

    def plan_from_price_id(self, price_id: str) -> PlanName:
        for plan, (field_name, _env_var) in _PLAN_PRICE_FIELDS.items():
            if price_id == getattr(self.settings, field_name):
                return plan
        raise StripeServiceError(f"unknown Stripe price id: {price_id}")

    async def ensure_customer(self, dealer: DealerOut) -> str:
        if dealer.stripe_customer_id:
            return dealer.stripe_customer_id

        customer = self.stripe.Customer.create(
            email=dealer.email,
            name=dealer.name,
            metadata={
                "dealer_id": str(dealer.id),
                "agartha_plan": str(dealer.plan),
            },
        )
        customer_id = _stripe_value(customer, "id")
        if not customer_id:
            raise StripeServiceError("Stripe customer creation returned no id")

        updated = await self.dealers.set_stripe_customer_id(dealer.id, customer_id)
        if updated is None:
            raise StripeServiceError(f"dealer {dealer.id} not found while storing Stripe customer")
        return customer_id

    async def create_checkout_session(
        self,
        *,
        dealer: DealerOut,
        target_plan: PlanName | str,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutSessionResult:
        plan = normalize_plan(target_plan)
        price_id = self.price_id_for_plan(plan)
        customer_id = await self.ensure_customer(dealer)
        metadata = {
            "dealer_id": str(dealer.id),
            "target_plan": plan.value,
        }

        session = self.stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(dealer.id),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url or self._public_url("/billing/success?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=cancel_url or self._public_url("/billing/cancel"),
            allow_promotion_codes=True,
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
        return CheckoutSessionResult(
            id=_required_stripe_value(session, "id"),
            url=_required_stripe_value(session, "url"),
            customer_id=customer_id,
            plan=plan,
        )

    async def create_billing_portal_session(
        self,
        *,
        dealer: DealerOut,
        return_url: str | None = None,
    ) -> BillingPortalSessionResult:
        customer_id = await self.ensure_customer(dealer)
        session = self.stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url or self._public_url("/billing"),
        )
        return BillingPortalSessionResult(
            id=_required_stripe_value(session, "id"),
            url=_required_stripe_value(session, "url"),
            customer_id=customer_id,
        )

    def construct_webhook_event(self, payload: bytes | str, signature: str | None) -> Any:
        if not self.settings.webhook_secret:
            raise StripeConfigurationError("STRIPE_WEBHOOK_SECRET is required")
        if not signature:
            raise StripeServiceError("Stripe signature header is required")
        return self.stripe.Webhook.construct_event(
            payload,
            signature,
            self.settings.webhook_secret,
        )

    def _public_url(self, path: str) -> str:
        if not self.settings.public_url:
            raise StripeConfigurationError("AGARTHA_PUBLIC_URL is required")
        return f"{self.settings.public_url.rstrip('/')}/{path.lstrip('/')}"


def _stripe_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _required_stripe_value(obj: Any, key: str) -> str:
    value = _stripe_value(obj, key)
    if not value:
        raise StripeServiceError(f"Stripe response missing {key!r}")
    return str(value)


def get_stripe_billing_service() -> StripeBillingService:
    return StripeBillingService()
