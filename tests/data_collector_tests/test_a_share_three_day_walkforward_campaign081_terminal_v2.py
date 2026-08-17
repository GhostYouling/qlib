from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign081_verified_v2.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_081_terminal_completion_freeze_v2_20260806.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_081/research_attempt_ledger_v4.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_v2_state_and_freeze_bindings_pass() -> None:
    assert bindings.validate_record(STATE)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True


def test_additive_suite_failure_accounting_and_terminal_result() -> None:
    state = _load(STATE)
    ledger = _load(LEDGER)
    accounting = state["corrected_attempt_accounting"]
    assert accounting["campaign081_infrastructure_failures"] == 8
    assert accounting["campaign081_attempts"] == 9
    assert accounting["campaign081_ledger_entries"] == 10
    assert accounting["cumulative_historical_research_attempts"] == 500
    assert accounting["cumulative_return_reading_development_trials"] == 282
    assert ledger["campaign081_infrastructure_failure_count"] == 8
    assert state["campaign081_terminal_result_unchanged"][
        "development_survivor_count"
    ] == 0
    assert state["campaign081_terminal_result_unchanged"][
        "stress_2024_2025_opened"
    ] is False


def test_candidate49_and_campaign082_boundaries_remain_frozen() -> None:
    state = _load(STATE)
    assert state["candidate49_future_only_layer"]["signal_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["execution_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["provider_request_issued"] is False
    assert state["next_offline_research"]["campaign082_scouting_authorized"] is True
    assert state["historical_research_boundary"][
        "may_generate_current_score_selection_sizing_order_or_advice"
    ] is False
