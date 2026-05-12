import io
import json
import logging

import structlog
from fastapi.testclient import TestClient

from tools.api.app import create_app
from tools.api.logging import configure_json_logging
from tools.api.security import create_token


def _flush_root_handlers():
    for handler in logging.getLogger().handlers:
        handler.flush()


def _json_lines(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_structured_file_logs_rotate_as_json(tmp_path):
    stream = io.StringIO()
    log_path = tmp_path / "api.log"
    configure_json_logging(
        level="INFO",
        stream=stream,
        file_path=log_path,
        max_bytes=350,
        backup_count=2,
        force=True,
    )

    logger = structlog.get_logger("agartha.rotation")
    for index in range(12):
        logger.info("rotation_event", index=index, payload="x" * 80)
    _flush_root_handlers()

    rotated_path = tmp_path / "api.log.1"
    assert log_path.exists()
    assert rotated_path.exists()
    assert _json_lines(log_path)
    assert _json_lines(rotated_path)
    assert all("logged_at" in entry for entry in _json_lines(log_path))


def test_audit_jsonl_rotates_when_size_limit_is_reached(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_PATH", str(log_path))
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_MAX_BYTES", "450")
    monkeypatch.setenv("AGARTHA_AUDIT_LOG_BACKUP_COUNT", "2")
    monkeypatch.setenv("AGARTHA_RATE_LIMIT_REQUESTS", "1000")

    client = TestClient(create_app())
    token = create_token("7", expires_in=3600, token_type="access")
    for index in range(8):
        response = client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Request-ID": f"req-rotation-{index}",
                "User-Agent": "pytest-log-rotation",
            },
        )
        assert response.status_code == 204

    rotated_path = tmp_path / "audit.log.1"
    assert log_path.exists()
    assert rotated_path.exists()
    assert _json_lines(log_path)
    assert _json_lines(rotated_path)
    assert all("request_id" in entry for entry in _json_lines(log_path))
