import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "setup_vps.sh"


def _script_text():
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_setup_vps_script_is_strict_and_root_guarded():
    text = _script_text()

    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -Eeuo pipefail" in text
    assert 'if [[ "${EUID}" -ne 0 ]]' in text
    assert "sudo ./setup_vps.sh" in text


def test_setup_vps_script_installs_official_docker_repo_and_compose_plugin():
    text = _script_text()

    assert "https://download.docker.com/linux/${OS_ID}/gpg" in text
    assert "/etc/apt/keyrings/docker.asc" in text
    assert "docker-ce" in text
    assert "docker-ce-cli" in text
    assert "containerd.io" in text
    assert "docker-buildx-plugin" in text
    assert "docker-compose-plugin" in text


def test_setup_vps_script_installs_systemd_unit_and_waits_for_env():
    text = _script_text()

    assert "deploy/systemd/agartha.service" in text
    assert "/etc/systemd/system/${SERVICE_NAME}.service" in text
    assert "systemctl daemon-reload" in text
    assert '[[ ! -f "${APP_DIR}/.env" ]]' in text
    assert "systemctl start ${SERVICE_NAME}.service" in text
    assert "systemctl restart" in text


def test_setup_vps_script_configures_web_firewall_rules():
    text = _script_text()

    assert "ufw allow OpenSSH" in text
    assert "ufw allow 80/tcp" in text
    assert "ufw allow 443/tcp" in text
    assert "AGARTHA_CONFIGURE_UFW" in text


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_setup_vps_script_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "execvpe(/bin/bash) failed" in result.stderr:
        pytest.skip("bash shim exists, but WSL has no /bin/bash")
    assert result.returncode == 0, result.stderr
