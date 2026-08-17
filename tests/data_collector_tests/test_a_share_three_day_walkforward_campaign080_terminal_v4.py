from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign080_verified_v4.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_080_terminal_completion_freeze_v4_20260806.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_080/research_attempt_ledger_v5.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_v4_state_and_freeze_bindings_pass() -> None:
    assert bindings.validate_record(STATE)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True


def test_additive_verification_failure_accounting_and_result() -> None:
    state = _load(STATE)
    ledger = _load(LEDGER)
    accounting = state["corrected_attempt_accounting"]
    assert accounting["campaign080_infrastructure_failures"] == 6
    assert accounting["campaign080_attempts"] == 7
    assert accounting["campaign080_ledger_entries"] == 8
    assert accounting["cumulative_historical_research_attempts"] == 491
    assert accounting["cumulative_return_reading_development_trials"] == 281
    assert ledger["campaign080_infrastructure_failure_count"] == 6
    assert state["campaign080_terminal_result_unchanged"]["development_survivor_count"] == 0
    assert state["campaign080_terminal_result_unchanged"]["stress_2024_2025_opened"] is False


def test_final_candidate49_credential_and_campaign081_boundaries() -> None:
    state = _load(STATE)
    assert state["candidate49_future_only_layer"]["signal_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["execution_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["provider_request_issued_this_campaign"] is False
    assert state["credential_state"]["workflow_loads_nonempty_tushare_token"] is True
    assert state["next_offline_research"]["campaign081_scouting_authorized"] is True
    assert state["historical_research_boundary"][
        "may_generate_current_score_selection_sizing_order_or_advice"
    ] is False
