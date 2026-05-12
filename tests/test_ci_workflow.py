from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _workflow_text():
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ci_workflow_uses_current_github_actions_and_read_only_permissions():
    text = _workflow_text()

    assert "name: CI" in text
    assert "permissions:" in text
    assert "contents: read" in text
    assert "uses: actions/checkout@v6" in text
    assert "uses: actions/setup-python@v6" in text
    assert "uses: actions/setup-node@v6" in text
    assert "cancel-in-progress: true" in text


def test_ci_workflow_runs_python_test_suite():
    text = _workflow_text()

    assert "python-version: \"3.12\"" in text
    assert "cache: pip" in text
    assert "cache-dependency-path: requirements.txt" in text
    assert "pip install -r requirements.txt" in text
    assert "python -m pytest -q" in text


def test_ci_workflow_runs_frontend_checks_and_e2e():
    text = _workflow_text()

    assert "working-directory: frontend" in text
    assert "node-version: \"22\"" in text
    assert "cache-dependency-path: frontend/package-lock.json" in text
    assert "npm ci" in text
    assert "npm run lint" in text
    assert "npm run build" in text
    assert "npx playwright install --with-deps chromium" in text
    assert "npm run test:e2e" in text


def test_ci_workflow_validates_compose_without_expanding_env_values():
    text = _workflow_text()

    assert "docker compose -f docker-compose.yml config --no-interpolate" in text
    assert "secrets." not in text
