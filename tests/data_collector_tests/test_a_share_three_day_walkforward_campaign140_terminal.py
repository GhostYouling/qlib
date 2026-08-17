from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_140_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_140_mechanism_source_frontier_audit_v2_20260814.json"
)
BASE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_140/research_attempt_ledger.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_140/research_attempt_ledger_v2.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_140_terminal_result_v2_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v178_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign140_prevalue_terminal_v2.json"
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
            "campaign140",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign140_complete_library_and_schema_only_catalog() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c140_{index:02d}" for index in range(1, 7)
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


def test_campaign140_frontier_and_numeric_orders_remain_frozen() -> None:
    frontier = _load(FRONTIER)
    assert bindings.validate_record(FRONTIER)["all_bindings_passed"] is True
    unchanged = frontier["unchanged_scientific_contract"]
    assert unchanged["concept_scouting_sha256"] == _sha(SCOUTING)
    assert unchanged["selected_candidate_count"] == 0
    assert unchanged["source_rows_or_column_values_read"] is False

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


def test_campaign140_append_only_ledger_chain_and_accounting() -> None:
    base = _load(BASE_LEDGER)
    previous = base["chain_genesis"]
    for entry in base["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_source_value_read"] is False
        assert entry["comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert base["chain_tip_sha256"] == previous
    assert base["entry_count"] == 6

    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["chain_tip_sha256"] == previous
    delta = ledger["entries"][0]
    assert delta["previous_entry_sha256"] == previous
    assert delta["entry_sha256"] == _entry_hash(delta)
    assert ledger["chain_tip_sha256"] == delta["entry_sha256"]
    assert ledger["effective_entry_count"] == 7
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1175
    assert ledger["cumulative_return_reading_development_trial_count"] == 313


def test_campaign140_terminal_policy_status_and_candidate49_isolation() -> None:
    for record in (TERMINAL, POLICY, STATUS):
        assert bindings.validate_record(record)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    status = _load(STATUS)
    assert terminal["unchanged_scientific_result"]["selected_candidate_count"] == 0
    assert policy["version"] == 178
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


def test_campaign140_reports_record_no_current_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_140_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign140" in text
        assert "153/141" in text
        assert "1175" in text
        assert "Candidate49" in text
