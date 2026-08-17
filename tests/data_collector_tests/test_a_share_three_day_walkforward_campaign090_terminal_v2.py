from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign090_features as campaign090


REPO_ROOT = campaign090.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign090_verified_v2.json"
)
STATUS_SHA256 = "46e1856a031b5e8ae1c805eb0e52076e3d16de60ac07d6f073730b21579a9a69"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v32_20260807.json"
)
POLICY_SHA256 = "cb5db190487c4af6060e5b6b9fd5d4c109f1fc439d815b87cf8d0c43448b5b97"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v2_state_and_final_attempt_accounting_are_exact() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    state = _load(STATUS_PATH)
    campaign = state["campaign090"]
    assert campaign["terminal_status"] == (
        "development_quality_gate_rejection_zero_survivors"
    )
    assert campaign["development_survivor_count"] == 0
    assert campaign["stress_2024_2025_opened"] is False
    assert state["accounting"] == {
        "cumulative_historical_research_attempt_count": 632,
        "cumulative_return_reading_development_trial_count": 288,
        "campaign090_attempt_count": 10,
        "campaign090_ledger_entry_count": 12,
        "campaign090_complete_factor_attempt_count": 1,
        "campaign090_return_reading_development_trial_count": 1,
    }


def test_v2_artifact_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    campaign = state["campaign090"]
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
            assert "Campaign090" in path.read_text(encoding="utf-8")


def test_v32_policy_preserves_order_and_appends_campaign090_once() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": campaign090.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign090.reconstruct_complete_definitions() + [factor]
    numeric = campaign090.reconstruct_comparisons() + [factor]
    assert len(complete) == 122
    assert campaign090._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 120
    assert campaign090._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_candidate49_and_stress_boundaries_remain_closed_in_v2() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v32_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
