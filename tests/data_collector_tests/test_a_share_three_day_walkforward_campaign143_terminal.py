from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_concept_scouting_20260814.json"
)
INVALID_FRONTIER_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_mechanism_contract_source_frontier_audit_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_mechanism_contract_source_frontier_audit_v2_20260814.json"
)
LEDGER_BASE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v1.json"
)
LEDGER_DELTA_1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v2.json"
)
INVALID_LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v3.json"
)
LEDGER_CORRECTION = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v4.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v5.json"
)
LEDGER_FINAL = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_143/research_attempt_ledger_v6.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_terminal_result_20260814.json"
)
TERMINAL_FINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_terminal_result_v2_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v187_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign143_prevalue_terminal.json"
)
VALIDATION_FINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_terminal_validation_20260814.json"
)
POLICY_FINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v188_20260814.json"
)
STATUS_FINAL = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign143_prevalue_terminal_v2.json"
)

FAILURES = [
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_zsh_nomatch_metadata_inventory_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_missing_predecessor_finalizer_probe_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_unretained_yielded_inventory_session_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_frontier_moneyflow_binding_typo_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_preledger_binding_scope_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_binding_error_report_shape_probe_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_over_narrow_failure_semantic_assertion_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_zsh_readonly_status_chain_hash_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_missing_binding_validator_cli_path_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_black_check_formatting_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_ledger_v3_predecessor_binding_typo_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_inline_python_binding_summary_syntax_failure_20260814.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_143_campaign142_mutable_report_lifecycle_test_failure_20260814.json",
]


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
            "campaign143",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign143_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c143_{index:02d}" for index in range(1, 7)
    ]
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert scouting["selection"]["genuinely_new_independent_mechanism_found"] is False
    boundary = scouting["research_boundary"]
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["campaign143_candidate_values_computed_or_read"] is False
    assert boundary["campaign143_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign143_preserves_library_and_numeric_orders() -> None:
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


def test_campaign143_effective_frontier_preserves_invalid_v1() -> None:
    invalid = _load(INVALID_FRONTIER_V1)
    frontier = _load(FRONTIER)
    assert _sha(INVALID_FRONTIER_V1) == (
        "e43782cdc957868f3bc72f7d234255254df0455e20097743cbd3ff4692e8d46b"
    )
    assert frontier["supersedes_without_rewriting"]["sha256"] == _sha(
        INVALID_FRONTIER_V1
    )
    assert frontier["supersedes_without_rewriting"]["invalid_binding_is_not_effective"]
    assert invalid["mandatory_prevalue_gate"]["proposals_passing_all_gates"] == 0
    content = frontier["effective_scientific_content"]
    assert (
        content["proposals_passing_contract_source_clock_and_independence_gates"] == 0
    )
    assert content["selected_candidate_count"] == 0
    assert content["complete_factor_definition_created"] is False
    assert frontier["effective_terminal_decision"][
        "campaign144_offline_scouting_allowed"
    ]


def test_campaign143_all_infrastructure_failures_are_explicit() -> None:
    records = [_load(path) for path in FAILURES]
    assert [record["attempt_id"] for record in records] == [
        f"campaign143_infrastructure_{index:03d}" for index in range(1, 14)
    ]
    assert all(
        record["kind"]
        == "a_share_three_day_walkforward_campaign143_infrastructure_failure"
        for record in records
    )
    assert records[0]["failure"]["process_exit_code"] == 1
    assert records[1]["failure"]["failed_component_exit_code"] == 2
    assert records[1]["failure"]["outer_shell_exit_code"] == 0
    assert records[2]["failure"]["terminal_process_exit_observed"] is False
    assert records[3]["failure"]["target_v1_modified_after_failure"] is False
    assert records[4]["failure"]["process_exit_code"] == 2
    assert records[5]["failure"]["process_exit_code"] == 5
    assert records[6]["failure"]["process_exit_code"] == 1
    assert records[7]["failure"]["outer_shell_exit_code"] == 0
    assert records[8]["failure"]["process_exit_code"] == 2
    assert records[9]["failure"]["process_exit_code"] == 1
    assert records[10]["failure"]["invalid_ledger_modified_after_detection"] is False
    assert records[11]["failure"]["process_exit_code"] == 1
    assert records[11]["failure"]["binding_validation_started"] is False
    assert records[12]["failure"]["pytest_passed"] == 11
    assert records[12]["failure"]["pytest_failed"] == 1
    assert all(
        record["research_boundary"]["provider_request_issued"] is False
        for record in records
    )
    assert all(
        record["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
        for record in records
    )


def test_campaign143_append_only_attempt_chain_and_accounting() -> None:
    ledger_base = _load(LEDGER_BASE)
    predecessor_tip = ledger_base["authoritative_predecessor"]["chain_tip_sha256"]
    genesis = hashlib.sha256(
        f"campaign143|genesis|{predecessor_tip}".encode("utf-8")
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
    assert ledger_base["entry_count"] == 14
    assert ledger_base["prevalue_concept_attempt_count"] == 6
    assert ledger_base["infrastructure_failure_attempt_count"] == 8

    ledger_delta_1 = _load(LEDGER_DELTA_1)
    assert ledger_delta_1["authoritative_predecessor"]["sha256"] == _sha(LEDGER_BASE)
    for entry in ledger_delta_1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger_delta_1["chain_tip_sha256"] == previous

    invalid_ledger_v3 = _load(INVALID_LEDGER_V3)
    assert invalid_ledger_v3["authoritative_predecessor"]["sha256"] != _sha(
        LEDGER_DELTA_1
    )

    ledger_correction = _load(LEDGER_CORRECTION)
    assert ledger_correction["authoritative_predecessor"]["sha256"] == _sha(
        LEDGER_DELTA_1
    )
    assert ledger_correction["supersedes_invalid_without_rewriting"]["sha256"] == _sha(
        INVALID_LEDGER_V3
    )
    for entry in ledger_correction["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger_correction["chain_tip_sha256"] == previous

    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_CORRECTION)
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous

    final_ledger = _load(LEDGER_FINAL)
    assert final_ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER)
    for entry in final_ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert final_ledger["chain_tip_sha256"] == previous
    assert final_ledger["effective_entry_count"] == 19
    assert final_ledger["effective_prevalue_concept_attempt_count"] == 6
    assert final_ledger["effective_infrastructure_failure_attempt_count"] == 13
    assert final_ledger["cumulative_historical_research_attempt_count"] == 1212
    assert final_ledger["cumulative_return_reading_development_trial_count"] == 313


def test_campaign143_bindings_policy_status_and_candidate49_isolation() -> None:
    for record in (
        SCOUTING,
        FRONTIER,
        LEDGER_BASE,
        LEDGER_DELTA_1,
        LEDGER_CORRECTION,
        LEDGER,
        LEDGER_FINAL,
        TERMINAL,
        TERMINAL_FINAL,
        POLICY,
    ):
        assert bindings.validate_record(record)["all_bindings_passed"] is True
    policy = _load(POLICY)
    status = _load(STATUS)
    assert policy["version"] == 187
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
    provisional_status_bindings = bindings.validate_record(STATUS)
    assert provisional_status_bindings["passed_binding_count"] == 6
    assert provisional_status_bindings["failed_binding_count"] == 3
    assert {
        item["json_pointer"] for item in provisional_status_bindings["failed_bindings"]
    } == {
        "/reports/campaign143_terminal_report",
        "/reports/current_research_report",
        "/reports/three_day_research_report",
    }

    final_records = (VALIDATION_FINAL, POLICY_FINAL, STATUS_FINAL)
    if all(path.exists() for path in final_records):
        for record in final_records:
            assert bindings.validate_record(record)["all_bindings_passed"] is True
        final_policy = _load(POLICY_FINAL)
        final_status = _load(STATUS_FINAL)
        assert final_policy["version"] == 188
        assert final_status["goal"]["status"] == "active"
        assert (
            final_status["effective_accounting"][
                "cumulative_historical_research_attempt_count"
            ]
            == 1212
        )


def test_campaign143_reports_record_no_current_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_143_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign143" in text
        assert "153/141" in text
        assert "1212" in text
        assert "Candidate49" in text
    assert (
        _load(TERMINAL)["research_boundary"][
            "current_scoring_selection_sizing_positions_or_orders_performed"
        ]
        is False
    )
