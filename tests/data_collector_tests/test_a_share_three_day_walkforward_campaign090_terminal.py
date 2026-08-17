from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign090_features as campaign090


REPO_ROOT = campaign090.REPO_ROOT
STATUS_PATH = (
    REPO_ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign090_verified.json"
)
STATUS_SHA256 = "11c776a1addfbd0cbac72199b6df5c70d25cbb4c307d89f565dffcba3de41da5"
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v31_20260807.json"
)
POLICY_SHA256 = "735ae9af7fdbb0f1abe925bed4aeec291189e6f35aaf534c2af3b49b186e4a21"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_state_and_attempt_accounting_are_bound() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    state = _load(STATUS_PATH)
    campaign = state["campaign090"]
    assert campaign["terminal_status"] == (
        "development_quality_gate_rejection_zero_survivors"
    )
    assert campaign["numeric_comparisons_passed"] == 119
    assert campaign["development_survivor_count"] == 0
    assert campaign["stress_2024_2025_opened"] is False
    assert campaign["stress_return_fields_read"] is False
    assert state["accounting"] == {
        "cumulative_historical_research_attempt_count": 629,
        "cumulative_return_reading_development_trial_count": 288,
        "campaign090_attempt_count": 7,
        "campaign090_ledger_entry_count": 9,
        "campaign090_complete_factor_attempt_count": 1,
        "campaign090_return_reading_development_trial_count": 1,
    }


def test_final_artifact_and_reporting_bindings_are_exact() -> None:
    state = _load(STATUS_PATH)
    campaign = state["campaign090"]
    for key in ("research_record", "terminal_completion_freeze", "final_attempt_ledger"):
        binding = campaign[key]
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True

    record = _load(REPO_ROOT / campaign["research_record"]["path"])
    for binding in record["reporting_bindings"].values():
        if not isinstance(binding, dict):
            continue
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert "Campaign090" in path.read_text(encoding="utf-8")


def test_future_numeric_policy_v31_appends_campaign090_exactly_once() -> None:
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


def test_candidate49_and_stress_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    for name in ("signal", "execution"):
        path = (
            REPO_ROOT
            / f"data/experiments/short_horizon/candidate49_future_{name}_ledger.json"
        )
        ledger = _load(path)
        assert ledger["entries"] == []
        assert ledger["historical_backfill_allowed"] is False
        assert ledger["provider_request_issued"] is False
    assert state["next_campaign_boundary"]["must_bind_v31_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
