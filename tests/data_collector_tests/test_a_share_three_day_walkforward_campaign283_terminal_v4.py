from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_concept_scouting_20260825.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_prevalue_mechanism_frontier_result_20260825.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_283/research_attempt_ledger_v6.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign283_terminal_v4.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_terminal_prevalue_report_v4.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign283_v4.md"
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_cross_stage_historical_report_hash_failure_20260825.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_focused_ledger_test_lifecycle_failure_20260825.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_json_binding_verifier_shape_failure_20260825.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_zsh_path_binding_verifier_failure_20260825.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_283_v3_black_format_failure_20260825.json",
)
UNIFIED = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(file_path: Path) -> dict:
    value = json.loads(file_path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _resolve(path_value: str) -> Path:
    target = Path(path_value)
    return target if target.is_absolute() else ROOT / target


def _assert_binding(binding: dict) -> None:
    target = _resolve(binding["path"])
    assert target.is_file()
    assert _sha(target) == binding["sha256"]


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        _assert_binding(binding)


def _entry_hash(entry: dict, previous: str) -> str:
    payload = "|".join(
        ("campaign283", entry["attempt_id"], previous, entry["phase"], entry["status"])
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_and_result_remain_prevalue() -> None:
    assert (
        _sha(CATALOG)
        == "d039872074dcb050345c9bc0a0c7355ef16022de4bc6c89c637946821e223721"
    )
    assert (
        _sha(RESULT)
        == "01df32486258d16c7ef3b5461ebacfd362dd36b627d5bb5767857d1bcbd62321"
    )
    catalog = _load(CATALOG)
    _assert_binding(catalog["authoritative_predecessor"])
    _assert_binding(catalog["historical_policy"])
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    assert len(catalog["concept_catalog"]) == len(result["route_results"]) == 7
    assert result["decision"]["economically_independent_route_count"] == 1
    assert result["decision"]["source_contract_ready_route_count"] == 0
    assert result["decision"]["selected_route_count"] == 0
    assert all(route["formula"] is None for route in result["route_results"])


def test_effective_v6_ledger_replays_all_entries() -> None:
    assert (
        _sha(LEDGER)
        == "5a971ee573fd4ec5011dd7f79fd84714bab27b089e0b837f73eeb8a929d82aff"
    )
    ledger = _load(LEDGER)
    _assert_binding(ledger["authoritative_predecessor"])
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger["entries"], start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        assert entry["scientific_attempt"] is (ordinal <= 7)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 12
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 2893
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_v4_reports_and_unified_accounting_correction() -> None:
    report = REPORT.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "累计历史尝试 2,893" in report
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    for report_path in UNIFIED:
        text = report_path.read_text(encoding="utf-8")
        assert text.count("### Campaign283 验证会计更正 v3") == 1
        correction = text.split("### Campaign283 验证会计更正 v3", maxsplit=1)[1]
        assert "累计历史尝试 2,893" in correction
        assert "Campaign284" in correction


def test_five_failures_are_value_free_and_not_consumed() -> None:
    assert len(FAILURES) == 5
    for failure_path in FAILURES:
        failure = _load(failure_path)
        assert failure["failure_classification"]["research_value_read"] is False
        assert (
            failure["failure_classification"]["result_consumed_as_validation_pass"]
            is False
        )
        boundary = failure["research_boundary"]
        assert boundary["provider_or_web_request_issued"] is False
        assert boundary["candidate49_ledgers_changed"] is False


def test_v4_state_binds_current_artifacts_and_active_goal() -> None:
    state = _load(STATE)
    _assert_bindings(state["authoritative_inputs"])
    assert state["active_data_root"] == "/Volumes/DIsk/Disk-Coding/qlib/data"
    assert state["goal"]["status"] == "active"
    assert state["goal"]["current_campaign"] == 283
    assert "Campaign284" in state["goal"]["next_safe_work"]
    assert state["effective_accounting"]["campaign283_attempt_count"] == 12
    assert (
        state["effective_accounting"]["campaign283_infrastructure_failure_count"] == 5
    )


def test_candidate49_and_credential_boundaries_remain_closed() -> None:
    state = _load(STATE)
    assert state["credential_presence_only"]["credential_value_or_digest_read"] is False
    candidate49 = state["candidate49"]
    assert candidate49["sole_active_prospective_candidate"] is True
    assert candidate49["candidate49_plan_or_run_executed"] is False
    assert candidate49["historical_backfill_performed"] is False
    assert _sha(SIGNAL) == candidate49["signal_ledger_sha256"]
    assert _sha(EXECUTION) == candidate49["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_no_values_stress_current_use_or_advice() -> None:
    state = _load(STATE)
    boundary = state["research_boundary"]
    assert boundary["repository_metadata_and_prior_terminal_history_read"] is True
    for key in (
        "provider_or_web_request_issued",
        "provider_response_or_source_row_read",
        "provider_credential_value_or_digest_read",
        "candidate_or_comparator_value_read",
        "historical_daily_price_or_forward_return_value_read",
        "stress_2024_2025_opened",
        "candidate49_plan_or_run_executed_by_campaign283",
        "candidate49_historical_backfill_performed",
        "candidate49_ledgers_changed",
        "second_prospective_candidate_created",
        "current_scoring_selection_sizing_positions_or_orders_performed",
        "investment_advice",
    ):
        assert boundary[key] is False
    assert state["library_state"]["changed_by_campaign283"] is False
    assert state["library_state"]["complete_factor_definition_count"] == 162
    assert state["library_state"]["eligible_numeric_comparator_count"] == 143
