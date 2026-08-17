from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_mechanism_source_frontier_audit_20260814.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_safe_credential_inspection_shell_parse_failure_20260814.json"
)
FAILURE_2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_pytest_collection_missing_compatibility_path_failure_20260814.json"
)
FAILURE_3 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_unified_report_append_patch_context_failure_20260814.json"
)
FAILURE_4 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_campaign141_mutable_report_binding_compatibility_failure_20260814.json"
)
LEDGER_BASE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_142/research_attempt_ledger_v2.json"
)
LEDGER_DELTA_1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_142/research_attempt_ledger_v3.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_142/research_attempt_ledger_v4.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_142_terminal_result_v4_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v186_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign142_prevalue_terminal_v4.json"
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
            "campaign142",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign142_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c142_{index:02d}" for index in range(1, 7)
    ]
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert scouting["selection"]["genuinely_new_independent_mechanism_found"] is False
    boundary = scouting["research_boundary"]
    assert boundary["parquet_schema_only_inspection_performed"] is True
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign142_preserves_complete_and_numeric_orders() -> None:
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


def test_campaign142_attempt_chain_and_failure_semantics() -> None:
    failure = _load(FAILURE)
    assert failure["failure"]["process_exit_code"] == 1
    assert failure["failure"]["shell_body_started"] is False
    assert failure["failure"]["failed_exit_code_bypassed"] is False
    assert failure["safe_retry"]["secret_printed_hashed_logged_or_persisted"] is False

    failure_2 = _load(FAILURE_2)
    assert failure_2["failure"]["process_exit_code"] == 4
    assert failure_2["failure"]["failed_exit_code_bypassed"] is False
    assert (
        failure_2["completed_checks_before_failure"]["pytest_tests_collected_or_run"]
        == 0
    )

    failure_3 = _load(FAILURE_3)
    assert failure_3["failure"]["process_exit_code"] == 1
    assert failure_3["failure"]["partial_write_performed"] is False
    assert failure_3["failure"]["failed_exit_code_bypassed"] is False

    failure_4 = _load(FAILURE_4)
    assert failure_4["failure"]["process_exit_code"] == 1
    assert failure_4["failure"]["pytest_passed"] == 9
    assert failure_4["failure"]["pytest_failed"] == 1
    assert failure_4["safe_retry"]["binding_validator_weakened_or_modified"] is False

    ledger_base = _load(LEDGER_BASE)
    predecessor_tip = ledger_base["authoritative_predecessor"]["chain_tip_sha256"]
    genesis = hashlib.sha256(
        f"campaign142|genesis|{predecessor_tip}".encode("utf-8")
    ).hexdigest()
    assert ledger_base["chain_genesis"] == genesis
    previous = genesis
    for entry in ledger_base["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_source_value_read"] is False
        assert entry["comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger_base["chain_tip_sha256"] == previous
    assert ledger_base["entry_count"] == 8
    assert ledger_base["prevalue_concept_attempt_count"] == 6
    assert ledger_base["infrastructure_failure_attempt_count"] == 2
    assert ledger_base["cumulative_historical_research_attempt_count"] == 1191

    ledger_delta_1 = _load(LEDGER_DELTA_1)
    assert ledger_delta_1["authoritative_predecessor"]["sha256"] == _sha(LEDGER_BASE)
    for entry in ledger_delta_1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger_delta_1["chain_tip_sha256"] == previous

    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_DELTA_1)
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["effective_entry_count"] == 10
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 4
    assert ledger["cumulative_historical_research_attempt_count"] == 1193
    assert ledger["cumulative_return_reading_development_trial_count"] == 313


def test_campaign142_bindings_policy_status_and_candidate49_isolation() -> None:
    for record in (
        SCOUTING,
        FRONTIER,
        LEDGER_BASE,
        LEDGER_DELTA_1,
        LEDGER,
        TERMINAL,
        POLICY,
    ):
        assert bindings.validate_record(record)["all_bindings_passed"] is True
    status_bindings = bindings.validate_record(STATUS)
    assert status_bindings["passed_binding_count"] == 7
    assert status_bindings["failed_binding_count"] == 2
    assert {item["json_pointer"] for item in status_bindings["failed_bindings"]} == {
        "/reports/current_research_report",
        "/reports/three_day_research_report",
    }
    frontier = _load(FRONTIER)
    assert frontier["mandatory_prevalue_gate"]["proposals_passing_all_gates"] == 0
    assert (
        frontier["terminal_decision"]["campaign142_complete_factor_definition_created"]
        is False
    )
    policy = _load(POLICY)
    status = _load(STATUS)
    assert policy["version"] == 186
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


def test_campaign142_reports_record_no_current_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_142_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign142" in text
        assert "153/141" in text
        assert "1193" in text
        assert "Candidate49" in text
