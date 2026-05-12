"""FastAPI dependency providers."""

from tools.api.dependencies.auth import (
    bearer_token_from_authorization,
    get_current_active_dealer,
    get_current_admin_dealer,
    get_current_dealer,
    get_dealer_from_bearer_token,
    get_optional_current_dealer,
)
from tools.api.dependencies.db import get_db

__all__ = [
    "bearer_token_from_authorization",
    "get_current_active_dealer",
    "get_current_admin_dealer",
    "get_current_dealer",
    "get_db",
    "get_dealer_from_bearer_token",
    "get_optional_current_dealer",
]
