from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign080_verified_v2.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_080_terminal_completion_freeze_v2_20260806.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_080/research_attempt_ledger_v3.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_v2_state_and_freeze_bindings_pass() -> None:
    assert bindings.validate_record(STATE)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True


def test_current_attempt_accounting_includes_both_infrastructure_failures() -> None:
    state = _load(STATE)
    ledger = _load(LEDGER)
    assert state["corrected_attempt_accounting"] == {
        "campaign080_infrastructure_failures": 2,
        "campaign080_complete_factor_attempts": 1,
        "campaign080_attempts": 3,
        "campaign080_ledger_entries": 4,
        "campaign080_return_reading_development_trials": 1,
        "cumulative_historical_research_attempts": 487,
        "cumulative_return_reading_development_trials": 281,
    }
    assert ledger["campaign080_infrastructure_failure_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 487


def test_terminal_result_and_future_library_are_unchanged() -> None:
    state = _load(STATE)
    assert state["campaign080_terminal_result_unchanged"]["development_survivor_count"] == 0
    assert state["campaign080_terminal_result_unchanged"]["stress_2024_2025_opened"] is False
    assert state["next_offline_research"]["complete_definition_count"] == 112
    assert state["next_offline_research"]["numeric_comparator_count"] == 110
    assert state["candidate49_future_only_layer"]["signal_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["execution_ledger_entries"] == 0
