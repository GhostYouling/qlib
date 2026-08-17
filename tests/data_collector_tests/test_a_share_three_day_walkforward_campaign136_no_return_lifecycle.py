from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign136_no_return_ready.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v163_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/research_attempt_ledger.json"
)
COVERAGE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/coverage/campaign136_coverage_audit.json"
)
UNIQUENESS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/uniqueness/campaign136_ordered_uniqueness_audit.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign136_ledger_chain_and_accounting_are_append_only() -> None:
    ledger = _json(LEDGER)
    previous = "0" * 64
    for entry in ledger["entries"]:
        payload = (
            f"campaign136|{entry['attempt_id']}|{previous}|"
            f"{entry['phase']}|{entry['status']}"
        )
        observed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == observed
        previous = observed
    assert len(ledger["entries"]) == ledger["entry_count"] == 11
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["infrastructure_failure_attempt_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 1131
    assert ledger["cumulative_return_reading_development_trial_count"] == 312


def test_coverage_and_all_140_uniqueness_gates_passed_without_returns() -> None:
    coverage = _json(COVERAGE)
    uniqueness = _json(UNIQUENESS)
    gate = coverage["coverage_and_variation"]
    assert gate["gate_passed_before_comparator_values"] is True
    assert gate["median_daily_coverage"] == gate["p05_daily_coverage"] == 1.0
    assert gate["eligible_names_p05"] == 138.0
    assert coverage["historical_daily_ohlcv_fields_read"] == []
    assert coverage["historical_forward_return_fields_read"] is False
    assert uniqueness["summary"]["all_required_numeric_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 140
    assert all(item["gate_passed"] is True for item in uniqueness["comparisons"])
    assert (
        uniqueness["summary"]["maximum_observed_absolute_median_daily_rank_correlation"]
        == 0.03709644736183112
    )
    assert uniqueness["historical_daily_ohlcv_fields_read"] == []
    assert uniqueness["historical_forward_return_fields_read"] is False
    assert uniqueness["stress_2024_2025_return_values_opened"] is False


def test_policy_keeps_campaign136_active_and_defers_numeric_append() -> None:
    policy = _json(POLICY)
    assert policy["status"] == (
        "campaign136_all_140_uniqueness_passed_one_2019_2023_development_freeze_allowed"
    )
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 152
    )
    numeric = policy["numerical_comparator_eligibility_while_campaign136_active"]
    assert numeric["eligible_numeric_comparator_count"] == 140
    assert numeric[
        "campaign136_numeric_series_append_deferred_until_terminal_classification"
    ]
    assert (
        policy["next_gate"]["campaign137_start_allowed_before_campaign136_terminal"]
        is False
    )
    assert policy["research_boundary"]["historical_forward_returns_read"] is False


def test_authoritative_state_goal_candidate49_and_hashes_are_consistent() -> None:
    state = _json(STATE)
    assert state["goal"] == {
        "objective": "请持续迭代因子。",
        "status": "active",
        "completion_or_blocked_requested": False,
    }
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign136"]["coverage"]["sha256"] == _sha(COVERAGE)
    assert state["campaign136"]["ordered_uniqueness"]["sha256"] == _sha(UNIQUENESS)
    assert state["campaign136"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["campaign136"]["historical_forward_returns_read"] is False
    candidate49 = state["candidate49"]
    assert candidate49["sole_prospective_candidate"] is True
    assert candidate49["signal_entries"] == candidate49["execution_entries"] == 0
    assert candidate49["ledgers_changed"] is False
    assert candidate49["signal_ledger_sha256"] == _sha(
        ROOT / candidate49["signal_ledger_path"]
    )
    assert candidate49["execution_ledger_sha256"] == _sha(
        ROOT / candidate49["execution_ledger_path"]
    )
