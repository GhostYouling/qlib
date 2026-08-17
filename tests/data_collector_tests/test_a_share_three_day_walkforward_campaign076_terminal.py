from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign076_features as features


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_terminal_research_record_and_attempt_accounting() -> None:
    x = _load("docs/a_share_three_day_walkforward_campaign_076_research_record.json")
    assert x["status"] == "terminal_zero_development_survivors_stress_closed"
    assert x["attempt_accounting"]["campaign076_infrastructure_failures"] == 8
    assert x["attempt_accounting"]["campaign076_attempts"] == 9
    assert x["attempt_accounting"]["cumulative_historical_attempts"] == 465
    assert x["attempt_accounting"]["cumulative_return_reading_development_trials"] == 278


def test_no_return_audit_passed_all_106_without_prices_or_returns() -> None:
    x = _load("data/experiments/short_horizon/historical_walkforward/campaign_076/no_return/20260806T033002Z_campaign076_no_return_audit.json")
    f = features.FACTOR_NAME
    assert x["coverage_and_capacity"][f]["gate_passed_before_comparison_values"] is True
    assert x["uniqueness"][f]["comparison_factor_count"] == 106
    assert x["uniqueness"][f]["all_required_numeric_comparisons_passed"] is True
    assert x["historical_daily_price_fields_read"] == []
    assert x["historical_forward_return_fields_read"] is False


def test_development_is_one_trial_zero_survivors_stress_closed() -> None:
    ledger = _load("data/experiments/short_horizon/historical_walkforward/campaign_076/walkforward/trial_ledger.json")
    survivors = _load("data/experiments/short_horizon/historical_walkforward/campaign_076/walkforward/development_survivors.json")
    stress = _load("data/experiments/short_horizon/historical_walkforward/campaign_076/walkforward/exposed_stress_consumption_record.json")
    assert len(ledger["entries"]) == 1
    assert survivors["selected_survivor_count"] == 0
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v12_appends_exact_factor_and_orders() -> None:
    x = _load("docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v12_20260806.json")
    assert x["complete_historical_feature_library"]["factor_definition_count"] == 108
    assert x["complete_historical_feature_library"]["order_sha256"] == "0b6758e579e190e35e0ac2e5bda666194369f0c71be4dc2a35b5ec744f419b94"
    assert x["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 107
    assert x["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"] == "b219b4879057a48600ba3e6d3d3a1a35ee6575d70b1476a71cf463ff8b63acc2"


def test_candidate49_ledgers_remain_empty_and_immutable() -> None:
    for path, expected in (
        ("data/experiments/short_horizon/candidate49_future_signal_ledger.json", "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"),
        ("data/experiments/short_horizon/candidate49_future_execution_ledger.json", "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"),
    ):
        x = _load(path)
        assert _sha(path) == expected
        assert x["entries"] == []


def test_reports_include_campaign076_without_trading_claims() -> None:
    for path in ("docs/a_share_three_day_walkforward_campaign_076_report.md", "data/experiments/short_horizon/three_day_research_report.md", "docs/a_share_data_pipeline.md"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "Campaign076" in text
        assert "24.195927" in text


def test_current_artifact_hashes() -> None:
    assert _sha("docs/a_share_three_day_walkforward_campaign_076_research_record.json") == "bd7aaef3d8b05e2d9c47214b42aa95ad4e09ef0835cb0d2849fab0d7cbdb8f39"
    assert _sha("data/experiments/short_horizon/historical_walkforward/campaign_076/research_attempt_ledger_v3.json") == "ac26fa86290a48bc8313dfd2441f592c001dd11ea323101a273e0930dc89c815"
    assert _sha("docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v12_20260806.json") == "8bf3f6a261816bcf0e71c86cada1224b91c8a75042040ae50dbc371076447484"
