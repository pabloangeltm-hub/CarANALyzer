import io
import json
import logging

import structlog

from tools.api.logging import configure_json_logging


def test_configure_json_logging_emits_structlog_json():
    stream = io.StringIO()
    configure_json_logging(level="INFO", stream=stream, force=True)

    structlog.get_logger("agartha.test").info(
        "sample_event",
        request_id="req-structlog",
        dealer_id=42,
    )

    body = json.loads(stream.getvalue())
    assert body["event"] == "sample_event"
    assert body["request_id"] == "req-structlog"
    assert body["dealer_id"] == 42
    assert body["logger"] == "agartha.test"
    assert body["level"] == "info"
    assert "logged_at" in body


def test_configure_json_logging_emits_stdlib_json_with_extra_fields():
    stream = io.StringIO()
    configure_json_logging(level="INFO", stream=stream, force=True)

    logging.getLogger("agartha.stdlib").warning(
        "stdlib_event",
        extra={"request_id": "req-stdlib"},
    )

    body = json.loads(stream.getvalue())
    assert body["event"] == "stdlib_event"
    assert body["request_id"] == "req-stdlib"
    assert body["logger"] == "agartha.stdlib"
    assert body["level"] == "warning"
    assert "logged_at" in body
