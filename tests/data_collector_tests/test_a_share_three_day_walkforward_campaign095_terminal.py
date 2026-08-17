from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign095_features as c95


ROOT = Path(__file__).resolve().parents[2]
FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_095_prevalue_reflection_semantic_failure_20260807.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_095/research_attempt_ledger_v1.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v39_20260807.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_095_research_record.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign095_terminal_before_values() -> None:
    failure = _load(FAILURE)
    boundary = failure["research_boundary"]
    assert failure["classification"] == {
        "scientific_semantic_failure": True,
        "infrastructure_or_implementation_failure": False,
        "complete_factor_attempt": True,
        "return_reading_development_trial": False,
    }
    assert boundary["campaign095_minute_source_rows_read"] is False
    assert boundary["campaign095_candidate_values_computed"] is False
    assert boundary["comparison_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign095_attempt_accounting_is_additive() -> None:
    ledger = _load(LEDGER)
    assert ledger["append_only"] is True
    assert len(ledger["entries"]) == ledger["campaign095_ledger_entry_count"] == 1
    assert ledger["campaign095_attempt_count"] == 1
    assert ledger["campaign095_infrastructure_or_implementation_failure_count"] == 0
    assert ledger["campaign095_complete_factor_attempt_count"] == 1
    assert ledger["campaign095_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 659
    assert ledger["cumulative_return_reading_development_trial_count"] == 291


def test_v39_appends_semantic_definition_without_numeric_comparator() -> None:
    policy = _load(POLICY)
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 127
    assert policy["complete_historical_feature_library"]["order_sha256"] == "17ad9beb53d236171155211ea4cc4b9ec05b8edea7ebc51ca7705f84adc9e030"
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 124
    assert numeric["eligible_numeric_comparator_order_sha256"] == c95.COMPARISON_ORDER_SHA256
    assert numeric["newly_classified_definition"]["numeric_comparator_eligible_for_campaign096"] is False
    assert c95._comparison_order_digest(c95.reconstruct_complete_definitions()) == "332d461e2b00bf6645eeb74cd59d3710d63f88b34add8afaadf4807ea712263d"


def test_candidate49_and_record_boundaries_remain_closed() -> None:
    record = _load(RECORD)
    layer = record["candidate49_future_only_layer"]
    assert layer["signal_ledger_entries"] == layer["execution_ledger_entries"] == 0
    assert layer["historical_backfill_performed"] is False
    assert layer["provider_request_issued"] is False
    assert layer["second_prospective_candidate_created"] is False
    assert _sha256(POLICY) == "26af71f841cf9d1880821b61853a347dfff9bc42652b2af09220aebf72de9bb6"
