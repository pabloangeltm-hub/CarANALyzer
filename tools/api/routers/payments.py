"""Payments router for Stripe billing flows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from tools.api.dependencies import get_current_active_dealer
from tools.api.schemas import (
    BillingPortalSessionCreate,
    BillingPortalSessionOut,
    CheckoutSessionCreate,
    CheckoutSessionOut,
    DealerOut,
)
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import (
    StripeBillingService,
    StripeServiceError,
    get_stripe_billing_service,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def get_billing_service() -> StripeBillingService:
    return get_stripe_billing_service()


@router.post(
    "/checkout",
    response_model=CheckoutSessionOut,
    summary="Crear checkout de Stripe",
    description=(
        "Crea una Stripe Checkout Session en modo suscripcion para subir el dealer autenticado "
        "a un plan de pago (`starter`, `pro` o `elite`). Requiere Bearer token, `X-API-Key` o "
        "`X-Dealer-ID` valido."
    ),
)
async def create_checkout_session(
    payload: CheckoutSessionCreate,
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
    billing: Annotated[StripeBillingService, Depends(get_billing_service)],
) -> CheckoutSessionOut:
    try:
        session = await billing.create_checkout_session(
            dealer=dealer,
            target_plan=payload.plan,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except StripeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except StripeServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CheckoutSessionOut(
        id=session.id,
        url=session.url,
        customer_id=session.customer_id,
        plan=session.plan,
    )


@router.post(
    "/portal",
    response_model=BillingPortalSessionOut,
    summary="Crear portal de facturacion Stripe",
    description=(
        "Crea una Stripe Billing Portal Session para que el dealer autenticado gestione "
        "metodo de pago, facturas y suscripcion. Requiere una cuenta activa."
    ),
)
async def create_billing_portal_session(
    payload: BillingPortalSessionCreate,
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
    billing: Annotated[StripeBillingService, Depends(get_billing_service)],
) -> BillingPortalSessionOut:
    try:
        session = await billing.create_billing_portal_session(
            dealer=dealer,
            return_url=payload.return_url,
        )
    except StripeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except StripeServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return BillingPortalSessionOut(
        id=session.id,
        url=session.url,
        customer_id=session.customer_id,
    )
