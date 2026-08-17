from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign146_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_147_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_147_mechanism_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_147/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_147_terminal_result_20260814.json"
)
CURRENT_REPORT = ROOT / "data/experiments/short_horizon/current_research_report.md"
THREE_DAY_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _order_digest(items: list[dict[str, str]]) -> str:
    payload = json.dumps(
        [[item["name"], item["score_direction"]] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign147",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign147_finite_catalog_records_every_choice_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c147_{index:02d}" for index in range(1, 7)
    ]
    assert all(item["hypothetical_formula"] for item in catalog)
    assert all(item["direction"] == "higher" for item in catalog)
    assert all(item["parameters"] for item in catalog)
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert (
        scouting["selection"]["genuinely_new_contract_permitted_mechanism_found"]
        is False
    )
    boundary = scouting["research_boundary"]
    assert boundary["source_rows_or_column_values_read"] is False
    assert boundary["campaign147_candidate_values_computed_or_read"] is False
    assert boundary["campaign147_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign147_frontier_rejects_consumed_mechanism_routes() -> None:
    frontier = _load(FRONTIER)
    results = frontier["proposal_gate_results"]
    assert len(results) == 6
    assert all(
        item["accepted_historical_source_and_original_contract_permits_inputs"] is True
        for item in results
    )
    assert all(
        item["semantically_independent_from_terminal_library"] is False
        for item in results
    )
    assert all(item["passed"] is False for item in results)
    summary = frontier["gate_summary"]
    assert summary["proposals_passing_original_source_contract_gate"] == 6
    assert (
        summary["proposals_passing_consumed_family_and_semantic_independence_gate"] == 0
    )
    assert summary["selected_candidate_count"] == 0
    assert frontier["decision"]["2024_2025_lockbox_opened"] is False


def test_campaign147_preserves_complete_and_numeric_library_orders() -> None:
    complete = features.reconstruct_complete_definitions()
    numeric = features.reconstruct_comparisons() + [
        {
            "name": features.FACTOR_NAME,
            "score_direction": "higher",
        }
    ]
    assert len(complete) == 155
    assert _order_digest(complete) == (
        "2e4114edb26fa3aaebd145ef07fe4e2ac9c5d9dc4586cf70ff61c20e39b954ba"
    )
    assert len(numeric) == 142
    assert _order_digest(numeric) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )


def test_campaign147_append_only_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["effective_entry_count"] == 7
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["effective_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1280
    assert ledger["cumulative_return_reading_development_trial_count"] == 314

    previous = ledger["genesis_previous_entry_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        evidence = ROOT / entry["evidence"]["path"]
        assert _sha(evidence) == entry["evidence"]["sha256"]
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_campaign147_terminal_result_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    result = terminal["terminal_scientific_result"]
    assert result["finite_concepts_reviewed"] == 6
    assert result["selected_candidate_count"] == 0
    assert result["source_acceptance_coverage_uniqueness_or_return_stage_run"] is False
    assert (
        result["source_candidate_comparator_daily_price_or_forward_return_values_read"]
        is False
    )
    assert (
        terminal["library_after_campaign147"]["complete_factor_definition_count"] == 155
    )
    assert (
        terminal["library_after_campaign147"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert terminal["effective_accounting"]["campaign147_attempt_count"] == 7
    assert (
        terminal["effective_accounting"]["cumulative_historical_research_attempt_count"]
        == 1280
    )
    candidate49 = terminal["candidate49"]
    assert candidate49["signal_ledger"]["entries"] == 0
    assert candidate49["execution_ledger"]["entries"] == 0
    assert candidate49["2026_08_14_same_day_retry_performed"] is False
    assert candidate49["ledgers_changed"] is False


def test_campaign147_bindings_and_unified_reports() -> None:
    for path in (SCOUTING, FRONTIER, LEDGER, TERMINAL):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True, report
    heading = "## Campaign147 非线性收益—金额前沿值前终止"
    assert CURRENT_REPORT.read_text(encoding="utf-8").count(heading) == 1
    assert THREE_DAY_REPORT.read_text(encoding="utf-8").count(heading) == 1
