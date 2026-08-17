from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign093_features as campaign093

REPO_ROOT = campaign093.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign093_terminal.json"
)
STATUS_SHA256 = "ffaa325909cd1d54e8a95d9ab7c7a30949e7a6672236ae20d8845ac73c66fe59"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v37_20260807.json"
)
POLICY_SHA256 = "0e0527d3f4fb5616f3eb7b24554eaa5fa71d354d89131193420cd1634de90fe0"


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
    result = state["campaign093_result"]
    assert result["coverage_gate_passed"] is True
    assert result["numeric_comparisons_passed"] == 121
    assert result["numeric_comparisons_failed"] == 1
    assert result["development_trial_count"] == 0
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    accounting = state["final_accounting"]
    assert accounting["campaign093_attempt_count"] == 4
    assert accounting["campaign093_ledger_entry_count"] == 6
    assert accounting["cumulative_historical_research_attempt_count"] == 650
    assert accounting["cumulative_return_reading_development_trial_count"] == 290


def test_terminal_chain_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign093_chain"]
    for binding in chain.values():
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / chain["research_record"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign093" in path.read_text(encoding="utf-8")


def test_v37_policy_appends_terminal_definition_and_comparator_order() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": campaign093.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign093.reconstruct_complete_definitions() + [factor]
    numeric = campaign093.reconstruct_comparisons() + [factor]
    assert len(complete) == 125
    assert campaign093._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 123
    assert campaign093._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_uniqueness_rejection_stopped_before_prices_or_returns() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign093_chain"]
    freeze = _load(REPO_ROOT / chain["terminal_completion_freeze"]["path"])
    audit_binding = freeze["no_return_audit"]
    audit = _load(REPO_ROOT / audit_binding["path"])
    factor = campaign093.FACTOR_NAME
    uniqueness = audit["uniqueness"][factor]
    failed = [
        item for item in uniqueness["comparisons"] if item["gate_passed"] is not True
    ]
    assert audit["admissible_factor_count"] == 0
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == (
        "intraday_intrabar_body_range_efficiency_240m"
    )
    assert failed[0]["absolute_median_daily_rank_correlation"] > 0.8
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


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
    assert state["next_campaign_boundary"]["must_bind_v37_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
