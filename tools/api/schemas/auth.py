"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from tools.api.schemas.dealers import DealerOut


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    expires_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned


class APIKeyOut(BaseModel):
    id: int | None = None
    name: str
    prefix: str
    api_key: str | None = Field(
        default=None,
        description="Only returned once when the key is created.",
    )
    created_at: datetime | str | None = None
    expires_at: datetime | str | None = None
    last_used_at: datetime | str | None = None
    active: bool = True


class RegisterOut(TokenOut):
    dealer: DealerOut
    api_key: str = Field(description="Initial API key returned once at registration.")
