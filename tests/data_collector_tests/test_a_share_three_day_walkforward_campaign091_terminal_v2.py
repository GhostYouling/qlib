from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign091_features as campaign091


REPO_ROOT = campaign091.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign091_verified_v2.json"
)
STATUS_SHA256 = "099d743ea2c315a1198d1d8fedbc82346970a69a31845ff8e29a98e9c4a2b540"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v34_20260807.json"
)
POLICY_SHA256 = "b5c3099ed3821573a9fde46a1ec2d47ec42ebe2f260bd55d65d3502b428e948c"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v2_state_and_final_accounting_are_exact() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    assert bindings.validate_record(STATUS_PATH)["all_bindings_passed"] is True
    state = _load(STATUS_PATH)
    assert state["campaign091"]["development_survivor_count"] == 0
    assert state["campaign091"]["stress_2024_2025_opened"] is False
    assert state["accounting"] == {
        "cumulative_historical_research_attempt_count": 639,
        "cumulative_return_reading_development_trial_count": 289,
        "campaign091_attempt_count": 7,
        "campaign091_ledger_entry_count": 10,
        "campaign091_infrastructure_failure_count": 6,
        "campaign091_complete_factor_attempt_count": 1,
        "campaign091_return_reading_development_trial_count": 1,
    }


def test_v2_artifact_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    campaign = state["campaign091"]
    for key in (
        "research_record_v2",
        "terminal_completion_freeze_v2",
        "final_attempt_ledger",
    ):
        binding = campaign[key]
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / campaign["research_record_v2"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign091" in path.read_text(encoding="utf-8")


def test_v34_policy_preserves_v33_order_and_terminal_comparator() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": campaign091.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign091.reconstruct_complete_definitions() + [factor]
    numeric = campaign091.reconstruct_comparisons() + [factor]
    assert len(complete) == 123
    assert campaign091._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 121
    assert campaign091._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_v2_scientific_result_and_stress_semantics_are_unchanged() -> None:
    state = _load(STATUS_PATH)
    record = _load(REPO_ROOT / state["campaign091"]["research_record_v2"]["path"])
    result = record["terminal_result"]
    assert result["development_trial_count"] == 1
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    assert result["stress_return_fields_read"] is False
    assert result["development_aggregate_20bp_return"] == -0.2924050460372013
    v1 = _load(REPO_ROOT / record["supersedes_without_rewriting"]["path"])
    assert v1["development_result"]["development_survivor_count"] == 0
    assert v1["development_result"]["stress_return_fields_read"] is False


def test_candidate49_and_next_campaign_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v34_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
