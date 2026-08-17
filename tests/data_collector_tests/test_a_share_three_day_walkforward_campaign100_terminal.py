from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as definitions

ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_100/no_return/20260807T123335Z_campaign100_no_return_audit.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_100_no_return_audit_result_binding_20260807.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_100/research_attempt_ledger_v9.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v54_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_no_return_result_is_exact_and_reads_no_returns() -> None:
    assert _sha256(AUDIT) == (
        "d9b23ba418a5bfbcc7671ab1162c5ff15cf5aab4817d321f19790a75c6fcf813"
    )
    assert _sha256(RESULT) == (
        "3138115f27a705f9e510521e706029a460a03e52ed717a37f0dd63c1d14230fd"
    )
    audit = _load(AUDIT)
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False
    assert _load(RESULT)["development_trial_authorized"] is False


def test_coverage_passes_and_all_128_comparators_are_accounted() -> None:
    audit = _load(AUDIT)
    coverage = next(iter(audit["coverage_and_capacity"].values()))
    uniqueness = next(iter(audit["uniqueness"].values()))
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9983557108069769
    assert coverage["p05_coverage"] == 0.9933708902303229
    assert uniqueness["comparison_factor_count"] == 128
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_numeric_comparisons_passed"] is False
    failed = {
        item["comparison_factor"]: item["absolute_median_daily_rank_correlation"]
        for item in uniqueness["comparisons"]
        if item["gate_passed"] is not True
    }
    assert failed == {
        "intraday_price_update_share_238m": 0.9123522089342854,
        "intraday_return_weak_order_entropy_234t": 0.8857119447213537,
        "intraday_terminal_nominal_share_price_affordability_rank_240m": 0.8947994447045681,
    }


def test_v53_orders_append_campaign100_once() -> None:
    policy = _load(POLICY)
    new = {"name": definitions.FACTOR_NAME, "score_direction": "higher"}
    complete = definitions.reconstruct_complete_definitions() + [new]
    numeric = definitions.reconstruct_comparisons() + [new]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 132
    assert definitions._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 129
    assert (
        definitions._order_digest(numeric)
        == numeric_policy["eligible_numeric_comparator_order_sha256"]
    )
    assert numeric_policy["last_comparator"][
        "numeric_comparator_eligible_for_campaign101"
    ]


def test_attempt_accounting_and_zero_development_trials_are_preserved() -> None:
    assert _sha256(LEDGER) == (
        "83db16f48a3242c8d514b9f7276db7dba61a3994c1816f6b2311fc7e3f63a868"
    )
    ledger = _load(LEDGER)
    assert ledger["campaign100_attempt_count"] == 14
    assert ledger["campaign100_ledger_entry_count"] == 15
    assert (
        ledger["campaign100_infrastructure_implementation_or_recording_failure_count"]
        == 6
    )
    assert ledger["campaign100_complete_no_return_factor_outcome_count"] == 1
    assert ledger["campaign100_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 724
    assert ledger["cumulative_return_reading_development_trial_count"] == 294


def test_reports_expose_terminal_uniqueness_rejection() -> None:
    paths = [
        ROOT / "docs/a_share_three_day_walkforward_campaign_100_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Campaign100" in text
        assert "0.912352" in text
        assert "128" in text
        assert "未读取" in text


def test_candidate49_ledgers_remain_empty_and_unchanged() -> None:
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
