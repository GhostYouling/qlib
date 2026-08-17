from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_158_schema_runtime_import_failure_20260815.json"
)
MATRIX = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_158_local_schema_field_coverage_matrix_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_158_local_schema_residual_audit_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_158/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_158_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v221_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign158_prevalue_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_158_terminal_report.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign158_matrix_matches_all_local_schemas_without_rows() -> None:
    matrix = _load(MATRIX)
    sources = matrix["source_field_matrix"]
    assert len(sources) == 17
    payload = []
    for source in sources:
        path = ROOT / source["path"]
        schema_names = pq.read_schema(path).names
        assert schema_names == list(source["fields"])
        payload.append(source["path"] + "|" + ",".join(schema_names))
        manifest_binding = source["manifest"]
        if manifest_binding is None:
            assert source["source"] == "margin_financing_top_flows_smoke"
            assert set(source["fields"].values()) == {"non_authoritative_duplicate"}
            continue
        manifest_path = ROOT / manifest_binding["path"]
        assert _sha(manifest_path) == manifest_binding["sha256"]
        assert _load(manifest_path)["sha256"] == source["data_sha256_from_manifest"]
    digest = hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()
    assert digest == matrix["inspection_contract"]["ordered_schema_sha256"]
    assert sum(len(source["fields"]) for source in sources) == 89
    assert len({field for source in sources for field in source["fields"]}) == 49
    assert (
        matrix["inspection_contract"]["parquet_row_group_or_column_value_read"] is False
    )


def test_campaign158_every_field_has_a_closed_or_nonalpha_disposition() -> None:
    matrix = _load(MATRIX)
    vocabulary = set(matrix["field_role_vocabulary"])
    roles = [
        role
        for source in matrix["source_field_matrix"]
        for role in source["fields"].values()
    ]
    assert set(roles) <= vocabulary
    assert len(roles) == 89
    summary = matrix["coverage_summary"]
    assert summary["schema_fields_without_a_disposition"] == 0
    assert (
        summary["genuinely_unconsumed_rankable_point_in_time_numeric_primitives"] == 0
    )
    assert summary["selected_candidate_count"] == 0
    assert (
        summary[
            "new_formula_direction_parameter_filter_subset_combination_or_model_frozen"
        ]
        is False
    )


def test_campaign158_residual_catalog_is_finite_and_stops_before_values() -> None:
    audit = _load(AUDIT)
    catalog = audit["finite_residual_catalog"]
    results = audit["gate_results"]
    assert len(catalog) == len(results) == 6
    assert [item["catalog_id"] for item in catalog] == [
        item["catalog_id"] for item in results
    ]
    assert all(item["hypothetical_formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    assert all(item["passed"] is False for item in results)
    assert audit["decision"]["selected_candidate_count"] == 0
    assert (
        audit["decision"][
            "predictive_ineffectiveness_of_unobserved_actual_disclosure_delay_established"
        ]
        is False
    )
    boundary = audit["research_boundary"]
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["candidate_or_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign158_runtime_failure_is_preserved_and_not_masked() -> None:
    failure = _load(FAILURE)
    assert failure["failure"]["exit_code"] == 1
    assert failure["failure"]["missing_module"] == "pyarrow"
    assert failure["failure"]["schema_opened_before_failure"] is False
    assert failure["failure"]["partial_output_or_target_write"] is False
    assert failure["safe_recovery"]["failed_exit_code_bypassed_or_masked"] is False


def test_campaign158_terminal_result_preserves_schema_only_semantics() -> None:
    terminal = _load(TERMINAL)
    classification = terminal["terminal_classification"]
    assert classification["terminal"] is True
    assert classification["parquet_files_schema_inspected"] == 17
    assert classification["ordered_field_occurrences_dispositioned"] == 89
    assert classification["unique_field_names_dispositioned"] == 49
    assert classification["schema_fields_without_a_disposition"] == 0
    assert classification["selected_candidate_count"] == 0
    assert classification["complete_factor_definition_created"] is False
    assert (
        classification[
            "parquet_row_source_response_candidate_comparator_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_campaign158_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1373
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign158",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = expected
    assert len(ledger["entries"]) == 7
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1380
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign158_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    comparisons = features.reconstruct_comparisons()
    assert len(definitions) == 157
    assert features._order_digest(definitions) == (
        "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )


def test_campaign158_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign158"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign158"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign158_terminal_report"]["sha256"] == _sha(REPORT)
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert len(_load(SIGNAL_LEDGER)["entries"]) == 0
    assert len(_load(EXECUTION_LEDGER)["entries"]) == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49"]["ledgers_changed"] is False
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False


def test_campaign158_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (FAILURE, MATRIX, AUDIT, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign158_reports_are_appended_once() -> None:
    heading = "## Campaign158 本地事件/基本面字段残余空间值前终止"
    assert "Campaign158" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert report_path.read_text(encoding="utf-8").count(heading) == 1


def test_campaign158_goal_remains_active_and_campaign159_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign158_scientific_decision_completed"] is True
    assert state["goal"]["campaign159_offline_scouting_authorized"] is True
    assert state["goal"]["campaign159_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
