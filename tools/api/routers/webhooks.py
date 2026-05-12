"""Webhook entrypoints for external billing providers."""

from __future__ import annotations

from typing import Any

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from tools.api.models.plan import PlanName
from tools.api.services.dealer_service import DealerService, dealer_service
from tools.api.services.email_service import send_payment_failed_email
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import (
    StripeBillingService,
    StripeServiceError,
    get_stripe_billing_service,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_webhook_billing_service() -> StripeBillingService:
    return get_stripe_billing_service()


def get_webhook_dealer_service() -> DealerService:
    return dealer_service


@router.post(
    "/stripe",
    summary="Recibir webhook de Stripe",
    description=(
        "Endpoint publico para eventos Stripe. Valida la firma `Stripe-Signature` "
        "contra `STRIPE_WEBHOOK_SECRET` y confirma recepcion. Los handlers de eventos "
        "con efectos de negocio se anaden en F4-T16..F4-T18."
    ),
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    billing: StripeBillingService = Depends(get_webhook_billing_service),
    dealers: DealerService = Depends(get_webhook_dealer_service),
) -> dict[str, Any]:
    payload = await request.body()
    try:
        event = billing.construct_webhook_event(payload, stripe_signature)
    except StripeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (StripeServiceError, ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await _handle_checkout_completed(event, dealers)
    await _handle_invoice_payment_failed(event, dealers)
    await _handle_subscription_deleted(event, dealers)

    return {
        "received": True,
        "id": _event_value(event, "id"),
        "type": _event_value(event, "type"),
    }


def _event_value(event: Any, key: str) -> Any:
    if isinstance(event, dict):
        return event.get(key)
    return getattr(event, key, None)


async def _handle_checkout_completed(event: Any, dealers: DealerService) -> None:
    if _event_value(event, "type") != "checkout.session.completed":
        return

    session = _event_value(_event_value(event, "data") or {}, "object")
    metadata = _event_value(session or {}, "metadata") or {}
    dealer_id = _metadata_value(metadata, "dealer_id") or _event_value(session or {}, "client_reference_id")
    target_plan = _metadata_value(metadata, "target_plan")
    customer_id = _event_value(session or {}, "customer")

    if dealer_id is None:
        raise HTTPException(status_code=400, detail="checkout session missing dealer_id")
    if target_plan is None:
        raise HTTPException(status_code=400, detail="checkout session missing target_plan")

    try:
        dealer_id_int = int(dealer_id)
        plan = PlanName(str(target_plan))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid checkout session metadata") from exc

    if customer_id:
        updated = await dealers.set_stripe_customer_id(dealer_id_int, str(customer_id))
        if updated is None:
            raise HTTPException(status_code=404, detail="Dealer not found")

    updated = await dealers.set_plan(dealer_id_int, plan)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")


def _metadata_value(metadata: Any, key: str) -> Any:
    if isinstance(metadata, dict):
        return metadata.get(key)
    return getattr(metadata, key, None)


async def _handle_invoice_payment_failed(event: Any, dealers: DealerService) -> None:
    if _event_value(event, "type") != "invoice.payment_failed":
        return

    invoice = _event_value(_event_value(event, "data") or {}, "object")
    customer_id = _event_value(invoice or {}, "customer")
    if not customer_id:
        raise HTTPException(status_code=400, detail="invoice missing customer")

    dealer = await dealers.get_by_stripe_customer_id(str(customer_id))
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")

    await send_payment_failed_email(to=dealer.email, dealer_name=dealer.name)


async def _handle_subscription_deleted(event: Any, dealers: DealerService) -> None:
    if _event_value(event, "type") != "customer.subscription.deleted":
        return

    subscription = _event_value(_event_value(event, "data") or {}, "object")
    customer_id = _event_value(subscription or {}, "customer")
    if not customer_id:
        raise HTTPException(status_code=400, detail="subscription missing customer")

    dealer = await dealers.get_by_stripe_customer_id(str(customer_id))
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")

    updated = await dealers.set_plan(dealer.id, PlanName.FREE)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
