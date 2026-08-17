from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign092_features as campaign092


REPO_ROOT = campaign092.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign092_terminal.json"
)
STATUS_SHA256 = "a289bebf3dc148e912e461dd169207e50ff5b712dcbcde500a30633106d55906"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v36_20260807.json"
)
POLICY_SHA256 = "8e2d23139dbe5f423a5b96fb1230a2f5f0f3c04e3bced33753aa38ac5d7554f8"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_state_and_final_accounting_are_exact() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    assert bindings.validate_record(STATUS_PATH)["all_bindings_passed"] is True
    state = _load(STATUS_PATH)
    assert datetime.fromisoformat(state["recorded_at"].replace("Z", "+00:00")) <= (
        datetime.now(timezone.utc)
    )
    assert state["campaign092_result"]["development_survivor_count"] == 0
    assert state["campaign092_result"]["stress_2024_2025_opened"] is False
    assert state["final_accounting"]["campaign092_attempt_count"] == 6
    assert state["final_accounting"]["campaign092_ledger_entry_count"] == 9
    assert (
        state["final_accounting"]["cumulative_historical_research_attempt_count"] == 646
    )
    assert (
        state["final_accounting"]["cumulative_return_reading_development_trial_count"]
        == 290
    )


def test_terminal_chain_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign092_chain"]
    for binding in chain.values():
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / chain["research_record"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign092" in path.read_text(encoding="utf-8")


def test_v36_policy_preserves_terminal_definition_and_comparator_order() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": campaign092.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign092.reconstruct_complete_definitions() + [factor]
    numeric = campaign092.reconstruct_comparisons() + [factor]
    assert len(complete) == 124
    assert campaign092._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 122
    assert campaign092._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_development_rejection_and_stress_closure_are_bound() -> None:
    root = REPO_ROOT / (
        "data/experiments/short_horizon/historical_walkforward/"
        "campaign_092/walkforward"
    )
    survivors = _load(root / "development_survivors.json")
    decision = survivors["trial_decisions"][0]
    assert survivors["selected_survivor_count"] == 0
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["development_aggregate_20bp_return"] < 0
    stress = _load(root / "exposed_stress_consumption_record.json")
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_candidate49_and_next_campaign_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    signal = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = REPO_ROOT / (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == candidate49["signal_ledger_sha256"]
    assert _sha256(execution) == candidate49["execution_ledger_sha256"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v36_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
