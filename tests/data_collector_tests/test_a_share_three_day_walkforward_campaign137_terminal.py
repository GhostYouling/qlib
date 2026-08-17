from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_137_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_137_mechanism_source_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_137/research_attempt_ledger.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_137/research_attempt_ledger_v2.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_137_terminal_result_v2_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v171_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign137_prevalue_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign137",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign137_finite_catalog_rejects_every_concept_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    boundary = scouting["research_boundary"]
    assert boundary["campaign137_source_rows_read"] is False
    assert boundary["campaign137_candidate_values_computed_or_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_campaign137_frontier_and_policy_preserve_152_141_orders() -> None:
    frontier = _load(FRONTIER)
    assert bindings.validate_record(FRONTIER)["all_bindings_passed"] is True
    assert frontier["concept_scouting"]["sha256"] == _sha(SCOUTING)
    assert (
        frontier["terminal_decision"]["campaign137_complete_factor_definition_created"]
        is False
    )
    policy = _load(POLICY)
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    assert policy["version"] == 171
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 152
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 141
    )
    assert (
        policy["complete_historical_feature_library"]["order_sha256"]
        == "60c465a3e2043efae6b92b8c5f3e007cd397a1cd0ec3094b4fa005665bbe5736"
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
        == "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
    )


def test_campaign137_append_only_ledger_chain_and_accounting() -> None:
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
    assert ledger["cumulative_historical_research_attempt_count"] == 1145
    assert ledger["cumulative_return_reading_development_trial_count"] == 313
    effective = _load(EFFECTIVE_LEDGER)
    assert _sha(LEDGER) == effective["authoritative_predecessor"]["sha256"]
    entry = effective["entries"][0]
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert effective["effective_entry_count"] == 8
    assert effective["effective_infrastructure_failure_attempt_count"] == 2
    assert effective["cumulative_historical_research_attempt_count"] == 1146


def test_campaign137_terminal_bindings_and_candidate49_isolation() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    assert bindings.validate_record(STATUS)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    status = _load(STATUS)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    assert status["goal"]["status"] == "active"
    assert status["candidate49"]["signal_entries"] == 0
    assert status["candidate49"]["execution_entries"] == 0
    assert status["campaign137"]["stress_2024_2025_opened"] is False


def test_unified_reports_record_campaign137_without_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_137_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign137" in text
        assert "152/141" in text
        assert "1146" in text or "1,146" in text
