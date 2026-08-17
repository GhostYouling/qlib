from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_141_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_141_mechanism_source_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_141/research_attempt_ledger.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_141/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_141/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_141_terminal_result_v3_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v181_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign141_prevalue_terminal_v3.json"
)


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
            "campaign141",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign141_complete_library_and_schema_only_catalog() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c141_{index:02d}" for index in range(1, 7)
    ]
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert scouting["selection"]["genuinely_new_independent_mechanism_found"] is False
    boundary = scouting["research_boundary"]
    assert boundary["parquet_schema_only_inspection_performed"] is True
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False

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


def test_campaign141_frontier_and_numeric_orders_remain_frozen() -> None:
    frontier = _load(FRONTIER)
    assert bindings.validate_record(FRONTIER)["all_bindings_passed"] is True
    assert frontier["mandatory_prevalue_gate"]["mechanism_independence_passed"] is False
    assert (
        frontier["terminal_decision"]["campaign141_complete_factor_definition_created"]
        is False
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


def test_campaign141_append_only_ledger_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_source_value_read"] is False
        assert entry["comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["entry_count"] == 6
    assert ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1181
    assert ledger["cumulative_return_reading_development_trial_count"] == 313

    delta_ledger = _load(LEDGER_V2)
    delta = delta_ledger["entries"][0]
    assert delta["previous_entry_sha256"] == previous
    assert delta["entry_sha256"] == _entry_hash(delta)
    assert delta["masked_failure_explicitly_recorded"] is True
    assert delta["failed_check_treated_as_passed"] is False
    assert delta_ledger["chain_tip_sha256"] == delta["entry_sha256"]
    assert delta_ledger["effective_entry_count"] == 7
    assert delta_ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert delta_ledger["cumulative_historical_research_attempt_count"] == 1182
    assert delta_ledger["cumulative_return_reading_development_trial_count"] == 313

    final_ledger = _load(LEDGER_V3)
    final_delta = final_ledger["entries"][0]
    assert final_delta["previous_entry_sha256"] == delta["entry_sha256"]
    assert final_delta["entry_sha256"] == _entry_hash(final_delta)
    assert final_delta["failed_exit_code_bypassed"] is False
    assert final_ledger["chain_tip_sha256"] == final_delta["entry_sha256"]
    assert final_ledger["effective_entry_count"] == 8
    assert final_ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert final_ledger["cumulative_historical_research_attempt_count"] == 1183
    assert final_ledger["cumulative_return_reading_development_trial_count"] == 313


def test_campaign141_terminal_policy_status_and_candidate49_isolation() -> None:
    for record in (TERMINAL, POLICY):
        assert bindings.validate_record(record)["all_bindings_passed"] is True
    status_bindings = bindings.validate_record(STATUS)
    assert status_bindings["passed_binding_count"] == 8
    assert status_bindings["failed_binding_count"] == 2
    assert {item["json_pointer"] for item in status_bindings["failed_bindings"]} == {
        "/reports/current_research_report",
        "/reports/three_day_research_report",
    }
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    status = _load(STATUS)
    assert terminal["unchanged_scientific_result"]["selected_candidate_count"] == 0
    assert policy["version"] == 181
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 153
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 141
    )
    assert status["goal"]["status"] == "active"
    assert status["candidate49"]["signal_entries"] == 0
    assert status["candidate49"]["execution_entries"] == 0
    signal = ROOT / status["candidate49"]["signal_ledger_path"]
    execution = ROOT / status["candidate49"]["execution_ledger_path"]
    assert _sha(signal) == status["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == status["candidate49"]["execution_ledger_sha256"]


def test_campaign141_reports_record_no_current_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_141_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign141" in text
        assert "153/141" in text
        assert "1183" in text
        assert "Candidate49" in text
