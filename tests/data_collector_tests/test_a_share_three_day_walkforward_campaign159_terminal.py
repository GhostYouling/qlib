from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_159_remaining_local_source_schema_inventory_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_159_remaining_local_source_residual_audit_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_159/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_159_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v222_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign159_prevalue_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_159_terminal_report.md"
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


def test_campaign159_inventory_is_finite_unique_and_schema_only() -> None:
    inventory = _load(INVENTORY)
    families = inventory["source_families"]
    family_names = [item["family"] for item in families]
    assert len(families) == len(set(family_names)) == 18
    inspection = inventory["inspection_contract"]
    assert inspection["repository_daily_parquet_file_count"] == 5451
    assert inspection["repository_rich_parquet_file_count"] == 226
    assert inspection["accepted_full_minute_partition_count"] == 33015
    assert inspection["parquet_row_group_or_column_value_read"] is False
    assert inspection["source_file_bytes_hashed_during_campaign159"] is False
    assert inspection["candidate_comparator_price_or_return_value_read"] is False
    summary = inventory["inventory_summary"]
    assert summary["source_families_reviewed"] == 18
    assert (
        summary[
            "accepted_full_history_families_with_unconsumed_contract_permitted_independent_primitive"
        ]
        == 0
    )
    assert summary["selected_candidate_count"] == 0
    assert summary["new_source_contract_or_formula_frozen"] is False


def test_campaign159_inventory_dispositions_cover_remaining_source_kinds() -> None:
    families = {item["family"]: item for item in _load(INVENTORY)["source_families"]}
    assert families["canonical_daily_price_volume_basis"]["source_status"] == (
        "accepted_active_baostock_daily_root"
    )
    assert families["accepted_full_tushare_one_minute_ohlcva"]["scope"] == (
        "33015 immutable 2019-2025 partitions"
    )
    assert families["tushare_classified_moneyflow_full_history"]["source_status"] == (
        "accepted_full_history_terminal_factor"
    )
    assert families["tushare_cash_conversion_acceptance_only"]["source_status"] == (
        "full_history_terminal_source_failure"
    )
    assert (
        families["derived_features_reconciliation_failures_and_experiment_outputs"][
            "source_status"
        ]
        == "derived_or_failure_evidence_not_new_raw_source"
    )


def test_campaign159_terminal_evidence_registry_is_fully_bound() -> None:
    inventory = _load(INVENTORY)
    registry = inventory["terminal_evidence_registry"]
    assert len(registry) == 14
    assert len({item["path"] for item in registry}) == 14
    for binding in registry:
        assert _sha(ROOT / binding["path"]) == binding["sha256"]


def test_campaign159_residual_catalog_is_finite_and_stops_before_values() -> None:
    audit = _load(AUDIT)
    catalog = audit["finite_residual_catalog"]
    results = audit["gate_results"]
    assert len(catalog) == len(results) == 6
    assert [item["catalog_id"] for item in catalog] == [
        item["catalog_id"] for item in results
    ]
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in catalog
    )
    assert all(item["passed"] is False for item in results)
    assert (
        sum(
            item["classification"] == "source_admission_failure_not_factor_failure"
            for item in catalog
        )
        == 1
    )
    decision = audit["decision"]
    assert decision["selected_candidate_count"] == 0
    assert decision["source_admission_failures_not_factor_failures"] == 1
    assert decision["terminal_contract_transform_or_artifact_rejections"] == 5
    boundary = audit["research_boundary"]
    assert boundary["parquet_rows_or_column_values_read"] is False
    assert boundary["candidate_or_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign159_terminal_result_and_accounting() -> None:
    terminal = _load(TERMINAL)
    classification = terminal["terminal_classification"]
    assert classification["terminal"] is True
    assert classification["source_families_reviewed"] == 18
    assert classification["finite_residual_routes_reviewed"] == 6
    assert classification["selected_candidate_count"] == 0
    assert classification["source_admission_failures_not_factor_failures"] == 1
    assert classification["terminal_contract_transform_or_artifact_rejections"] == 5
    assert classification["complete_factor_definition_created"] is False
    assert (
        classification[
            "parquet_row_source_response_candidate_comparator_daily_price_or_forward_return_values_read"
        ]
        is False
    )
    accounting = terminal["effective_accounting"]
    assert accounting["campaign159_attempt_count"] == 6
    assert accounting["campaign159_infrastructure_failure_count"] == 0
    assert accounting["cumulative_historical_research_attempt_count"] == 1386
    assert accounting["cumulative_return_reading_development_trial_count"] == 314


def test_campaign159_attempt_chain_and_predecessor() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1380
    assert predecessor["cumulative_return_reading_development_trial_count"] == 314
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign159",
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
    assert len(ledger["entries"]) == 6
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1386
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign159_preserves_library_orders() -> None:
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
    policy = _load(POLICY)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 157
    )
    assert policy["complete_historical_feature_library"]["unchanged_from_v221"] is True
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v221"] is True


def test_campaign159_publication_bindings_and_candidate49_boundary() -> None:
    inventory = _load(INVENTORY)
    audit = _load(AUDIT)
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (inventory, audit, terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign159"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign159"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign159_terminal_report"]["sha256"] == _sha(REPORT)
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


def test_campaign159_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (INVENTORY, AUDIT, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign159_reports_are_appended_once() -> None:
    heading = "## Campaign159 剩余本地来源合同残余空间值前终止"
    assert "Campaign159" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert report_path.read_text(encoding="utf-8").count(heading) == 1


def test_campaign159_goal_remains_active_and_campaign160_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign159_scientific_decision_completed"] is True
    assert state["goal"]["campaign160_offline_scouting_authorized"] is True
    assert state["goal"]["campaign160_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
    assert state["research_boundary"]["stress_2024_2025_returns_opened"] is False
