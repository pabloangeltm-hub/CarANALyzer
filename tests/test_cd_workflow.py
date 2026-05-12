from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "cd.yml"


def _workflow_text():
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_cd_workflow_deploys_only_after_ci_success_or_manual_dispatch():
    text = _workflow_text()

    assert "name: CD" in text
    assert "workflow_run:" in text
    assert "- CI" in text
    assert "branches:" in text
    assert "- main" in text
    assert "types:" in text
    assert "- completed" in text
    assert "workflow_dispatch:" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "environment: production" in text


def test_cd_workflow_uses_ssh_secrets_without_third_party_actions():
    text = _workflow_text()

    assert "secrets.VPS_HOST" in text
    assert "secrets.VPS_USER" in text
    assert "secrets.VPS_SSH_KEY" in text
    assert "ssh-keyscan" in text
    assert "agartha_deploy_key" in text
    assert "appleboy/" not in text
    assert "uses:" not in text


def test_cd_workflow_runs_deploy_steps_on_vps():
    text = _workflow_text()

    assert 'APP_DIR="/opt/agartha"' in text
    assert "git fetch origin main" in text
    assert "git reset --hard origin/main" in text
    assert "docker compose -f docker-compose.yml build" in text
    assert "docker compose -f docker-compose.yml run --rm api" in text
    assert "python tools/run_migrations.py --db-path /app/.tmp/agartha.db" in text
    assert "systemctl restart \"$SERVICE_NAME\"" in text
    assert "docker compose -f docker-compose.yml ps" in text


def test_cd_workflow_has_limited_permissions_and_serial_deploys():
    text = _workflow_text()

    assert "permissions:" in text
    assert "contents: read" in text
    assert "group: production-deploy" in text
    assert "cancel-in-progress: false" in text
