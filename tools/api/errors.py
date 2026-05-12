"""RFC 7807 problem detail handlers for the API."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

LOGGER = structlog.get_logger("agartha.api.errors")
PROBLEM_JSON = "application/problem+json"


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else _status_title(exc.status_code)
    return problem_response(
        request,
        status_code=exc.status_code,
        title=_status_title(exc.status_code),
        detail=detail,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "loc": list(error.get("loc", ())),
            "msg": error.get("msg"),
            "type": error.get("type"),
        }
        for error in exc.errors()
    ]
    return problem_response(
        request,
        status_code=422,
        title="Unprocessable Entity",
        detail="Request validation failed.",
        extra={"errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception(
        "unhandled_api_exception",
        path=str(request.url.path),
        error_type=type(exc).__name__,
    )
    return problem_response(
        request,
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
    )


def problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
    }
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    if request_id:
        body["request_id"] = request_id
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"
