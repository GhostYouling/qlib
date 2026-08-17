from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign078_features as prior


ROOT = Path(__file__).resolve().parents[2]
FACTOR = "signal_day_turnover_rate_pct"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_effective_mechanism_correction_is_terminal_before_values() -> None:
    correction = _load(
        "docs/a_share_three_day_walkforward_campaign_079_mechanism_overlap_correction_20260806.json"
    )
    assert correction["status"].startswith("terminal_rejected_before_daily_source_rows")
    assert correction["invalid_mechanism_overlap_audit"]["preserved"] is True
    assert correction["terminal_factor_definition"]["name"] == FACTOR
    assert correction["decision"]["numeric_comparator_eligible"] is False
    assert correction["boundaries"]["daily_source_rows_read"] is False
    assert correction["boundaries"]["candidate_values_computed"] is False
    assert correction["boundaries"]["comparison_values_read"] is False
    assert correction["boundaries"]["historical_forward_returns_read"] is False


def test_attempt_ledger_counts_one_factor_attempt_and_no_return_trial() -> None:
    ledger = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_079/"
        "research_attempt_ledger_v1.json"
    )
    assert ledger["campaign079_attempt_count"] == 1
    assert ledger["campaign079_infrastructure_failure_count"] == 0
    assert ledger["campaign079_complete_factor_attempt_count"] == 1
    assert ledger["campaign079_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 484
    assert ledger["cumulative_return_reading_development_trial_count"] == 280


def test_v15_appends_definition_but_keeps_numeric_order_unchanged() -> None:
    policy = _load(
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v15_20260806.json"
    )
    complete = prior.reconstruct_complete_definitions() + [
        {"name": "intraday_amount_local_peak_density_238p", "score_direction": "higher"},
        {"name": FACTOR, "score_direction": "higher"},
    ]
    numeric = prior.reconstruct_comparisons() + [
        {"name": "intraday_amount_local_peak_density_238p", "score_direction": "higher"}
    ]
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 111
    assert policy["complete_historical_feature_library"]["order_sha256"] == prior._comparison_order_digest(complete)
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 109
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"] == prior._comparison_order_digest(numeric)
    assert policy["numerical_comparator_eligibility"]["newly_classified_definition"]["numeric_comparator_eligible_for_campaign080"] is False


def test_no_campaign079_value_or_development_artifacts_exist() -> None:
    experiment = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_079"
    assert not (experiment / "no_return").exists()
    assert not (experiment / "walkforward").exists()
    assert not (ROOT / "docs/a_share_three_day_walkforward_campaign_079_no_return_preregistration.json").exists()
    assert not (ROOT / "scripts/a_share_three_day_walkforward_campaign079_features.py").exists()
    assert not (ROOT / "scripts/a_share_three_day_walkforward_campaign079.py").exists()


def test_candidate49_ledgers_remain_empty_and_immutable() -> None:
    for path, digest in (
        ("data/experiments/short_horizon/candidate49_future_signal_ledger.json", "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"),
        ("data/experiments/short_horizon/candidate49_future_execution_ledger.json", "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"),
    ):
        assert _sha(path) == digest
        assert _load(path)["entries"] == []


def test_current_records_and_reports_are_consistent() -> None:
    record = _load("docs/a_share_three_day_walkforward_campaign_079_research_record.json")
    assert record["status"] == "terminal_prevalue_semantic_overlap_no_numeric_audit_or_returns"
    assert record["value_and_return_boundary"]["candidate_values_computed"] is False
    assert _sha("docs/a_share_three_day_walkforward_campaign_079_research_record.json") == "4f6b770dc3e7d4b8a0e42ce7054add8b91852fd28b20c7fbadc81bce3a082fa9"
    assert _sha("data/experiments/short_horizon/historical_walkforward/campaign_079/research_attempt_ledger_v1.json") == "fb2e9279846543b045fe0067ba795af0f2c3c0d564fbc4b925a5ebcdd60e02a5"
    assert _sha("docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v15_20260806.json") == "e4df7ab965b003d8f77cbdffa742127e8f118417e6165b52afa6ae30cc5cfb63"
    for path in (
        "docs/a_share_three_day_walkforward_campaign_079_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
        "docs/a_share_data_pipeline.md",
    ):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "Campaign079" in text
        assert "484" in text
        assert "Candidate49" in text
