"""Authentication router."""

from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from tools.api.dependencies import get_current_active_dealer, get_dealer_from_bearer_token
from tools.api.dealer_store import create_dealer, get_dealer_row_by_email, row_to_dealer
from tools.api.schemas import APIKeyCreate, APIKeyOut, DealerCreate, DealerOut, LoginIn, RegisterOut, TokenOut
from tools.api.services.api_key_service import rotate_dealer_api_key
from tools.api.services.auth_service import (
    ACCESS_TOKEN_SECONDS,
    REFRESH_TOKEN_SECONDS,
    create_jwt,
    revoke_token,
    verify_password,
)
from tools.api.services.email_service import EmailConfigurationError, send_welcome_email
from tools.api.services.stripe_client import StripeConfigurationError
from tools.api.services.stripe_service import (
    StripeBillingService,
    StripeServiceError,
    get_stripe_billing_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_register_billing_service() -> StripeBillingService:
    try:
        return get_stripe_billing_service()
    except StripeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/register",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar dealer y abrir sesion",
    description=(
        "Crea una cuenta de dealer, provisiona su customer en Stripe, envia email de bienvenida "
        "si Resend esta configurado y devuelve tokens JWT junto con la API key inicial."
    ),
)
async def register(
    payload: DealerCreate,
    billing: Annotated[StripeBillingService, Depends(get_register_billing_service)],
) -> RegisterOut:
    try:
        dealer, api_key = await create_dealer(payload)
    except aiosqlite.IntegrityError as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Dealer email already exists") from exc
        raise

    try:
        stripe_customer_id = await billing.ensure_customer(dealer)
    except StripeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except StripeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dealer = dealer.model_copy(update={"stripe_customer_id": stripe_customer_id})

    try:
        await send_welcome_email(to=dealer.email, dealer_name=dealer.name)
    except EmailConfigurationError:
        pass

    subject = str(dealer.id)
    return RegisterOut(
        dealer=dealer,
        api_key=api_key,
        access_token=create_jwt(subject, expires_in=ACCESS_TOKEN_SECONDS, token_type="access"),
        refresh_token=create_jwt(subject, expires_in=REFRESH_TOKEN_SECONDS, token_type="refresh"),
        expires_in=ACCESS_TOKEN_SECONDS,
    )


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Login con email y contraseña",
    description=(
        "Autentica al dealer y retorna un access token (TTL 1 h) y un refresh token (TTL 7 días). "
        "Almacena ambos tokens en el cliente; usa el access token en `Authorization: Bearer <token>`. "
        "No requiere autenticación previa."
    ),
    response_description="Par de tokens JWT para el dealer autenticado.",
)
async def login(payload: LoginIn) -> TokenOut:
    row = await get_dealer_row_by_email(payload.email)
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    dealer = row_to_dealer(row)
    if not dealer.active:
        raise HTTPException(status_code=403, detail="Dealer account is inactive")
    subject = str(dealer.id)
    return TokenOut(
        access_token=create_jwt(subject, expires_in=ACCESS_TOKEN_SECONDS, token_type="access"),
        refresh_token=create_jwt(subject, expires_in=REFRESH_TOKEN_SECONDS, token_type="refresh"),
        expires_in=ACCESS_TOKEN_SECONDS,
    )


@router.post(
    "/refresh",
    response_model=TokenOut,
    summary="Renovar access token",
    description=(
        "Emite un nuevo par de tokens a partir de un refresh token válido. "
        "Enviar el refresh token en `Authorization: Bearer <refresh_token>`. "
        "Invalida el par anterior implícitamente al rotar."
    ),
)
async def refresh(authorization: str | None = Header(default=None, alias="Authorization")) -> TokenOut:
    dealer = await get_dealer_from_bearer_token(authorization, token_type="refresh")
    if dealer is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not dealer.active:
        raise HTTPException(status_code=403, detail="Dealer account is inactive")
    subject = str(dealer.id)
    return TokenOut(
        access_token=create_jwt(subject, expires_in=ACCESS_TOKEN_SECONDS, token_type="access"),
        refresh_token=create_jwt(subject, expires_in=REFRESH_TOKEN_SECONDS, token_type="refresh"),
        expires_in=ACCESS_TOKEN_SECONDS,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
    description=(
        "Endpoint semántico de logout. La invalidación real del token se realiza en el cliente "
        "descartando ambos tokens almacenados. El servidor no mantiene blacklist en esta versión."
    ),
)
async def logout(authorization: str | None = Header(default=None, alias="Authorization")) -> Response:
    token = (
        authorization.split(" ", 1)[1]
        if authorization and authorization.lower().startswith("bearer ")
        else None
    )
    if token:
        await revoke_token(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api-key",
    response_model=APIKeyOut,
    summary="Rotar API key",
    description=(
        "Genera y almacena una nueva API key para el dealer autenticado, invalidando la anterior. "
        "El campo `api_key` solo se devuelve en esta respuesta; guárdalo inmediatamente. "
        "Requiere access token válido en `Authorization: Bearer <token>`."
    ),
)
async def create_api_key(
    payload: APIKeyCreate,
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
) -> APIKeyOut:
    rotated = await rotate_dealer_api_key(dealer.id)
    if rotated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    updated_dealer, key_material = rotated
    return APIKeyOut(
        id=updated_dealer.id,
        name=payload.name,
        prefix=updated_dealer.api_key_prefix or key_material.prefix,
        api_key=key_material.api_key,
        created_at=updated_dealer.created_at,
        expires_at=payload.expires_at,
        active=updated_dealer.active,
    )
