from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_096/"
    "research_attempt_ledger_v2.json"
)
RECORD = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_096_research_record_v2.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v41_20260807.json"
)
FREEZE = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_096_"
    "terminal_completion_freeze_v2_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_effective_v2_binding_chain_is_exact() -> None:
    assert _sha256(LEDGER) == (
        "8ec7e18246a3a6328a9280afd17134c4aecceed5c6e256161bdf79943375301d"
    )
    assert _sha256(RECORD) == (
        "fd6d20175b591cdc5a0b5762fff40b048163d6a2c855374e07e3a6887a2b9e2c"
    )
    assert _sha256(POLICY) == (
        "00ff7f93fcbdf09f8c75f81f1c1bc9e247d32a3088f50967316cc9f9a3bae9c5"
    )
    assert _sha256(FREEZE) == (
        "ea2830a5b9d56c9390802d91169610a5997f9120aa4b3732482c10941d748521"
    )
    for path in (LEDGER, RECORD, POLICY, FREEZE):
        assert bindings.validate_record(path)["all_bindings_passed"] is True


def test_postresult_failure_is_one_additive_attempt_only() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["supersedes_without_rewriting"]
    assert predecessor["preserved"] is True
    assert predecessor["preserved_entry_count"] == 6
    assert predecessor["preserved_attempt_count"] == 6
    assert len(ledger["appended_entries"]) == 1
    appended = ledger["appended_entries"][0]
    assert appended["ordinal"] == 7
    assert appended["kind"] == "infrastructure_or_implementation_failure"
    assert appended["research_attempt_count_increment"] == 1
    assert appended["development_trial_count_increment"] == 0
    assert appended["factor_or_snapshot_values_recomputed"] is False
    assert appended["comparison_values_read"] is False
    assert appended["historical_forward_returns_read"] is False
    assert ledger["campaign096_attempt_count"] == 7
    assert ledger["campaign096_ledger_entry_count"] == 7
    assert ledger["campaign096_infrastructure_or_implementation_failure_count"] == 6
    assert ledger["campaign096_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 666
    assert ledger["cumulative_return_reading_development_trial_count"] == 291


def test_scientific_result_and_v41_orders_are_unchanged() -> None:
    record = _load(RECORD)
    result = record["scientific_result"]
    assert record["supersedes_without_rewriting"]["scientific_result_changed"] is False
    assert result["coverage_gate_passed"] is False
    assert result["median_coverage"] == 0.9231861259965655
    assert result["p05_coverage"] == 0.8075504413619168
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_returns_read"] is False
    assert result["development_trial_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    policy = _load(POLICY)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 128
    )
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        "9380287d8339113cb01fa99670c77078f9be82b7463c06c1e7debb92b1add48b"
    )
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 125
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "50a737e640cac8e063aab8be0b483a6d9be87d0e5ddd1e1395e625ab371a4cae"
    )
    support = policy[
        "mandatory_prevalue_support_predicate_gate_for_campaign097_and_later"
    ]
    assert support["required"] is True
    assert (
        support["known_campaign086_campaign096_support_equivalence_must_be_challenged"]
        is True
    )


def test_reports_and_candidate49_boundaries_remain_exact() -> None:
    freeze = _load(FREEZE)
    for key in (
        "campaign_report",
        "unified_report",
        "current_report",
        "data_pipeline_documentation",
    ):
        report = ROOT / freeze[key]["path"]
        assert _sha256(report) == freeze[key]["sha256"]
        text = report.read_text(encoding="utf-8")
        assert "666" in text
        assert "291" in text
    signal = ROOT / (
        "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = ROOT / (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == freeze["candidate49_signal_ledger_sha256"]
    assert _sha256(execution) == freeze["candidate49_execution_ledger_sha256"]
    assert freeze["candidate49_ledgers_changed"] is False
    assert freeze["provider_request_issued"] is False
    assert freeze["current_scoring_selection_sizing_or_orders_performed"] is False
    assert freeze["investment_advice"] is False
