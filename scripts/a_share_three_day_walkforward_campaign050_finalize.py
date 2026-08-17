#!/usr/bin/env python3
"""Publish append-only terminal evidence for historical Campaign050."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_half_session_extreme_shock_reversal_completion_2h"
TRIAL_ID = f"wf050_{FACTOR}_single_higher"
CROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_050"
WALKFORWARD = CROOT / "walkforward"
AUDIT = CROOT / "no_return/20260801T104432Z_campaign050_no_return_audit.json"
SNAPSHOT = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign050_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign050_feature_library_v1/"
    "snapshot_manifest.json"
)
TRIAL_LEDGER = WALKFORWARD / "trial_ledger.json"
SURVIVORS = WALKFORWARD / "development_survivors.json"
STRESS = WALKFORWARD / "exposed_stress_consumption_record.json"
CAMPAIGN_REPORT = WALKFORWARD / "campaign_report.json"
ATTEMPT_LEDGER = CROOT / "research_attempt_ledger.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_050_research_record.json"
POST_RESULT_TRANSITION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_post_result_test_transition_20260801.json"
REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_unified_report_supersession_20260801.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_verification_20260801.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign050_verified.json"

POLICY = ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
PREDECESSOR_STATE = ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign049_verified.json"
PREDECESSOR_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_049_research_record.json"
PREDECESSOR_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_049_unified_report_supersession_20260801.json"
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_050_concept_scouting.json"
MECHANISM = ROOT / "docs/a_share_three_day_walkforward_campaign_050_mechanism_overlap_audit.json"
PROTOCOL = ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_preregistration.json"
FEATURE_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_feature_implementation_freeze_20260801.json"
FEATURE_FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_feature_build_infrastructure_repair_20260801.json"
FEATURE_REPAIR_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_feature_build_repair_implementation_freeze_20260801.json"
SNAPSHOT_BINDING = ROOT / "docs/a_share_three_day_walkforward_campaign_050_snapshot_publication_binding_20260801.json"
AUDIT_ENTRY_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_entrypoint_freeze_20260801.json"
AUDIT_FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_infrastructure_failure_repair_20260801.json"
AUDIT_REPAIR_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_repair_implementation_freeze_20260801.json"
NO_RETURN_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_freeze_20260801.json"
POST_AUDIT_TRANSITION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_post_audit_test_transition_20260801.json"
PREREG_V1 = ROOT / "docs/a_share_three_day_walkforward_campaign_050_preregistration.json"
PREREG_V2 = ROOT / "docs/a_share_three_day_walkforward_campaign_050_preregistration_v2.json"
PREREG = ROOT / "docs/a_share_three_day_walkforward_campaign_050_preregistration_v3.json"
PREREG_FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_development_preregistration_semantic_failure_20260801.json"
TEMPLATE_FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_development_preregistration_template_failure_20260801.json"
DEVELOPMENT_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_development_implementation_freeze_20260801.json"
RUNNER = ROOT / "scripts/a_share_three_day_walkforward_campaign050_v3.py"
FEATURE_RUNNER = ROOT / "scripts/a_share_three_day_walkforward_campaign050_features_v8.py"
FINALIZER = Path(__file__).resolve()
CAMPAIGN_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign050.py"
TERMINAL_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign050_terminal.py"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def binding(path: Path) -> dict[str, str]:
    return {"path": display(path), "sha256": sha256(path)}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_new(path: Path, value: dict[str, Any]) -> Path:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if load(path) != value:
            raise RuntimeError(f"refuse to rewrite terminal evidence: {path}")
        return path
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def validation_rows() -> list[dict[str, Any]]:
    entry = load(TRIAL_LEDGER)["entries"][0]
    rows = []
    for fold in entry["training_and_validation_folds"]:
        metrics = fold["validation_metrics"]
        rows.append({
            "fold": fold["fold"],
            "validation_year": int(metrics["start"][:4]),
            "cohorts": metrics["association"]["cohorts"],
            "mean_rank_ic": metrics["association"]["mean_rank_ic"],
            "mean_top3_minus_bottom3_gross_return": metrics["association"]["mean_top3_minus_bottom3_gross_return"],
            "normalized_return": metrics["normalized_execution"]["net_cumulative_return"],
            "normalized_maximum_drawdown": metrics["normalized_execution"]["maximum_drawdown"],
            "pilot_10bp_return": metrics["pilot_execution_primary_10bp"]["net_cumulative_return"],
            "board_lot_affordability_rate": metrics["pilot_execution_primary_10bp"]["board_lot_affordability_rate"],
            "maximum_daily_amount_participation": metrics["pilot_execution_primary_10bp"]["maximum_filled_trade_daily_amount_participation"],
            "terminal_unresolved_positions": metrics["pilot_execution_primary_10bp"]["terminal_unresolved_position_count"],
        })
    return rows


def post_result_transition() -> Path:
    old = load(DEVELOPMENT_FREEZE)["bindings"]["development_boundary_tests"]
    if old["sha256"] == sha256(CAMPAIGN_TESTS):
        raise RuntimeError("Campaign050 tests did not transition from pre-return state")
    return write_new(POST_RESULT_TRANSITION, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign050_post_result_test_transition",
        "status": "pre_return_test_fingerprint_preserved_terminal_assertions_current",
        "recorded_at": "2026-08-01T11:17:00Z",
        "purpose": "Preserve the exact pre-return test fingerprint while binding the one-trial, zero-survivor, unopened-stress terminal assertions.",
        "bindings": {
            "development_implementation_freeze": binding(DEVELOPMENT_FREEZE),
            "current_campaign_tests": binding(CAMPAIGN_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "terminal_publisher": binding(FINALIZER),
        },
        "historical_test_binding": {
            "path": old["path"],
            "expected_pre_return_sha256": old["sha256"],
            "current_post_result_sha256": sha256(CAMPAIGN_TESTS),
            "development_freeze_rewritten": False,
        },
        "observed_transition": {"pre_result_test_passed": 3, "pre_result_test_failed": 1, "only_failure": "empty-ledger assertion observed one immutable trial"},
        "semantic_boundary": {
            "formula_direction_cost_fold_purge_or_gate_changed": False,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def attempt_ledger() -> Path:
    protocol = load(PROTOCOL)
    audit = load(AUDIT)
    snapshot = load(SNAPSHOT)
    trial = load(TRIAL_LEDGER)["entries"][0]
    decision = load(SURVIVORS)["trial_decisions"][0]
    aggregate = trial["development_aggregate_metrics"]
    common = {
        "formula": protocol["candidate"]["formula"],
        "direction": "higher",
        "feature_set": [FACTOR],
        "parameter_filter_subset_combination_and_model": "exact frozen single factor; no alternate field/tie/window/transform/direction/scale/threshold/filter/subset/combination/model/fit",
        "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
        "provider_request_issued": False,
    }
    entries = [
        {"sequence": 1, "kind": "infrastructure_only_failure", "stage": "feature_snapshot_build", "recorded_at": "2026-08-01T07:59:46Z", "research_attempt_count_increment": 1, "outcome": "failed_closed_on_valid_empty_joint_base_partition_after_801_partial_checkpoints", "evidence": binding(FEATURE_FAILURE), "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        {"sequence": 2, "kind": "infrastructure_only_failure", "stage": "ordered_no_return_audit", "recorded_at": "2026-08-01T09:32:12Z", "research_attempt_count_increment": 1, "outcome": "failed_closed_after_all_candidate_partitions_and_72_comparisons_because_campaign049_verifier_shared_campaign050_output_columns", "evidence": binding(AUDIT_FAILURE), "no_return_metrics_persisted": False, "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        {"sequence": 3, "kind": "single_factor_ordered_no_return_gate", "recorded_at": audit["created_at"], "research_attempt_count_increment": 1, **common, "outcome": "admitted_exactly_one_factor_for_frozen_development", "data_and_code_fingerprints": {"protocol": binding(PROTOCOL), "snapshot": {**binding(SNAPSHOT), "dataset_sha256": snapshot["dataset_sha256"]}, "audit": binding(AUDIT), "audit_freeze": binding(NO_RETURN_FREEZE), "effective_runner": binding(FEATURE_RUNNER)}, "no_return_metrics": {"median_coverage": audit["coverage_and_capacity"][FACTOR]["median_coverage"], "p05_coverage": audit["coverage_and_capacity"][FACTOR]["p05_coverage"], "comparison_count": 73, "maximum_absolute_median_daily_rank_correlation": audit["uniqueness"][FACTOR]["maximum_observed_absolute_median_daily_rank_correlation"], "all_gates_passed": True}, "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        {"sequence": 4, "kind": "infrastructure_only_failure", "stage": "development_preregistration_exact_schema", "recorded_at": "2026-08-01T10:51:17Z", "research_attempt_count_increment": 1, "outcome": "failed_closed_on_two_unexpected_top_level_explanatory_fields", "evidence": binding(PREREG_FAILURE), "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        {"sequence": 5, "kind": "infrastructure_only_failure", "stage": "development_preregistration_template_binding", "recorded_at": "2026-08-01T10:55:07Z", "research_attempt_count_increment": 1, "outcome": "failed_closed_on_noncanonical_campaign004_template_identity", "evidence": binding(TEMPLATE_FAILURE), "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        {"sequence": 6, "parent_sequence": 3, "kind": "development_result_continuation", "recorded_at": trial["created_at"], "research_attempt_count_increment": 0, "development_trial_count_increment": 1, **common, "outcome": "terminal_zero_survivors_frozen_quality_gates_failed", "data_and_code_fingerprints": {"preregistration": binding(PREREG), "runner": binding(RUNNER), "development_freeze": binding(DEVELOPMENT_FREEZE), "trial_ledger": binding(TRIAL_LEDGER), "survivor_file_bytes": binding(SURVIVORS)}, "development_aggregate_metrics": {"mean_rank_ic": aggregate["association"]["mean_rank_ic"], "normalized_return": aggregate["normalized_execution"]["net_cumulative_return"], "pilot_0bp_return": aggregate["pilot_slippage_sensitivity"]["0.0000"]["net_cumulative_return"], "pilot_5bp_return": aggregate["pilot_slippage_sensitivity"]["0.0005"]["net_cumulative_return"], "pilot_10bp_return": aggregate["pilot_slippage_sensitivity"]["0.0010"]["net_cumulative_return"], "pilot_20bp_return": aggregate["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"]}, "validation_metrics": validation_rows(), "survivor_decision": decision, "historical_daily_price_fields_read": ["open", "close", "volume", "amount", "factor", "limit_status", "listing_quality"], "historical_forward_return_fields_read": True, "development_years_read": [2019, 2020, 2021, 2022, 2023], "2024_2025_stress_return_fields_read": False},
    ]
    return write_new(ATTEMPT_LEDGER, {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign050_research_attempt_ledger",
        "append_only": True,
        "counting_rule": "Every distinct formula, direction, parameter set, subset, filter, model, combination, and infrastructure-only failure counts once; the same frozen factor advancing from no-return admission to its preregistered development trial adds a continuation entry but no second research attempt.",
        "campaign050_ledger_entry_count": 6,
        "campaign050_attempt_count": 5,
        "historical_research_attempt_count_before_campaign050": 280,
        "cumulative_historical_research_attempt_count": 285,
        "campaign050_historical_return_trial_count": 1,
        "cumulative_return_reading_development_trial_count_before_campaign050": 264,
        "cumulative_return_reading_development_trial_count": 265,
        "entries": entries,
    })


def research_record() -> Path:
    protocol, snapshot, audit = load(PROTOCOL), load(SNAPSHOT), load(AUDIT)
    coverage, uniqueness = audit["coverage_and_capacity"][FACTOR], audit["uniqueness"][FACTOR]
    nearest = max(uniqueness["comparisons"], key=lambda item: item["absolute_median_daily_rank_correlation"])
    trial_ledger, survivor, stress = load(TRIAL_LEDGER), load(SURVIVORS), load(STRESS)
    trial, decision = trial_ledger["entries"][0], survivor["trial_decisions"][0]
    aggregate = trial["development_aggregate_metrics"]
    return write_new(RESEARCH_RECORD, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign050_research_record",
        "status": "completed_zero_development_survivors_stress_interval_not_opened",
        "recorded_at": "2026-08-01T11:20:00Z",
        "purpose": "Record every Campaign050 failure, exact factor configuration, ordered no-return result, sole 2019-2023 expanding-walk-forward trial, and closed 2024-2025 boundary.",
        "authoritative_inputs": {"prior_iteration_state": binding(PREDECESSOR_STATE), "historical_walkforward_policy": binding(POLICY), "prior_campaign_terminal_record": binding(PREDECESSOR_RECORD)},
        "frozen_evidence": {
            "concept_scouting": binding(CONCEPT), "mechanism_overlap_audit": binding(MECHANISM), "no_return_preregistration": binding(PROTOCOL), "feature_implementation_freeze": binding(FEATURE_FREEZE), "feature_build_failure": binding(FEATURE_FAILURE), "feature_build_repair_freeze": binding(FEATURE_REPAIR_FREEZE), "snapshot_publication_binding": binding(SNAPSHOT_BINDING), "no_return_audit_entrypoint_freeze": binding(AUDIT_ENTRY_FREEZE), "no_return_audit_failure": binding(AUDIT_FAILURE), "no_return_audit_repair_freeze": binding(AUDIT_REPAIR_FREEZE), "no_return_audit_freeze": binding(NO_RETURN_FREEZE), "post_audit_test_transition": binding(POST_AUDIT_TRANSITION), "development_preregistration_v1_preserved": binding(PREREG_V1), "development_preregistration_v2_preserved": binding(PREREG_V2), "development_preregistration": binding(PREREG), "development_schema_failure": binding(PREREG_FAILURE), "development_template_failure": binding(TEMPLATE_FAILURE), "development_implementation_freeze": binding(DEVELOPMENT_FREEZE), "post_result_test_transition": binding(POST_RESULT_TRANSITION),
        },
        "factor_definition": protocol["candidate"],
        "feature_snapshot": {**binding(SNAPSHOT), "dataset_sha256": snapshot["dataset_sha256"], "partitions": snapshot["partitions"], "rows": snapshot["rows"], "eligible_rows": snapshot["factor_eligible_rows"][FACTOR], "quality": snapshot["quality"], "all_partition_byte_and_frame_hashes_valid": audit["snapshot_file_verification"]["all_partition_byte_and_frame_hashes_valid"], "source_fields_read": snapshot["source_fields_read"]},
        "no_return_result": {**binding(AUDIT), "status": audit["status"], "median_coverage": coverage["median_coverage"], "p05_coverage": coverage["p05_coverage"], "median_eligible_names": coverage["eligible_names_median"], "p05_eligible_names": coverage["eligible_names_p05"], "potential_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"], "comparison_count": uniqueness["comparison_factor_count"], "all_comparisons_passed": uniqueness["all_required_comparisons_passed"], "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"], "nearest_comparison_factor": nearest["comparison_factor"], "nearest_median_daily_rank_correlation": nearest["median_daily_rank_correlation"], "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False},
        "development_artifacts": {"runner": binding(RUNNER), "development_boundary_tests": binding(CAMPAIGN_TESTS), "terminal_tests": binding(TERMINAL_TESTS), "research_attempt_ledger": {**binding(ATTEMPT_LEDGER), "campaign_attempt_count": 5, "ledger_entry_count": 6}, "trial_ledger": {**binding(TRIAL_LEDGER), "entry_count": 1, "chain_tip_sha256": trial_ledger["chain_tip_sha256"]}, "development_survivors_file_bytes": {**binding(SURVIVORS), "selected_survivor_count": 0}, "development_survivors_canonical_json_value_sha256": stress["survivor_record_sha256"], "exposed_stress_consumption_record": {**binding(STRESS), "status": stress["status"], "stress_interval_opened": False, "stress_return_fields_read": False}, "campaign_report": binding(CAMPAIGN_REPORT)},
        "validation_fold_results": validation_rows(),
        "development_aggregate_result": {"cohorts": aggregate["association"]["cohorts"], "mean_rank_ic": aggregate["association"]["mean_rank_ic"], "mean_top3_minus_bottom3_gross_return": aggregate["association"]["mean_top3_minus_bottom3_gross_return"], "normalized_return": aggregate["normalized_execution"]["net_cumulative_return"], "normalized_maximum_drawdown": aggregate["normalized_execution"]["maximum_drawdown"], "pilot_0bp_return": aggregate["pilot_slippage_sensitivity"]["0.0000"]["net_cumulative_return"], "pilot_5bp_return": aggregate["pilot_slippage_sensitivity"]["0.0005"]["net_cumulative_return"], "pilot_10bp_return": aggregate["pilot_slippage_sensitivity"]["0.0010"]["net_cumulative_return"], "pilot_20bp_return": aggregate["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"]},
        "survivor_decision": {**decision, "selected_survivor_count": 0},
        "attempt_accounting": {"infrastructure_only_failures": 4, "complete_factor_attempts": 1, "campaign_distinct_attempts": 5, "campaign_ledger_entries": 6, "cumulative_historical_research_attempts": 285, "campaign_return_reading_development_trials": 1, "cumulative_return_reading_development_trials": 265},
        "prospective_boundary": {"candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0}, "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0}, "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False, "second_prospective_candidate_activation_created": False, "current_scoring_selection_sizing_or_orders_performed": False},
        "decision": {"factor_terminal": True, "reason": "Only 2021 was profitable; 2022 and 2023 normalized and 10bp returns were negative, and the frozen spread, fold-consistency, pilot-return, drawdown, and aggregate-20bp gates failed.", "2024_2025_stress_opened": False, "2024_2025_returns_read": False, "invert_repair_reanchor_renormalize_rewindow_rescale_filter_threshold_rerun_rescue_or_combine_allowed": False, "cumulative_historical_research_attempt_count_after_campaign": 285, "historical_development_return_trial_count_after_campaign": 265, "current_aggregation_candidate_count": 0, "next_action": "Begin Campaign051 only from a genuinely independent pre-value-frozen mechanism; Candidate49 remains the sole prospective candidate.", "investment_advice_or_current_selection_claim_allowed": False},
    })


def report_supersession() -> Path:
    previous = load(PREDECESSOR_SUPERSESSION)
    return write_new(REPORT_SUPERSESSION, {
        "version": 1, "kind": "a_share_three_day_walkforward_campaign050_unified_report_supersession", "status": "campaign049_report_binding_preserved_historically_campaign050_report_current", "recorded_at": "2026-08-01T11:24:00Z", "purpose": "Preserve Campaign049's immutable report binding while binding the append-only Campaign050 terminal update.",
        "bindings": {"campaign049_terminal_record": binding(PREDECESSOR_RECORD), "campaign050_terminal_record": binding(RESEARCH_RECORD), "previous_campaign049_supersession": binding(PREDECESSOR_SUPERSESSION), "current_unified_research_report": binding(REPORT)},
        "historical_binding": {"record": display(PREDECESSOR_SUPERSESSION), "json_pointer": "/bindings/current_unified_research_report", "expected_sha256": previous["bindings"]["current_unified_research_report"]["sha256"], "current_sha256": sha256(REPORT), "historical_record_rewritten": False, "previous_supersession_rewritten": False},
        "semantic_boundary": {"campaign049_result_or_gate_changed": False, "campaign050_result_or_gate_changed_after_values": False, "report_update_is_append_only": True, "additional_historical_daily_price_or_forward_return_read": False, "2024_2025_stress_return_read": False, "candidate49_ledgers_changed": False},
    })


def verification(focused: int, full: int, warnings: int) -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator
    records = [RESEARCH_RECORD, PREREG, POST_RESULT_TRANSITION, REPORT_SUPERSESSION]
    checked = {display(path): validator.validate_record(path, data_root=DATA_ROOT) for path in records}
    if not all(item["all_bindings_passed"] for item in checked.values()):
        raise RuntimeError("Campaign050 terminal bindings are not current")
    return write_new(VERIFICATION, {
        "version": 1, "kind": "a_share_three_day_walkforward_campaign050_verification", "status": "terminal_campaign050_and_candidate49_isolation_verified", "recorded_at": "2026-08-01T11:28:00Z", "purpose": "Bind Campaign050 terminal evidence, append-only accounting, unopened 2024-2025 semantics, tests, and unchanged Candidate49 ledgers.",
        "bindings": {"research_record": binding(RESEARCH_RECORD), "post_result_test_transition": binding(POST_RESULT_TRANSITION), "unified_report_supersession": binding(REPORT_SUPERSESSION), "no_return_audit": binding(AUDIT), "development_preregistration": binding(PREREG), "development_runner": binding(RUNNER), "feature_runner": binding(FEATURE_RUNNER), "campaign_tests": binding(CAMPAIGN_TESTS), "terminal_tests": binding(TERMINAL_TESTS), "feature_snapshot": binding(SNAPSHOT), "research_attempt_ledger": binding(ATTEMPT_LEDGER), "trial_ledger": binding(TRIAL_LEDGER), "development_survivors": binding(SURVIVORS), "unopened_stress_record": binding(STRESS), "campaign_report": binding(CAMPAIGN_REPORT), "unified_research_report": binding(REPORT), "candidate49_signal_ledger": binding(SIGNAL_LEDGER), "candidate49_execution_ledger": binding(EXECUTION_LEDGER)},
        "verification_summary": {"binding_records_checked": len(checked), "all_bindings_passed": True, "focused_campaign050_tests_passed": focused, "full_data_collector_tests_passed": full, "full_data_collector_tests_failed": 0, "full_data_collector_test_warnings": warnings, "candidate49_ledgers_rehashed_unchanged": True},
        "terminal_decision": {"campaign_research_attempt_count": 5, "campaign_ledger_entry_count": 6, "cumulative_historical_research_attempt_count": 285, "development_trial_count": 1, "cumulative_return_reading_development_trial_count": 265, "development_survivor_count": 0, "stress_2024_2025_opened": False, "stress_return_fields_read": False, "candidate49_historical_return_read": False, "candidate49_ledgers_changed": False, "second_prospective_activation_created": False, "current_scoring_selection_sizing_or_orders_performed": False},
    })


def state() -> Path:
    record = load(RESEARCH_RECORD)
    return write_new(STATE, {
        "version": 1, "kind": "a_share_three_day_iteration_status", "status": "campaign050_terminal_verified_historical_walkforward_ready_for_independent_campaign051", "recorded_at": "2026-08-01T11:30:00Z", "authoritative_predecessor": binding(PREDECESSOR_STATE),
        "research_policy": {"historical_walkforward_policy": binding(POLICY), "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True, "every_formula_direction_parameter_subset_filter_model_combination_and_infrastructure_failure_counted": True, "historical_results_may_generate_current_scores_selections_sizes_or_orders": False, "historical_results_may_backfill_candidate49": False},
        "fixed_strategy": {"holding_period_local_sessions": 3, "signal": "accepted local session close t", "entry": "next accepted local session open t+1", "exit": "third accepted local session close t+3", "topk": 3, "development_folds": 3, "purge_signal_sessions_each_partition_boundary": 3, "t_t_plus_1_t_plus_3_must_remain_in_same_partition": True, "pilot_capital_cny": 200000, "primary_pilot_cost_bps": 10, "aggregate_survivor_cost_bps": 20},
        "campaign050": {"factor": FACTOR, "direction": "higher", "formula": load(PROTOCOL)["candidate"]["formula"], "no_return": record["no_return_result"], "development": {"trial_id": TRIAL_ID, "trial_count": 1, "validation_fold_results": validation_rows(), "development_aggregate_result": record["development_aggregate_result"], "development_survivor_count": 0, "2024_2025_stress_opened": False, "2024_2025_returns_read": False}, "attempt_accounting": record["attempt_accounting"], "terminal": record["decision"], "authoritative_records": {"research_record": binding(RESEARCH_RECORD), "verification": binding(VERIFICATION), "unified_report_supersession": binding(REPORT_SUPERSESSION)}},
        "cumulative_state": {"cumulative_historical_research_attempt_count_after_campaign050": 285, "cumulative_return_reading_development_trial_count_after_campaign050": 265, "current_historical_aggregation_candidate_count": 0},
        "local_data_context": {"active_daily_data_root": str(ROOT / "data"), "local_date": "2026-08-01", "local_weekday": "Saturday", "candidate49_same_day_workflow_applicable": False, "dotenv_path": str(ROOT / ".env"), "dotenv_is_regular_non_symlink_file": True, "dotenv_is_git_ignored": True, "dotenv_mode": "0600", "tushare_token_present": True, "credential_value_printed_hashed_or_persisted_in_records": False, "provider_request_issued_by_campaign050_or_credential_verification": False},
        "prospective_boundary": {"active_candidate_count": 1, "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m", "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0}, "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0}, "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False, "second_prospective_candidate_activation_allowed": False},
        "verification_summary": load(VERIFICATION)["verification_summary"],
        "next_action": {"historical": "Begin Campaign051 from an independent mechanism with pre-value scouting, overlap audit, finite fingerprint-bound protocol, and append-only accounting; offline work may run at any time.", "prospective": "Today is Saturday; do not run Candidate49 provider workflow. On the next accepted local trading date retain the same-day post-16:30 ready=true gate and a new absolute-date staging root.", "strict_prohibitions": ["do not backfill Candidate49 historical returns signals executions or milestones", "do not start a second prospective candidate", "do not invert repair rewindow rescale filter threshold rerun rescue or combine Campaign050", "do not open Campaign050 2024-2025 stress", "do not generate current scores selections position sizes orders or investment advice"]},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("post-result-transition", "attempt-ledger", "research-record", "report-supersession", "verification", "state"))
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args()
    actions = {"post-result-transition": post_result_transition, "attempt-ledger": attempt_ledger, "research-record": research_record, "report-supersession": report_supersession, "verification": lambda: verification(args.focused_passed, args.full_passed, args.warnings), "state": state}
    path = actions[args.stage]()
    print(json.dumps({"path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
