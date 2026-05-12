"""Request audit logging middleware for the B2B API."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tools.api.security import verify_token

LOGGER = structlog.get_logger("agartha.api.audit")
DEFAULT_AUDIT_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_AUDIT_LOG_BACKUP_COUNT = 5


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, log_path: str | None = None, enabled: bool | None = None) -> None:
        super().__init__(app)
        self.enabled = enabled if enabled is not None else _env_bool("AGARTHA_AUDIT_LOG_ENABLED", True)
        self.log_path = Path(log_path or os.getenv("AGARTHA_AUDIT_LOG_PATH", ".tmp/api_audit.jsonl"))
        self._file_handler = _audit_file_handler(
            self.log_path,
            max_bytes=_env_int("AGARTHA_AUDIT_LOG_MAX_BYTES", DEFAULT_AUDIT_LOG_MAX_BYTES),
            backup_count=_env_int("AGARTHA_AUDIT_LOG_BACKUP_COUNT", DEFAULT_AUDIT_LOG_BACKUP_COUNT),
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            self._write_event(request, request_id, status_code, started, error=True)
            raise

        response.headers["X-Request-ID"] = request_id
        self._write_event(request, request_id, status_code, started)
        return response

    def _write_event(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        started: float,
        *,
        error: bool = False,
    ) -> None:
        if not self.enabled:
            return
        event = self._event(request, request_id, status_code, started, error=error)
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        try:
            _emit_jsonl(self._file_handler, payload)
        except OSError:
            LOGGER.exception("failed_to_write_api_audit_event", log_path=str(self.log_path))
        LOGGER.info("api_request", **event)

    @staticmethod
    def _event(
        request: Request,
        request_id: str,
        status_code: int,
        started: float,
        *,
        error: bool,
    ) -> dict[str, Any]:
        dealer_id = _dealer_id(request)
        route = request.scope.get("route")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "request_id": request_id,
            "dealer_id": dealer_id,
            "method": request.method,
            "path": request.url.path,
            "endpoint": getattr(route, "path", request.url.path),
            "status_code": status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "client_ip": _client_ip(request),
            "api_key_prefix": _api_key_prefix(request),
            "user_agent": request.headers.get("User-Agent"),
            "error": error,
        }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _audit_file_handler(path: Path, *, max_bytes: int, backup_count: int) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=max(0, max_bytes),
        backupCount=max(0, backup_count),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler


def _emit_jsonl(handler: RotatingFileHandler, payload: str) -> None:
    record = logging.LogRecord(
        name="agartha.api.audit.file",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=payload,
        args=(),
        exc_info=None,
    )
    handler.emit(record)


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _api_key_prefix(request: Request) -> str | None:
    api_key = request.headers.get("X-API-Key")
    return api_key[:10] if api_key else None


def _dealer_id(request: Request) -> int | None:
    header_dealer_id = request.headers.get("X-Dealer-ID")
    if header_dealer_id:
        try:
            return int(header_dealer_id)
        except ValueError:
            return None

    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    payload = verify_token(token, token_type="access")
    if not payload:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
