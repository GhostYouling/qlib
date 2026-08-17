from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign120_features as features


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_120_terminal_result_20260814.json"
)
CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_120_terminal_accounting_correction_v2_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v112_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign120_terminal_v2.json"
)
ATTEMPTS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_120/research_attempt_ledger_v4.json"
)
COVERAGE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_120/coverage/campaign120_coverage_audit.json"
)
UNIQUENESS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_120/uniqueness/campaign120_ordered_uniqueness_audit.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign120_terminal_bindings_and_final_status() -> None:
    for path in (TERMINAL, CORRECTION, POLICY, STATUS):
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    status = _load(STATUS)
    assert terminal["status"] == (
        "terminal_numeric_uniqueness_failure_before_historical_daily_prices_or_returns"
    )
    assert status["campaign120_terminal"]["terminal"] is True
    assert status["campaign120_terminal"]["retry_or_rescue_allowed"] is False


def test_campaign120_snapshot_and_coverage_pass_are_preserved() -> None:
    terminal = _load(TERMINAL)
    coverage = _load(COVERAGE)["coverage_and_variation"]
    snapshot = terminal["snapshot_evidence"]
    assert snapshot["partitions"] == 33015
    assert snapshot["rows"] == snapshot["eligible_rows"] == 7724498
    assert snapshot["all_partition_byte_frame_hashes_and_integer_values_reverified"]
    assert coverage["median_daily_coverage"] == 0.9994517542211769
    assert coverage["p05_daily_coverage"] == 0.9956886515772271
    assert coverage["gate_passed_before_comparator_values"] is True


def test_campaign120_uniqueness_failure_stops_before_returns() -> None:
    audit = _load(UNIQUENESS)
    terminal = _load(TERMINAL)
    assert audit["comparison_summary"]["comparison_factor_count"] == 137
    assert audit["comparison_summary"]["comparison_order_matches_preregistration"]
    assert (
        audit["comparison_summary"]["all_required_numeric_comparisons_passed"] is False
    )
    assert (
        audit["comparison_summary"][
            "maximum_observed_absolute_median_daily_rank_correlation"
        ]
        == 0.8036786444597779
    )
    assert terminal["uniqueness_evidence"]["failed_comparator"]["name"] == (
        "intraday_range_weak_order_entropy_236t"
    )
    unopened = terminal["unopened_stages"]
    assert unopened["historical_daily_price_fields_read"] == []
    assert unopened["historical_forward_return_fields_read"] is False
    assert unopened["development_trial_count"] == 0
    assert unopened["stress_2024_2025_opened"] is False


def test_campaign120_final_attempt_accounting_is_append_only() -> None:
    attempts = _load(ATTEMPTS)
    correction = _load(CORRECTION)
    assert attempts["attempt_count"] == attempts["ledger_entry_count"] == 19
    assert attempts["infrastructure_failure_count"] == 13
    assert attempts["return_reading_complete_development_trial_count"] == 0
    assert attempts["cumulative_historical_research_attempt_count"] == 954
    assert attempts["cumulative_return_reading_development_trial_count"] == 305
    prior = ROOT / attempts["supersedes_without_rewriting"]["path"]
    assert _sha(prior) == attempts["supersedes_without_rewriting"]["sha256"]
    assert correction["correction"]["scientific_result_changed"] is False
    assert correction["correction"]["library_order_changed"] is False


def test_v112_preserves_campaign120_once_in_both_frozen_libraries() -> None:
    policy = _load(POLICY)
    complete = features.reconstruct_complete_definitions()
    numeric = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(complete) == 146
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 146
    )
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        features._order_digest(complete)
    )
    assert len(numeric) == 138
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 138
    )
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_order_sha256"
    ] == features._order_digest(numeric)


def test_campaign120_reports_candidate49_and_current_action_boundaries() -> None:
    terminal = _load(TERMINAL)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    for relative in (
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
        "docs/a_share_three_day_walkforward_campaign_120_terminal_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign120" in text
        assert "0.803679" in text
        assert "2024–2025" in text
