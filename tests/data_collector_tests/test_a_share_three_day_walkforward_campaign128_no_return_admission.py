from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
STATUS = (
    DOCS
    / "a_share_three_day_iteration_status_20260814_campaign128_no_return_pass_v2.json"
)
POLICY = (
    DOCS
    / "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v141_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_128/research_attempt_ledger_v8.json"
)
COVERAGE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_128/coverage/campaign128_coverage_audit.json"
)
UNIQUENESS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_128/uniqueness/campaign128_ordered_uniqueness_audit.json"
)
ADMISSION = (
    DOCS
    / "a_share_three_day_walkforward_campaign_128_no_return_development_admission_20260814.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_snapshot_coverage_and_uniqueness_authorities_are_exact() -> None:
    coverage = load(COVERAGE)
    uniqueness = load(UNIQUENESS)
    assert sha(COVERAGE) == (
        "8ccfbc0fb76b5c4187febbf8659fb29c864259efd4e3a8be3bc5d0db8a980605"
    )
    assert sha(UNIQUENESS) == (
        "7661112a503f8930cba5fd79c03815b8c830d39f98703746362b85b37fa14cef"
    )
    assert (
        coverage["coverage_and_variation"]["gate_passed_before_comparator_values"]
        is True
    )
    summary = uniqueness["comparison_summary"]
    assert summary["comparison_factor_count"] == 139
    assert summary["comparison_order_matches_preregistration"] is True
    assert summary["all_required_numeric_comparisons_passed"] is True
    assert summary["maximum_observed_absolute_median_daily_rank_correlation"] < 0.8


def test_all_139_results_are_recorded_and_strictly_passed() -> None:
    result = load(UNIQUENESS)
    comparisons = result["comparisons"]
    assert len(comparisons) == 139
    assert all(item["gate_passed"] is True for item in comparisons)
    assert all(
        item["absolute_median_daily_rank_correlation"] < 0.8 for item in comparisons
    )
    assert result["admissible_factor_names"] == [
        "intraday_transaction_price_dispersion_resolution_2h"
    ]


def test_admission_is_interface_only_and_returns_remain_closed() -> None:
    admission = load(ADMISSION)
    assert admission["authoritative_no_return_audit"]["sha256"] == sha(UNIQUENESS)
    assert admission["interface_only_no_recomputation"] is True
    assert admission["admissible_factor_count"] == 1
    assert admission["all_139_numeric_comparisons_passed"] is True
    assert admission["historical_daily_price_fields_read"] == []
    assert admission["historical_forward_return_fields_read"] is False


def test_latest_ledger_delta_chain_and_accounting() -> None:
    ledger = load(LEDGER)
    assert ledger["inherits_without_rewriting"]["inherited_entry_count"] == 12
    previous = ledger["inherits_without_rewriting"]["inherited_chain_tip_sha256"]
    for entry in ledger["appended_entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign128|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        )
        assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 13
    assert ledger["cumulative_historical_research_attempt_count"] == 1046
    assert ledger["cumulative_return_reading_development_trial_count"] == 306


def test_v139_allows_only_one_frozen_development_trial_next() -> None:
    policy = load(POLICY)
    gate = policy["frozen_scientific_state_unchanged"]
    assert gate["coverage_gate_passed"] is True
    assert gate["all_139_numeric_uniqueness_gates_passed"] is True
    assert gate["exact_one_2019_2023_development_preregistration_allowed"] is True
    assert gate["historical_daily_price_or_forward_return_values_opened"] is False
    assert gate["stress_2024_2025_return_values_allowed"] is False


def test_active_status_preserves_candidate49_and_no_return_boundary() -> None:
    status = load(STATUS)
    assert status["status"] == (
        "campaign128_no_return_gates_passed_v139_development_freeze_next"
    )
    assert status["authoritative_boundaries"]["numeric_policy"]["sha256"] == sha(POLICY)
    assert status["candidate49"]["signal_entry_count"] == 0
    assert status["candidate49"]["execution_entry_count"] == 0
    assert (
        status["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )
    assert status["research_boundary"]["stress_2024_2025_return_values_opened"] is False
