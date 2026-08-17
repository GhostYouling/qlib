from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_144_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_144_mechanism_contract_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_144/research_attempt_ledger_v1.json"
)
LEDGER_DELTA_1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_144/research_attempt_ledger_v2.json"
)
LEDGER_FINAL = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_144/research_attempt_ledger_v3.json"
)
LEDGER_POSTPUBLICATION = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_144/research_attempt_ledger_v4.json"
)
LEDGER_EFFECTIVE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_144/research_attempt_ledger_v5.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_144_terminal_result_v5_20260814.json"
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
            "campaign144",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign144_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c144_{index:02d}" for index in range(1, 7)
    ]
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert (
        scouting["selection"]["genuinely_new_contract_permitted_mechanism_found"]
        is False
    )
    boundary = scouting["research_boundary"]
    assert boundary["source_rows_or_column_values_read"] is False
    assert boundary["campaign144_candidate_values_computed_or_read"] is False
    assert boundary["campaign144_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign144_frontier_rejects_consumed_or_contract_forbidden_routes() -> None:
    frontier = _load(FRONTIER)
    results = frontier["proposal_gate_results"]
    assert len(results) == 6
    assert all(item["passed"] is False for item in results)
    assert frontier["gate_summary"]["selected_candidate_count"] == 0
    assert (
        frontier["gate_summary"][
            "proposals_passing_consumed_operator_and_semantic_independence_gate"
        ]
        == 0
    )
    industry = next(item for item in results if item["catalog_id"] == "c144_05")
    assert industry["original_source_contract_permits_candidate_use"] is False
    assert frontier["decision"]["2024_2025_lockbox_opened"] is False


def test_campaign144_preserves_library_and_numeric_orders() -> None:
    complete = c128.reconstruct_complete_definitions()
    complete.extend(
        [
            {
                "name": "daily_realized_price_basis_adjustment_magnitude_1d",
                "score_direction": "higher",
            },
            {
                "name": "quarterly_realized_profit_growth_forecast_surprise_rank",
                "score_direction": "higher",
            },
        ]
    )
    assert len(complete) == 153
    assert _order_digest(complete) == (
        "bf66faef96d7058c7028da52757c65d8e0bf7978cf72d3967cd236e4da30b875"
    )

    comparisons = c128.reconstruct_comparisons()
    comparisons.extend(
        [
            {"name": c128.FACTOR_NAME, "score_direction": "higher"},
            {
                "name": "daily_realized_price_basis_adjustment_magnitude_1d",
                "score_direction": "higher",
            },
        ]
    )
    assert len(comparisons) == 141
    assert _order_digest(comparisons) == (
        "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
    )


def test_campaign144_append_only_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["effective_entry_count"] == 14
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 8
    assert ledger["effective_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1226
    assert ledger["cumulative_return_reading_development_trial_count"] == 313

    previous = ledger["genesis_previous_entry_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        evidence = ROOT / entry["evidence"]["path"]
        assert _sha(evidence) == entry["evidence"]["sha256"]
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]

    for delta_path, expected_count, expected_infrastructure_count in (
        (LEDGER_DELTA_1, 17, 11),
        (LEDGER_FINAL, 18, 12),
        (LEDGER_POSTPUBLICATION, 27, 21),
        (LEDGER_EFFECTIVE, 28, 22),
    ):
        delta = _load(delta_path)
        predecessor = ROOT / delta["authoritative_predecessor"]["path"]
        assert delta["authoritative_predecessor"]["sha256"] == _sha(predecessor)
        assert delta["authoritative_predecessor"]["chain_tip_sha256"] == previous
        for entry in delta["entries"]:
            assert entry["previous_entry_sha256"] == previous
            assert entry["entry_sha256"] == _entry_hash(entry)
            evidence = ROOT / entry["evidence"]["path"]
            assert _sha(evidence) == entry["evidence"]["sha256"]
            assert entry["candidate_comparator_price_or_return_value_read"] is False
            previous = entry["entry_sha256"]
        assert previous == delta["chain_tip_sha256"]
        assert delta["effective_entry_count"] == expected_count
        assert (
            delta["effective_infrastructure_failure_attempt_count"]
            == expected_infrastructure_count
        )
    assert (
        _load(LEDGER_EFFECTIVE)["cumulative_historical_research_attempt_count"] == 1240
    )


def test_campaign144_terminal_result_and_candidate49_boundary() -> None:
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
        terminal["library_after_campaign144"]["complete_factor_definition_count"] == 153
    )
    assert (
        terminal["library_after_campaign144"]["eligible_numeric_comparator_count"]
        == 141
    )
    assert terminal["effective_accounting"]["campaign144_attempt_count"] == 28
    assert (
        terminal["effective_accounting"]["campaign144_infrastructure_failure_count"]
        == 22
    )
    assert (
        terminal["effective_accounting"]["cumulative_historical_research_attempt_count"]
        == 1240
    )
    candidate49 = terminal["candidate49"]
    assert candidate49["signal_ledger"]["entries"] == 0
    assert candidate49["execution_ledger"]["entries"] == 0
    assert candidate49["2026_08_14_same_day_retry_performed"] is False
    assert candidate49["ledgers_changed"] is False


def test_campaign144_binding_records_and_reports() -> None:
    for path in (
        SCOUTING,
        FRONTIER,
        LEDGER,
        LEDGER_DELTA_1,
        LEDGER_FINAL,
        LEDGER_POSTPUBLICATION,
        LEDGER_EFFECTIVE,
        TERMINAL,
    ):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True, report
    heading = "## Campaign144 组合前沿值前终止"
    assert CURRENT_REPORT.read_text(encoding="utf-8").count(heading) == 1
    assert THREE_DAY_REPORT.read_text(encoding="utf-8").count(heading) == 1
