import hashlib
import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNER_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py"
)
STATE_V1 = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign265_source_acceptance_plan_ready.json"
)
FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_post_plan_mutable_report_hash_test_failure_20260824.json"
)
DESELECT_FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_post_plan_pytest_deselect_prefix_failure_20260824.json"
)
LEDGER_V6 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v6.json"
)
UNIFIED_REPORTS = (
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_planner():
    spec = importlib.util.spec_from_file_location(
        "campaign265_source_acceptance_current_planner", PLANNER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ready_state_v1_is_immutable_plan_only_evidence() -> None:
    assert (
        _sha256(STATE_V1)
        == "4b6e942d22cebadebd714b8b7eed0fb7be529ac5f482a158c74be1f2b6a23c0a"
    )
    state = _load(STATE_V1)
    stage = state["campaign265_source_acceptance_plan_stage"]
    assert stage["plan_ready"] is True
    assert stage["plan_actual_exit_code"] == 0
    assert stage["credential_load_authorized"] is False
    assert stage["provider_request_authorized"] is False


def test_mutable_reports_have_exactly_one_source_plan_section() -> None:
    heading = "## Campaign265：零网络来源验收计划就绪（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "合计 1,700 次" in text
        assert "不授权执行" in text
        assert "累计历史尝试 2,617" in text


def test_historical_report_hash_failure_is_preserved_and_narrow() -> None:
    assert (
        _sha256(FAILURE)
        == "def9ae5138f3548ad7a386d734d2ba3c6e6bf793e29e96de366d469cd611e1c9"
    )
    failure = _load(FAILURE)
    assert failure["result"]["passed"] == 41
    assert failure["result"]["failed"] == 1
    assert (
        failure["correction_boundary"][
            "immutable_historical_test_must_not_be_rewritten"
        ]
        is True
    )
    assert failure["research_boundary"]["candidate_or_comparator_value_read"] is False


def test_deselect_prefix_failure_is_preserved_and_has_exact_current_node() -> None:
    assert (
        _sha256(DESELECT_FAILURE)
        == "5e00cb8e5fbb4ed2d58d2ce5633bb9fcd3fe7fe0bd0db7acaf2977582d555710"
    )
    failure = _load(DESELECT_FAILURE)
    assert failure["result"]["passed"] == 46
    assert failure["result"]["failed"] == 1
    assert failure["result"]["actual_collected_node"].startswith(
        "data_collector_tests/"
    )
    assert (
        failure["correction_boundary"]["old_test_or_mutable_report_rewrite_allowed"]
        is False
    )


def test_attempt_ledger_v6_adds_only_the_second_validation_failure() -> None:
    assert (
        _sha256(LEDGER_V6)
        == "fd015de31865b048f8f199759b4330dbfd3732167f174c6ab79576b865889c36"
    )
    ledger = _load(LEDGER_V6)
    assert ledger["effective_entry_count"] == 15
    assert ledger["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger["effective_prevalue_scientific_attempt_count"] == 8
    assert ledger["cumulative_historical_research_attempt_count"] == 2619
    assert ledger["return_reading_development_trial_count"] == 0
    entry = ledger["appended_entries"]
    assert len(entry) == 1
    assert entry[0]["scientific_attempt"] is False
    assert entry[0]["candidate_or_comparator_value_read"] is False


def test_plan_remains_ready_without_source_artifacts_or_provider_access() -> None:
    planner = _load_planner()
    plan = planner.build_plan()
    assert plan["ready"] is True
    assert plan["blockers"] == []
    assert plan["provider_request_issued"] is False
    assert plan["filesystem_write_performed"] is False
