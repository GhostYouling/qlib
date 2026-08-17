from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign094_features_v4 as definitions

REPO_ROOT = definitions.REPO_ROOT
STATUS_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260807_campaign094_terminal.json"
)
STATUS_SHA256 = "643d8228fc0c62c713a9817b6d59ac229002296e64a63ec9cae738550ed4295e"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v38_20260807.json"
)
POLICY_SHA256 = "38994cc61f350f40a9a85d75a30a6e36831d968416799284413247e8d2cd4b42"


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
    result = state["campaign094_result"]
    assert result["coverage_gate_passed"] is True
    assert result["numeric_comparisons_passed"] == 123
    assert result["numeric_comparisons_failed"] == 0
    assert result["development_trial_count"] == 1
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    accounting = state["final_accounting"]
    assert accounting["campaign094_attempt_count"] == 5
    assert accounting["campaign094_ledger_entry_count"] == 8
    assert accounting["cumulative_historical_research_attempt_count"] == 655
    assert accounting["cumulative_return_reading_development_trial_count"] == 291


def test_terminal_chain_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign094_chain"]
    for binding in chain.values():
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / chain["research_record"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign094" in path.read_text(encoding="utf-8")


def test_v38_policy_appends_terminal_definition_and_comparator_order() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": definitions.FACTOR_NAME, "score_direction": "higher"}
    complete = definitions.reconstruct_complete_definitions() + [factor]
    numeric = definitions.reconstruct_comparisons() + [factor]
    assert len(complete) == 126
    assert definitions._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 124
    assert definitions._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_development_rejection_and_stress_closure_are_exact() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign094_chain"]
    ledger = _load(REPO_ROOT / chain["trial_ledger"]["path"])
    survivors = _load(REPO_ROOT / chain["development_survivors"]["path"])
    stress = _load(REPO_ROOT / chain["exposed_stress_consumption"]["path"])
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["trial_id"] == (
        "wf094_intraday_range_local_peak_clock_dispersion_236p_single_higher"
    )
    folds = entry["training_and_validation_folds"]
    assert len(folds) == 3
    assert [
        fold["validation_metrics"]["association"]["mean_rank_ic"] for fold in folds
    ] == [
        -0.006129125392041096,
        -0.0024847600614538944,
        0.0018208545146860132,
    ]
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["development_aggregate_20bp_return"] == -0.16037181216484475
    assert survivors["selected_survivor_count"] == 0
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
    assert state["next_campaign_boundary"]["must_bind_v38_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
