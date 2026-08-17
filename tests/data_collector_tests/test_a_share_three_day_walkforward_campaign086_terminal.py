from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign086_verified.json"
FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_terminal_completion_freeze_20260807.json"
)
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_086_research_record.json"
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v25_20260807.json"
)
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_086/research_attempt_ledger_v10.json"
)
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_086/no_return/20260806T171922Z_campaign086_no_return_audit.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authoritative_state_and_terminal_bindings_are_live() -> None:
    state = _json(STATE)
    assert _sha256(STATE) == "124affacf9b3665589cfc08a72e6886c5d1baa2dd5fc721b7450f066755dc12b"
    assert state["status"].startswith("campaign086_terminal_coverage_rejection")
    assert state["terminal_completion_freeze"]["sha256"] == _sha256(FREEZE)
    assert state["current_research_record"]["sha256"] == _sha256(RECORD)
    assert state["current_research_attempt_ledger"]["sha256"] == _sha256(LEDGER)
    assert state["future_numeric_comparator_policy_v25"]["sha256"] == _sha256(
        POLICY
    )


def test_terminal_result_stopped_before_comparisons_or_returns() -> None:
    audit = _json(AUDIT)
    factor = "intraday_intrabar_close_location_serial_persistence_238p"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["gate_passed_before_comparison_values"] is False
    assert coverage["median_coverage"] == 0.9231861259965655
    assert coverage["p05_coverage"] == 0.8075504413619168
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is False
    assert uniqueness["comparison_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_attempt_and_future_library_accounting() -> None:
    ledger = _json(LEDGER)
    policy = _json(POLICY)
    assert ledger["campaign086_attempt_count"] == 10
    assert ledger["campaign086_infrastructure_failure_count"] == 9
    assert ledger["campaign086_complete_factor_attempt_count"] == 1
    assert ledger["campaign086_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 582
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 118
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_count"
    ] == 116
    assert policy["research_boundary"][
        "campaign086_terminal_coverage_failure_rewritten"
    ] is False


def test_reporting_and_candidate49_boundaries_are_current() -> None:
    state = _json(STATE)
    for item in state["unified_reporting"].values():
        path = REPO_ROOT / item["path"]
        assert item["sha256"] == _sha256(path)
        text = path.read_text(encoding="utf-8")
        assert "Campaign086" in text
        assert "92.318613" in text
    layer = state["candidate49_future_only_layer"]
    assert layer["remains_only_active_prospective_candidate"] is True
    assert layer["signal_ledger_entries"] == 0
    assert layer["execution_ledger_entries"] == 0
    assert layer["historical_backfill_performed"] is False
