from pathlib import Path


SERVICE_PATH = Path(__file__).resolve().parents[1] / "deploy" / "systemd" / "agartha.service"


def _service_text():
    return SERVICE_PATH.read_text(encoding="utf-8")


def test_systemd_service_unit_runs_docker_compose_stack():
    text = _service_text()

    assert "[Unit]" in text
    assert "Requires=docker.service" in text
    assert "After=docker.service network-online.target" in text
    assert "[Service]" in text
    assert "Type=oneshot" in text
    assert "WorkingDirectory=/opt/agartha" in text
    assert "ExecStart=/usr/bin/docker compose up -d --remove-orphans" in text
    assert "ExecStop=/usr/bin/docker compose down" in text
    assert "RemainAfterExit=yes" in text
    assert "[Install]" in text
    assert "WantedBy=multi-user.target" in text


def test_systemd_service_unit_has_no_windows_line_endings():
    raw = SERVICE_PATH.read_bytes()

    assert b"\r\n" not in raw
