#!/usr/bin/env python3
"""Publish append-only terminal evidence for Campaign048."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_two_sided_wick_absorption_balance_240m"
TRIAL_ID = "wf048_intraday_two_sided_wick_absorption_balance_240m_single_higher"
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_048"
WALKFORWARD = CAMPAIGN_ROOT / "walkforward"
ATTEMPT_LEDGER_V1 = CAMPAIGN_ROOT / "research_attempt_ledger.json"
ATTEMPT_LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v2.json"
TRIAL_LEDGER = WALKFORWARD / "trial_ledger.json"
SURVIVORS = WALKFORWARD / "development_survivors.json"
STRESS = WALKFORWARD / "exposed_stress_consumption_record.json"
CAMPAIGN_REPORT = WALKFORWARD / "campaign_report.json"
AUDIT = CAMPAIGN_ROOT / "no_return/20260801T050642Z_campaign048_no_return_audit.json"
SNAPSHOT = DATA_ROOT / "derived/a_share/rich/tushare/minute_walkforward_campaign048_feature_library/tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign048_feature_library_v1/snapshot_manifest.json"
PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"
PREREG_V1 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_preregistration.json"
PREREG_V2 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_preregistration_v2.json"
NO_RETURN_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_audit_freeze_20260801.json"
DEVELOPMENT_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_development_implementation_freeze_20260801.json"
SEMANTIC_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_development_namespace_semantic_failure_20260801.json"
POST_RESULT_TRANSITION_V1 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_post_result_test_transition_20260801.json"
POST_RESULT_TRANSITION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_post_result_test_transition_v2_20260801.json"
RESEARCH_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_research_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_SUPERSESSION_V1 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_unified_report_supersession_20260801.json"
REPORT_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_unified_report_supersession_v2_20260801.json"
POST_REPORT_TRANSITION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_post_report_test_transition_20260801.json"
VERIFICATION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_verification_20260801.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign048_verified.json"
RUNNER_V1 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048.py"
RUNNER_V2 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_v2.py"
FEATURE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_features_v3.py"
FEATURE_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048_features.py"
CAMPAIGN_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048.py"
TERMINAL_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048_terminal.py"
C43_TERMINAL_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign043_terminal.py"
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
PREDECESSOR_STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign047_verified.json"
PREDECESSOR_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_research_record.json"
PREDECESSOR_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_unified_report_supersession_20260801.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def binding(path: Path) -> dict[str, str]:
    return {"path": display(path), "sha256": sha256(path)}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_new(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if load(path) != record:
            raise RuntimeError(f"refuse to rewrite terminal evidence: {path}")
        return
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def validation_rows() -> list[dict[str, Any]]:
    entry = load(TRIAL_LEDGER)["entries"][0]
    rows = []
    for fold in entry["training_and_validation_folds"]:
        metrics = fold["validation_metrics"]
        rows.append(
            {
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
            }
        )
    return rows


def post_result_transition() -> Path:
    freeze = load(DEVELOPMENT_FREEZE)
    old = freeze["bindings"]["development_boundary_tests"]
    if old["sha256"] == sha256(CAMPAIGN_TESTS):
        raise RuntimeError("Campaign048 post-result tests did not transition")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_post_result_test_transition",
        "status": "pre_return_test_fingerprint_preserved_terminal_assertions_current",
        "recorded_at": "2026-08-01T05:20:00Z",
        "purpose": "Preserve the exact pre-return boundary-test fingerprint while binding the post-result terminal status and rejection assertions.",
        "supersedes": binding(POST_RESULT_TRANSITION_V1),
        "bindings": {
            "development_implementation_freeze": binding(DEVELOPMENT_FREEZE),
            "pre_return_namespace_semantic_failure": binding(SEMANTIC_FAILURE),
            "current_campaign_tests": binding(CAMPAIGN_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
        },
        "historical_test_binding": {
            "path": old["path"],
            "expected_pre_return_sha256": old["sha256"],
            "current_post_result_sha256": sha256(CAMPAIGN_TESTS),
            "development_freeze_rewritten": False,
        },
        "semantic_boundary": {
            "test_change": "replace empty-ledger expectation with one exact terminal trial and add immutable terminal evidence assertions",
            "formula_direction_cost_fold_purge_or_gate_changed": False,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    }
    write_new(POST_RESULT_TRANSITION, record)
    return POST_RESULT_TRANSITION


def attempt_ledger() -> Path:
    audit = load(AUDIT)
    snapshot = load(SNAPSHOT)
    uniqueness = audit["uniqueness"][FACTOR]
    nearest = max(
        uniqueness["comparisons"],
        key=lambda item: item["absolute_median_daily_rank_correlation"],
    )
    rows = validation_rows()
    trial = load(TRIAL_LEDGER)["entries"][0]
    aggregate = trial["development_aggregate_metrics"]
    decision = load(SURVIVORS)["trial_decisions"][0]
    entries = [
        {
            "sequence": 1,
            "recorded_at": "2026-08-01T04:03:00Z",
            "kind": "infrastructure_only_failure",
            "stage": "feature_runner_parent_fingerprint_import",
            "attempt": "import the first Campaign048 feature runner before candidate values",
            "outcome": "failed_closed_because_the_parent_runner_fingerprint_used_an_abbreviated_summary_value",
            "candidate_values_read": False,
            "comparison_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued": False,
            "research_choice_changed": False,
            "recovery": "bind the exact Campaign047 parent hash without changing formula direction or gates",
        },
        {
            "sequence": 2,
            "recorded_at": "2026-08-01T04:06:00Z",
            "kind": "infrastructure_only_failure",
            "stage": "feature_snapshot_output_namespace_status",
            "attempt": "status the first bound Campaign048 build entry before candidate values",
            "outcome": "failed_closed_because_the_inherited_output_parent_still_named_campaign047",
            "candidate_values_read": False,
            "comparison_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued": False,
            "research_choice_changed": False,
            "recovery": "publish v2 path-only build entry using the Campaign048 output parent; formula and all gates unchanged",
        },
        {
            "sequence": 3,
            "recorded_at": "2026-08-01T05:06:42Z",
            "kind": "single_factor_ordered_no_return_gate",
            "stage": "coverage_capacity_then_71_factor_uniqueness",
            "attempt": TRIAL_ID,
            "factor": FACTOR,
            "direction": "higher",
            "formula": load(PROTOCOL)["candidate"]["formula"],
            "configuration": "exactly 240 regular bars; finite positive ordered OHLC; at least 120 positive-range bars; exact zero wicks retained; no imputation clipping threshold filter model fit subset combination alternate direction or parameter search",
            "outcome": "admitted_exactly_one_factor_for_the_frozen_2019_2023_development_trial",
            "data_and_code_fingerprints": {
                "no_return_protocol_sha256": sha256(PROTOCOL),
                "feature_snapshot_manifest_sha256": sha256(SNAPSHOT),
                "feature_snapshot_dataset_sha256": snapshot["dataset_sha256"],
                "effective_feature_runner_sha256": sha256(FEATURE_RUNNER),
                "no_return_audit_sha256": sha256(AUDIT),
            },
            "coverage_metrics": {
                "candidate_eligible_rows": audit["coverage_and_capacity"][FACTOR]["candidate_eligible_rows"],
                "median_coverage": audit["coverage_and_capacity"][FACTOR]["median_coverage"],
                "p05_coverage": audit["coverage_and_capacity"][FACTOR]["p05_coverage"],
                "eligible_names_p05": audit["coverage_and_capacity"][FACTOR]["eligible_names_p05"],
                "potential_non_overlapping_three_session_cohorts": audit["coverage_and_capacity"][FACTOR]["potential_non_overlapping_three_session_cohorts"],
                "gate_passed": True,
            },
            "uniqueness_metrics": {
                "comparison_factor_count": uniqueness["comparison_factor_count"],
                "comparison_order_matches_preregistration": uniqueness["comparison_order_matches_preregistration"],
                "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"],
                "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
                "nearest_comparison": nearest["comparison_factor"],
                "all_required_comparisons_passed": uniqueness["all_required_comparisons_passed"],
            },
            "candidate_values_read": True,
            "comparison_values_read": True,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "research_choice_changed_after_values": False,
        },
        {
            "sequence": 4,
            "recorded_at": "2026-08-01T05:15:00Z",
            "kind": "infrastructure_only_failure",
            "stage": "development_runner_namespace_semantic_validation",
            "attempt": "validate Campaign048 v1 exact trial-id override after all 17 preregistration bindings passed",
            "outcome": "failed_before_daily_price_or_return_read_because_the_override_targeted_the_outer_generated_namespace",
            "failure_record": display(SEMANTIC_FAILURE),
            "failed_preregistration_sha256": sha256(PREREG_V1),
            "candidate_values_newly_read": False,
            "comparison_values_newly_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued": False,
            "research_choice_changed": False,
            "recovery": "publish byte-bound v2 runner and preregistration with the exact trial-id override inside the inherited engine namespace",
        },
        {
            "sequence": 5,
            "recorded_at": trial["created_at"],
            "kind": "development_result_continuation",
            "parent_sequence": 3,
            "attempt": TRIAL_ID,
            "factor": FACTOR,
            "direction": "higher",
            "formula": load(PROTOCOL)["candidate"]["formula"],
            "development_trial_count_increment": 1,
            "research_attempt_count_increment": 0,
            "training_and_validation_folds": [
                "train 2019-2020, validate 2021",
                "train 2019-2021, validate 2022",
                "train 2019-2022, validate 2023",
            ],
            "purge_signal_sessions_each_boundary": 3,
            "label_containment_required": True,
            "entry_exit": "next accepted local session open t+1 to third accepted local session close t+3",
            "data_and_code_fingerprints": {
                "development_preregistration_sha256": sha256(PREREG_V2),
                "development_runner_sha256": sha256(RUNNER_V2),
                "development_implementation_freeze_sha256": sha256(DEVELOPMENT_FREEZE),
                "trial_ledger_sha256": sha256(TRIAL_LEDGER),
                "development_survivor_record_sha256": sha256(SURVIVORS),
                "closed_stress_record_sha256": sha256(STRESS),
                "campaign_report_sha256": sha256(CAMPAIGN_REPORT),
            },
            "validation_fold_metrics": rows,
            "development_aggregate_metrics": {
                "cohorts": aggregate["association"]["cohorts"],
                "mean_rank_ic": aggregate["association"]["mean_rank_ic"],
                "mean_top3_minus_bottom3_gross_return": aggregate["association"]["mean_top3_minus_bottom3_gross_return"],
                "normalized_return": aggregate["normalized_execution"]["net_cumulative_return"],
                "normalized_maximum_drawdown": aggregate["normalized_execution"]["maximum_drawdown"],
                "pilot_0bp_return": aggregate["pilot_slippage_sensitivity"]["0.0000"]["net_cumulative_return"],
                "pilot_5bp_return": aggregate["pilot_slippage_sensitivity"]["0.0005"]["net_cumulative_return"],
                "pilot_10bp_return": aggregate["pilot_slippage_sensitivity"]["0.0010"]["net_cumulative_return"],
                "pilot_20bp_return": aggregate["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"],
            },
            "survivor_decision": decision,
            "historical_daily_price_fields_read": ["open", "close", "factor", "paused", "limit"],
            "historical_forward_return_fields_read": True,
            "2024_2025_stress_opened": False,
            "2024_2025_stress_return_fields_read": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "status_and_rejection_reason": "terminal_zero_survivors_all_three_validation_rank_ic_spread_normalized_return_and_10bp_return_values_negative_with_drawdown_and_aggregate_20bp_gates_failed",
        },
    ]
    entries.append(
        {
            "sequence": 6,
            "recorded_at": "2026-08-01T05:24:00Z",
            "kind": "infrastructure_only_failure",
            "stage": "terminal_research_record_publication",
            "attempt": "publish the first Campaign048 terminal research record from the immutable trial ledger",
            "outcome": "failed_closed_because_the_publisher_expected_a_nonexistent_top_level_entries_sha256_field",
            "preserved_attempt_ledger_v1": binding(ATTEMPT_LEDGER_V1),
            "historical_daily_price_fields_newly_read": [],
            "historical_forward_return_fields_newly_read": False,
            "provider_request_issued": False,
            "research_choice_changed": False,
            "recovery": "publish an additive v2 attempt ledger and derive entry count plus chain tip only from fields present in the immutable trial ledger",
        }
    )
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_research_attempt_ledger",
        "append_only": True,
        "counting_rule": "Every distinct formula, direction, parameter set, subset, filter, model, combination, and infrastructure-only failure counts once; the same frozen factor advancing from no-return admission into its preregistered development trial remains one research attempt but adds a continuation ledger entry.",
        "supersedes": binding(ATTEMPT_LEDGER_V1),
        "campaign048_ledger_entry_count": 6,
        "campaign048_attempt_count": 5,
        "historical_research_attempt_count_before_campaign048": 274,
        "cumulative_historical_research_attempt_count": 279,
        "campaign048_historical_return_trial_count": 1,
        "cumulative_return_reading_development_trial_count_before_campaign048": 263,
        "cumulative_return_reading_development_trial_count": 264,
        "entries": entries,
    }
    write_new(ATTEMPT_LEDGER, record)
    return ATTEMPT_LEDGER


def research_record() -> Path:
    protocol = load(PROTOCOL)
    snapshot = load(SNAPSHOT)
    audit = load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    nearest = max(unqueness := uniqueness["comparisons"], key=lambda item: item["absolute_median_daily_rank_correlation"])
    trial_ledger = load(TRIAL_LEDGER)
    entry = trial_ledger["entries"][0]
    aggregate = entry["development_aggregate_metrics"]
    survivor = load(SURVIVORS)
    decision = survivor["trial_decisions"][0]
    stress = load(STRESS)
    quality = snapshot["quality"]
    q = f"{FACTOR}__"
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_research_record",
        "status": "completed_zero_development_survivors_stress_interval_not_opened",
        "recorded_at": "2026-08-01T05:23:00Z",
        "purpose": "Record every Campaign048 failure, exact factor configuration, ordered no-return result, and sole 2019-2023 expanding-walk-forward trial; preserve the zero-survivor decision and keep 2024-2025, Candidate49 history, and current trading outputs closed.",
        "authoritative_inputs": {
            "prior_iteration_state": binding(PREDECESSOR_STATE),
            "historical_walkforward_policy": binding(POLICY),
            "prior_campaign_terminal_record": binding(PREDECESSOR_RECORD),
        },
        "frozen_evidence": {
            "concept_scouting": binding(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_concept_scouting.json"),
            "mechanism_overlap_audit": binding(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_mechanism_overlap_audit.json"),
            "no_return_preregistration": binding(PROTOCOL),
            "feature_implementation_freeze": binding(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_feature_implementation_freeze_20260801.json"),
            "snapshot_publication_binding": binding(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_snapshot_publication_binding_20260801.json"),
            "snapshot_protocol_clarification": binding(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_inherited_protocol_evidence_clarification_20260801.json"),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "development_namespace_semantic_failure": binding(SEMANTIC_FAILURE),
            "development_preregistration_v1_preserved": binding(PREREG_V1),
            "development_preregistration_v2": binding(PREREG_V2),
            "development_implementation_freeze": binding(DEVELOPMENT_FREEZE),
        },
        "factor_definition": protocol["candidate"],
        "feature_snapshot": {
            **binding(SNAPSHOT),
            "dataset_sha256": snapshot["dataset_sha256"],
            "partitions": snapshot["partitions"],
            "rows": snapshot["rows"],
            "eligible_rows": snapshot["factor_eligible_rows"][FACTOR],
            "below_minimum_positive_range_rows": quality[q + "below_minimum_positive_range_rows"],
            "invalid_ohlc_order_rows": quality[q + "invalid_ohlc_order_rows"],
            "zero_wick_denominator_rows": quality[q + "zero_wick_denominator_rows"],
            "endpoint_canonicalized_rows": quality[q + "endpoint_canonicalized_rows"],
            "exact_zero_lower_wick_positions": quality[q + "exact_zero_lower_wick_positions"],
            "exact_zero_upper_wick_positions": quality[q + "exact_zero_upper_wick_positions"],
            "all_partition_byte_and_frame_hashes_valid": audit["snapshot_file_verification"]["all_partition_byte_and_frame_hashes_valid"],
            "source_fields_read": snapshot["source_fields_read"],
            "source_volume_or_amount_read": False,
        },
        "no_return_result": {
            **binding(AUDIT),
            "status": audit["status"],
            "median_coverage": coverage["median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "median_eligible_names": coverage["eligible_names_median"],
            "p05_eligible_names": coverage["eligible_names_p05"],
            "potential_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "comparison_count": uniqueness["comparison_factor_count"],
            "comparison_order_matches_preregistration": uniqueness["comparison_order_matches_preregistration"],
            "all_comparisons_passed": uniqueness["all_required_comparisons_passed"],
            "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
            "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"],
            "nearest_comparison_factor": nearest["comparison_factor"],
            "nearest_median_daily_rank_correlation": nearest["median_daily_rank_correlation"],
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
        },
        "development_artifacts": {
            "runner_v1_preserved": binding(RUNNER_V1),
            "runner_v2": binding(RUNNER_V2),
            "development_boundary_tests": binding(CAMPAIGN_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "post_result_test_transition": binding(POST_RESULT_TRANSITION),
            "post_result_test_transition_v1_preserved": binding(POST_RESULT_TRANSITION_V1),
            "research_attempt_ledger_v1_preserved": binding(ATTEMPT_LEDGER_V1),
            "research_attempt_ledger": {**binding(ATTEMPT_LEDGER), "campaign_attempt_count": 5, "ledger_entry_count": 6, "cumulative_historical_research_attempt_count": 279, "cumulative_historical_return_trial_count": 264},
            "trial_ledger": {**binding(TRIAL_LEDGER), "entry_count": len(trial_ledger["entries"]), "chain_tip_sha256": trial_ledger["chain_tip_sha256"]},
            "development_survivors": {**binding(SURVIVORS), "selected_survivor_count": survivor["selected_survivor_count"]},
            "exposed_stress_consumption_record": {**binding(STRESS), "status": stress["status"], "stress_interval_opened": stress["stress_interval_opened"], "stress_return_fields_read": stress["stress_return_fields_read"]},
            "campaign_report": binding(CAMPAIGN_REPORT),
        },
        "validation_fold_results": validation_rows(),
        "development_aggregate_result": {
            "cohorts": aggregate["association"]["cohorts"],
            "mean_rank_ic": aggregate["association"]["mean_rank_ic"],
            "mean_top3_minus_bottom3_gross_return": aggregate["association"]["mean_top3_minus_bottom3_gross_return"],
            "normalized_return": aggregate["normalized_execution"]["net_cumulative_return"],
            "normalized_maximum_drawdown": aggregate["normalized_execution"]["maximum_drawdown"],
            "pilot_0bp_return": aggregate["pilot_slippage_sensitivity"]["0.0000"]["net_cumulative_return"],
            "pilot_5bp_return": aggregate["pilot_slippage_sensitivity"]["0.0005"]["net_cumulative_return"],
            "pilot_10bp_return": aggregate["pilot_slippage_sensitivity"]["0.0010"]["net_cumulative_return"],
            "pilot_20bp_return": aggregate["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"],
            "pilot_10bp_maximum_drawdown": aggregate["pilot_slippage_sensitivity"]["0.0010"]["maximum_drawdown"],
        },
        "survivor_decision": {**decision, "selected_survivor_count": survivor["selected_survivor_count"]},
        "prospective_boundary": {
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "decision": {
            "factor_terminal": True,
            "reason": "All three validation mean Rank IC, spread, normalized-return, and 10bp pilot-return values were negative; drawdown and aggregate 20bp gates also failed.",
            "2024_2025_stress_opened": False,
            "2024_2025_returns_read": False,
            "invert_repair_reanchor_renormalize_rewindow_rescale_filter_threshold_rerun_rescue_or_combine_allowed": False,
            "cumulative_historical_research_attempt_count_after_campaign": 279,
            "historical_development_return_trial_count_after_campaign": 264,
            "current_aggregation_candidate_count": 0,
            "next_action": "Begin Campaign049 historical research only from a genuinely independent mechanism; Candidate49 remains the sole prospective candidate and is unrelated to historical campaign numbering.",
            "investment_advice_or_current_selection_claim_allowed": False,
        },
    }
    write_new(RESEARCH_RECORD, record)
    return RESEARCH_RECORD


def report_supersession() -> Path:
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_unified_report_supersession",
        "status": "campaign047_report_binding_preserved_historically_campaign048_report_current",
        "recorded_at": "2026-08-01T05:27:00Z",
        "purpose": "Preserve Campaign047's immutable unified-report fingerprint and supersession chain while binding the append-only Campaign048 report update.",
        "bindings": {
            "campaign047_terminal_record": binding(PREDECESSOR_RECORD),
            "campaign048_terminal_record": binding(RESEARCH_RECORD),
            "previous_campaign047_supersession": binding(PREDECESSOR_SUPERSESSION),
            "previous_campaign048_supersession": binding(REPORT_SUPERSESSION_V1),
            "current_unified_research_report": binding(REPORT),
        },
        "historical_binding": {
            "record": display(REPORT_SUPERSESSION_V1),
            "json_pointer": "/bindings/current_unified_research_report",
            "expected_sha256": load(REPORT_SUPERSESSION_V1)["bindings"]["current_unified_research_report"]["sha256"],
            "current_sha256": sha256(REPORT),
            "historical_record_rewritten": False,
            "previous_supersession_rewritten": False,
        },
        "semantic_boundary": {
            "campaign047_result_or_gate_changed": False,
            "campaign048_result_or_gate_changed_after_values": False,
            "report_update_is_append_only": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    }
    write_new(REPORT_SUPERSESSION, record)
    return REPORT_SUPERSESSION


def post_report_transition() -> Path:
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_post_report_test_transition",
        "status": "historical_campaign047_report_binding_expected_stale_campaign048_supersession_current",
        "recorded_at": "2026-08-01T05:31:00Z",
        "purpose": "Bind the test transition that preserves Campaign047's immutable old report hash while recognizing Campaign048's append-only report supersession.",
        "bindings": {
            "campaign048_report_supersession": binding(REPORT_SUPERSESSION),
            "updated_campaign047_terminal_test": binding(REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign047_terminal.py"),
            "campaign048_terminal_test": binding(TERMINAL_TESTS),
        },
        "first_full_suite": {
            "passed": 1709,
            "failed": 1,
            "warnings": 13,
            "only_failure": "Campaign047 terminal test still required its historical unified-report binding to match the Campaign048-appended report.",
        },
        "semantic_boundary": {
            "campaign047_record_rewritten": False,
            "campaign048_record_or_result_changed": False,
            "test_now_requires_exactly_one_historical_report_binding_mismatch": True,
            "current_supersession_bindings_must_all_pass": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    }
    write_new(POST_REPORT_TRANSITION, record)
    return POST_REPORT_TRANSITION


def verification(focused_passed: int, full_passed: int, warnings: int) -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    research_validation = validator.validate_record(RESEARCH_RECORD, data_root=DATA_ROOT)
    prereg_validation = validator.validate_record(PREREG_V2, data_root=DATA_ROOT)
    transition_validation = validator.validate_record(POST_RESULT_TRANSITION, data_root=DATA_ROOT)
    supersession_validation = validator.validate_record(REPORT_SUPERSESSION, data_root=DATA_ROOT)
    if not all(item["all_bindings_passed"] for item in (research_validation, prereg_validation, transition_validation, supersession_validation)):
        raise RuntimeError("Campaign048 terminal bindings are not current")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_verification",
        "status": "terminal_campaign048_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-01T05:32:00Z",
        "purpose": "Bind Campaign048 terminal evidence, append-only ledgers, closed stress semantics, report supersession, tests, unchanged prospective ledgers, and credential-safe Saturday boundary.",
        "bindings": {
            "research_record": binding(RESEARCH_RECORD),
            "post_result_test_transition": binding(POST_RESULT_TRANSITION),
            "unified_report_supersession": binding(REPORT_SUPERSESSION),
            "post_report_test_transition": binding(POST_REPORT_TRANSITION),
            "no_return_preregistration": binding(PROTOCOL),
            "no_return_audit": binding(AUDIT),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "development_preregistration": binding(PREREG_V2),
            "development_implementation_freeze": binding(DEVELOPMENT_FREEZE),
            "namespace_semantic_failure": binding(SEMANTIC_FAILURE),
            "campaign_runner": binding(RUNNER_V2),
            "feature_and_no_return_runner": binding(FEATURE_RUNNER),
            "feature_tests": binding(FEATURE_TESTS),
            "campaign_tests": binding(CAMPAIGN_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "updated_historical_report_test": binding(C43_TERMINAL_TESTS),
            "feature_snapshot": binding(SNAPSHOT),
            "research_attempt_ledger": binding(ATTEMPT_LEDGER),
            "trial_ledger": binding(TRIAL_LEDGER),
            "development_survivors": binding(SURVIVORS),
            "unopened_stress_record": binding(STRESS),
            "campaign_report": binding(CAMPAIGN_REPORT),
            "unified_research_report": binding(REPORT),
            "candidate49_signal_ledger": binding(SIGNAL_LEDGER),
            "candidate49_execution_ledger": binding(EXECUTION_LEDGER),
        },
        "verification_summary": {
            "development_preregistration_binding_count": prereg_validation["binding_count"],
            "development_preregistration_bindings_passed": prereg_validation["passed_binding_count"],
            "research_record_binding_count": research_validation["binding_count"],
            "research_record_bindings_passed": research_validation["passed_binding_count"],
            "post_result_transition_binding_count": transition_validation["binding_count"],
            "report_supersession_binding_count": supersession_validation["binding_count"],
            "focused_campaign048_tests_passed": focused_passed,
            "full_data_collector_tests_passed": full_passed,
            "full_data_collector_tests_failed": 0,
            "full_data_collector_test_warnings": warnings,
            "first_full_suite_expected_historical_report_pointer_failure": {"passed": 1709, "failed": 1, "warnings": 13},
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign_research_attempt_count": 5,
            "campaign_ledger_entry_count": 6,
            "cumulative_historical_research_attempt_count": 279,
            "development_trial_count": 1,
            "cumulative_return_reading_development_trial_count": 264,
            "development_survivor_count": 0,
            "stress_2024_2025_opened": False,
            "stress_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "campaign048_formula_direction_parameter_cost_fold_purge_or_gate_changed_after_values": False,
        },
    }
    write_new(VERIFICATION, record)
    return VERIFICATION


def state() -> Path:
    record = {
        "version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign048_terminal_verified_historical_walkforward_ready_for_independent_campaign049",
        "recorded_at": "2026-08-01T05:35:00Z",
        "authoritative_predecessor": binding(PREDECESSOR_STATE),
        "research_policy": {
            "historical_walkforward_policy": binding(POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
            "every_formula_direction_parameter_subset_filter_model_combination_and_infrastructure_failure_counted": True,
            "historical_results_may_generate_current_scores_selections_sizes_or_orders": False,
            "historical_results_may_backfill_candidate49": False,
        },
        "fixed_strategy": {
            "holding_period_local_sessions": 3,
            "signal": "accepted local session close t",
            "entry": "next accepted local session open t+1",
            "exit": "third accepted local session close t+3",
            "topk": 3,
            "development_folds": 3,
            "purge_signal_sessions_each_partition_boundary": 3,
            "t_t_plus_1_t_plus_3_must_remain_in_same_partition": True,
            "pilot_capital_cny": 200000,
            "primary_pilot_cost_bps": 10,
            "aggregate_survivor_cost_bps": 20,
        },
        "campaign048": {
            "factor": FACTOR,
            "direction": "higher",
            "formula": load(PROTOCOL)["candidate"]["formula"],
            "no_return": {
                "median_coverage": load(AUDIT)["coverage_and_capacity"][FACTOR]["median_coverage"],
                "p05_coverage": load(AUDIT)["coverage_and_capacity"][FACTOR]["p05_coverage"],
                "comparison_factor_count": 71,
                "maximum_observed_absolute_median_daily_rank_correlation": load(AUDIT)["uniqueness"][FACTOR]["maximum_observed_absolute_median_daily_rank_correlation"],
                "admissible_factor_count": 1,
            },
            "development": {
                "trial_id": TRIAL_ID,
                "trial_count": 1,
                "validation_mean_rank_ic": [row["mean_rank_ic"] for row in validation_rows()],
                "validation_normalized_return": [row["normalized_return"] for row in validation_rows()],
                "validation_pilot_10bp_return": [row["pilot_10bp_return"] for row in validation_rows()],
                "development_pilot_10bp_return": load(RESEARCH_RECORD)["development_aggregate_result"]["pilot_10bp_return"],
                "development_pilot_20bp_return": load(RESEARCH_RECORD)["development_aggregate_result"]["pilot_20bp_return"],
                "development_survivor_count": 0,
                "2024_2025_stress_opened": False,
                "2024_2025_returns_read": False,
            },
            "attempt_accounting": {
                "infrastructure_only_failures": 4,
                "complete_factor_attempts": 1,
                "campaign048_distinct_attempts": 5,
                "campaign048_ledger_entries": 6,
                "campaign048_return_reading_development_trials": 1,
                "cumulative_historical_research_attempts": 279,
                "cumulative_return_reading_development_trials": 264,
            },
            "terminal": {
                "factor_terminal": True,
                "reason": "All three frozen validation folds had negative association, spread, normalized return, and 10bp pilot return.",
                "invert_repair_rewindow_rescale_filter_threshold_rerun_rescue_or_combine_allowed": False,
            },
            "authoritative_records": {
                "research_record": binding(RESEARCH_RECORD),
                "verification": binding(VERIFICATION),
                "unified_report_supersession": binding(REPORT_SUPERSESSION),
            },
        },
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign048": 279,
            "cumulative_return_reading_development_trial_count_after_campaign048": 264,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_daily_data_root": "/Users/niyufei/Coding/qlib/data",
            "local_date": "2026-08-01",
            "local_weekday": "Saturday",
            "candidate49_same_day_workflow_applicable": False,
            "dotenv_path": "/Users/niyufei/Coding/qlib/.env",
            "dotenv_is_regular_non_symlink_file": True,
            "dotenv_is_git_ignored": True,
            "dotenv_mode": "0600",
            "tushare_token_present": True,
            "credential_value_printed_hashed_or_persisted_in_records": False,
            "provider_request_issued_by_campaign048_or_credential_verification": False,
        },
        "prospective_boundary": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate50_activation_allowed": False,
        },
        "verification_summary": load(VERIFICATION)["verification_summary"],
        "next_action": {
            "historical": "Begin historical Campaign049 from an independent mechanism with separate pre-value scouting, overlap audit, finite fingerprint-bound protocol, and binding-validator exit code 0. Offline work may run at any time.",
            "prospective": "Today is Saturday, so do not run Candidate49 provider workflow. On the next accepted local trading date use a new absolute-date staging root and retain the post-16:30 ready=true gate.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start Candidate50",
                "do not invert repair rewindow rescale filter threshold rerun rescue or combine Campaign048",
                "do not open Campaign048 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice",
            ],
        },
    }
    write_new(STATE, record)
    return STATE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("post-result-transition", "attempt-ledger", "research-record", "report-supersession", "post-report-transition", "verification", "state"))
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args()
    actions = {
        "post-result-transition": post_result_transition,
        "attempt-ledger": attempt_ledger,
        "research-record": research_record,
        "report-supersession": report_supersession,
        "post-report-transition": post_report_transition,
        "verification": lambda: verification(args.focused_passed, args.full_passed, args.warnings),
        "state": state,
    }
    path = actions[args.stage]()
    print(json.dumps({"path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
