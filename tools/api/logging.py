"""Structured JSON logging configuration for the Agartha API."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

import structlog


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 5
_CONFIGURED = False


def configure_json_logging(
    *,
    level: str | int | None = None,
    stream: TextIO | None = None,
    file_path: str | Path | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    force: bool = False,
) -> None:
    """Configure stdlib logging and structlog to emit one JSON object per line."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    log_level = _log_level(level or os.getenv("AGARTHA_LOG_LEVEL", DEFAULT_LOG_LEVEL))
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="logged_at"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    formatter = _json_formatter(shared_processors)
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
        existing_handler.close()
    root_logger.addHandler(handler)
    resolved_file_path = file_path or os.getenv("AGARTHA_LOG_FILE_PATH", "").strip() or None
    if resolved_file_path:
        root_logger.addHandler(
            _rotating_json_handler(
                Path(resolved_file_path),
                shared_processors=shared_processors,
                max_bytes=max_bytes
                if max_bytes is not None
                else _env_int("AGARTHA_LOG_MAX_BYTES", DEFAULT_LOG_MAX_BYTES),
                backup_count=backup_count
                if backup_count is not None
                else _env_int("AGARTHA_LOG_BACKUP_COUNT", DEFAULT_LOG_BACKUP_COUNT),
            )
        )
    root_logger.setLevel(log_level)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.captureWarnings(True)
    _CONFIGURED = True


def _log_level(value: str | int) -> int:
    if isinstance(value, int):
        return value
    normalized = value.strip().upper()
    return getattr(logging, normalized, logging.INFO)


def _json_formatter(processors: list[object]) -> structlog.stdlib.ProcessorFormatter:
    return structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=processors,
    )


def _rotating_json_handler(
    path: Path,
    *,
    shared_processors: list[object],
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=max(0, max_bytes),
        backupCount=max(0, backup_count),
        encoding="utf-8",
    )
    handler.setFormatter(_json_formatter(shared_processors))
    return handler


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
