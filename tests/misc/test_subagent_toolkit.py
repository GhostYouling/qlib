import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "subagents" / "compose_prompt.py"
ROLES_FILE = REPO_ROOT / "scripts" / "subagents" / "roles.json"


def _load_compose_module():
    spec = importlib.util.spec_from_file_location("compose_prompt", COMPOSE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_subagent_roles_schema_valid():
    module = _load_compose_module()
    roles = module.load_roles(ROLES_FILE)
    errors = module.validate_roles(roles)
    assert errors == []


def test_subagent_list_contains_known_roles():
    module = _load_compose_module()
    roles = module.load_roles(ROLES_FILE)
    rendered = module.render_list(roles)
    assert "model-worker (worker)" in rendered
    assert "pipeline-explorer (explorer)" in rendered


def test_subagent_prompt_contains_required_sections():
    module = _load_compose_module()
    roles = module.load_roles(ROLES_FILE)
    prompt = module.compose_prompt(
        role_name="model-worker",
        role=roles["model-worker"],
        objective="Add robust trainer callback",
        contexts=["Keep recorder compatibility"],
        acceptance=["tests/model pass"],
        extra="",
    )
    assert "Owned write scope:" in prompt
    assert "Required validation commands:" in prompt
    assert "Add robust trainer callback" in prompt
    assert "tests/model pass" in prompt


def test_subagent_cli_validate_success():
    result = subprocess.run(
        [sys.executable, str(COMPOSE_SCRIPT), "--validate"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "roles.json is valid." in result.stdout

