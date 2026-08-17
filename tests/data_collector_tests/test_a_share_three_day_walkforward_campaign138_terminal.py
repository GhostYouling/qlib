from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_138_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_138_mechanism_source_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_138/research_attempt_ledger.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_138/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_138_terminal_result_v3_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v174_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign138_prevalue_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign138",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign138_catalog_and_schema_gate_reject_all_six_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    daily = scouting["accepted_local_schema_audit"]["accepted_daily_schema_sample"]
    forbidden = {
        "peTTM",
        "pbMRQ",
        "psTTM",
        "pcfNcfTTM",
        "total_mv",
        "circ_mv",
        "total_share",
        "free_share",
    }
    assert forbidden.isdisjoint(daily["field_names"])
    assert daily["valuation_or_share_count_fields_present"] == []
    boundary = scouting["research_boundary"]
    assert boundary["parquet_schema_only_inspection_performed"] is True
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_campaign138_frontier_bindings_and_no_provider_admission() -> None:
    frontier = _load(FRONTIER)
    assert bindings.validate_record(FRONTIER)["all_bindings_passed"] is True
    assert frontier["concept_scouting"]["sha256"] == _sha(SCOUTING)
    assert (
        frontier["source_metadata_review"]["programmatic_provider_request_issued"]
        is False
    )
    assert (
        frontier["source_metadata_review"]["source_rows_or_column_values_read"] is False
    )
    decision = frontier["terminal_decision"]
    assert decision["campaign138_complete_factor_definition_created"] is False
    assert decision["campaign138_may_request_new_provider_history"] is False


def test_campaign138_append_only_ledger_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["entry_count"] == 7
    assert ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1153
    assert ledger["cumulative_return_reading_development_trial_count"] == 313
    effective = _load(EFFECTIVE_LEDGER)
    assert effective["authoritative_predecessor"]["chain_tip_sha256"] == (
        "9008fdb174022a8d6e6528474d6720659870ac582685a4f75359fc64cb060aea"
    )
    entry = effective["entries"][0]
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert effective["effective_entry_count"] == 9
    assert effective["effective_infrastructure_failure_attempt_count"] == 3
    assert effective["cumulative_historical_research_attempt_count"] == 1155


def test_campaign138_terminal_policy_status_and_candidate49_isolation() -> None:
    for record in (TERMINAL, POLICY, STATUS):
        assert bindings.validate_record(record)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    status = _load(STATUS)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    assert policy["version"] == 174
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 152
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 141
    )
    assert status["goal"]["status"] == "active"
    assert status["candidate49"]["signal_entries"] == 0
    assert status["candidate49"]["execution_entries"] == 0
    assert status["campaign138"]["stress_2024_2025_opened"] is False


def test_unified_reports_record_campaign138_without_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_138_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign138" in text
        assert "152/141" in text
        assert "1155" in text or "1,155" in text
