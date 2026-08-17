from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign091_features as campaign091


REPO_ROOT = campaign091.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign091_terminal.json"
)
STATUS_SHA256 = "4f1c6d28117cd1eab4f33f903ee3ffd215264eaa9231987afaa292aabd654c97"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v33_20260807.json"
)
POLICY_SHA256 = "5412505e8c3478376efa844de58da66fb093a29685731a783a6e7f488ea05034"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_state_and_attempt_accounting_are_exact() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    state = _load(STATUS_PATH)
    campaign = state["campaign091"]
    assert campaign["terminal_status"] == (
        "development_quality_gate_rejection_zero_survivors"
    )
    assert campaign["development_survivor_count"] == 0
    assert campaign["stress_2024_2025_opened"] is False
    assert state["accounting"] == {
        "cumulative_historical_research_attempt_count": 636,
        "cumulative_return_reading_development_trial_count": 289,
        "campaign091_attempt_count": 4,
        "campaign091_ledger_entry_count": 7,
        "campaign091_complete_factor_attempt_count": 1,
        "campaign091_return_reading_development_trial_count": 1,
    }


def test_terminal_artifact_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    campaign = state["campaign091"]
    for key in (
        "research_record",
        "terminal_completion_freeze",
        "final_attempt_ledger",
    ):
        binding = campaign[key]
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / campaign["research_record"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign091" in path.read_text(encoding="utf-8")


def test_v33_policy_preserves_order_and_appends_campaign091_once() -> None:
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


def test_trial_rejection_and_stress_consumption_semantics_are_exact() -> None:
    state = _load(STATUS_PATH)
    record = _load(REPO_ROOT / state["campaign091"]["research_record"]["path"])
    result = record["development_result"]
    assert result["trial_count"] == 1
    assert result["operationally_admissible"] is True
    assert result["validation_quality_gate_passed"] is False
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    stress_binding = record["walkforward_artifacts"][
        "exposed_stress_consumption_record"
    ]
    stress = _load(REPO_ROOT / stress_binding["path"])
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_candidate49_and_next_campaign_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v33_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
