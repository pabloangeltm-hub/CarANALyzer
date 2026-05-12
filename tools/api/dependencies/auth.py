"""Authentication dependencies shared by API routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from tools.api.dealer_store import (
    get_dealer_by_id,
)
from tools.api.schemas import DealerOut
from tools.api.services.api_key_service import get_dealer_by_api_key
from tools.api.security import verify_token as verify_legacy_token
from tools.api.services.auth_service import verify_jwt


def bearer_token_from_authorization(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


async def get_dealer_from_bearer_token(
    authorization: str | None,
    *,
    token_type: str = "access",
) -> DealerOut | None:
    token = bearer_token_from_authorization(authorization)
    if not token:
        return None
    payload = await verify_jwt(token, token_type=token_type)  # type: ignore[arg-type]
    if payload is None:
        payload = verify_legacy_token(token, token_type=token_type)
    if not payload:
        return None
    try:
        dealer_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    return await get_dealer_by_id(dealer_id)


async def get_optional_current_dealer(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_dealer_id: Annotated[int | None, Header(alias="X-Dealer-ID")] = None,
) -> DealerOut | None:
    dealer = await get_dealer_from_bearer_token(authorization, token_type="access")
    if dealer is not None:
        return dealer

    if x_api_key:
        return await get_dealer_by_api_key(x_api_key)

    if x_dealer_id is not None:
        return await get_dealer_by_id(x_dealer_id)

    return None


async def get_current_dealer(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_dealer_id: Annotated[int | None, Header(alias="X-Dealer-ID")] = None,
) -> DealerOut:
    dealer = await get_optional_current_dealer(authorization, x_api_key, x_dealer_id)
    if dealer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dealer credentials required",
        )
    return dealer


async def get_current_active_dealer(
    dealer: Annotated[DealerOut, Depends(get_current_dealer)],
) -> DealerOut:
    if not dealer.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dealer account is inactive",
        )
    return dealer


async def get_current_admin_dealer(
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
) -> DealerOut:
    if dealer.plan != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin plan required",
        )
    return dealer
