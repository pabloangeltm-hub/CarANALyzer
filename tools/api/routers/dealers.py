"""Dealer management router."""

from __future__ import annotations

import aiosqlite
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from tools.api.dependencies import get_current_active_dealer
from tools.api.dealer_store import (
    create_dealer,
    get_dealer_by_id,
    list_dealers,
    update_dealer,
)
from tools.api.schemas import DealerCreate, DealerOut, DealerUpdate

router = APIRouter(prefix="/dealers", tags=["dealers"])


@router.post(
    "",
    response_model=DealerOut,
    status_code=201,
    summary="Registrar concesionario",
    description=(
        "Crea una cuenta de dealer con plan `free` por defecto. "
        "El email debe ser único; retorna 409 si ya existe. "
        "La contraseña se almacena hasheada con PBKDF2-SHA256."
    ),
)
async def create_dealer_endpoint(payload: DealerCreate) -> DealerOut:
    try:
        dealer, _api_key = await create_dealer(payload)
        return dealer
    except aiosqlite.IntegrityError as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Dealer email already exists") from exc
        raise


@router.get(
    "",
    response_model=list[DealerOut],
    summary="Listar concesionarios",
    description="Retorna todos los dealers registrados. Paginado con `limit` y `offset`. Solo para uso admin.",
)
async def list_dealers_endpoint(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DealerOut]:
    return await list_dealers(limit=limit, offset=offset)


@router.get(
    "/me",
    response_model=DealerOut,
    summary="Perfil del dealer autenticado",
    description=(
        "Retorna el perfil del dealer identificado por Bearer token, `X-API-Key` o `X-Dealer-ID`. "
        "Útil para el frontend para mostrar el plan activo y el uso de API calls."
    ),
)
async def get_me(
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
) -> DealerOut:
    return dealer


@router.patch(
    "/me",
    response_model=DealerOut,
    summary="Actualizar perfil propio",
    description=(
        "Actualiza nombre, plan o estado activo del dealer autenticado. "
        "Solo se modifican los campos presentes en el body. "
        "Requiere Bearer token, `X-API-Key` o `X-Dealer-ID`."
    ),
)
async def update_me(
    payload: DealerUpdate,
    dealer: Annotated[DealerOut, Depends(get_current_active_dealer)],
) -> DealerOut:
    updated = await update_dealer(dealer.id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return updated


@router.get(
    "/{dealer_id}",
    response_model=DealerOut,
    summary="Perfil de dealer por ID",
    description="Retorna el perfil de un dealer específico por su `id`. Uso admin/interno.",
)
async def get_dealer(dealer_id: int) -> DealerOut:
    dealer = await get_dealer_by_id(dealer_id)
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return dealer
