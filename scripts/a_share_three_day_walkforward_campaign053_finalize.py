#!/usr/bin/env python3
"""Publish append-only terminal evidence for historical Campaign053."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_amount_price_discovery_alignment_js_238p"
DUPLICATE = "intraday_price_update_share_238m"
CROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_053"
AUDIT = CROOT / "no_return/20260803T125238Z_campaign053_no_return_audit.json"
SNAPSHOT = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign053_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign053_feature_library_v1/snapshot_manifest.json"
)

POLICY = ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
PREDECESSOR = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign052_candidate49_source_failure_verified.json"
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_053_concept_scouting.json"
MECHANISM = ROOT / "docs/a_share_three_day_walkforward_campaign_053_mechanism_overlap_audit.json"
PROTOCOL = ROOT / "docs/a_share_three_day_walkforward_campaign_053_no_return_preregistration.json"
FEATURE_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_053_feature_implementation_freeze_20260803.json"
SNAPSHOT_BINDING = ROOT / "docs/a_share_three_day_walkforward_campaign_053_snapshot_publication_binding_20260803.json"
REPAIR_AUTHORIZATION = ROOT / "docs/a_share_three_day_walkforward_campaign_053_no_return_audit_campaign051_verifier_failure_repair_20260803.json"
REPAIR_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_053_campaign051_verifier_repair_implementation_freeze_20260803.json"
FEATURE_RUNNERS = [
    ROOT / f"scripts/a_share_three_day_walkforward_campaign053_features{suffix}.py"
    for suffix in ("", "_v2", "_v3", "_v4", "_v5", "_v6")
]
FINALIZER = ROOT / "scripts/a_share_three_day_walkforward_campaign053_finalize.py"
FEATURE_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign053_features.py"
REPAIR_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign053_no_return_audit_repair.py"
TERMINAL_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign053_terminal.py"

NO_RETURN_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_053_no_return_audit_freeze_20260803.json"
ATTEMPT_LEDGER = CROOT / "research_attempt_ledger.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_053_research_record.json"
REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_053_unified_report_supersession_20260803.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_053_verification_20260803.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign053_verified.json"
PIPELINE_DOC = ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
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


def audit_parts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    audit = load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    if len(failed) != 1 or failed[0]["comparison_factor"] != DUPLICATE:
        raise RuntimeError("Campaign053 failed-comparison semantics changed")
    return audit, coverage, uniqueness, failed[0]


def no_return_freeze() -> Path:
    audit, coverage, uniqueness, failed = audit_parts()
    gate = coverage["gate"]
    return write_new(NO_RETURN_FREEZE, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_no_return_audit_freeze",
        "status": "terminal_zero_admissible_factors_after_uniqueness_before_historical_returns",
        "recorded_at": "2026-08-03T12:56:00Z",
        "purpose": "Bind the sole completed Campaign053 no-return audit and forbid post-correlation rescue.",
        "authoritative_inputs": {
            "no_return_preregistration": binding(PROTOCOL),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "snapshot_manifest": {**binding(SNAPSHOT), "dataset_sha256": load(SNAPSHOT)["dataset_sha256"]},
            "audit_infrastructure_failure_and_authorized_repair": binding(REPAIR_AUTHORIZATION),
            "repair_implementation_freeze": binding(REPAIR_FREEZE),
            "no_return_audit": binding(AUDIT),
            "effective_successful_audit_runner": binding(FEATURE_RUNNERS[4]),
            "audit_hash_bound_terminal_runner": binding(FEATURE_RUNNERS[5]),
        },
        "result": {
            "candidate": FACTOR,
            "direction": "higher",
            "candidate_eligible_rows": coverage["candidate_eligible_rows"],
            "quality_listing_eligible_rows": coverage["quality_listing_eligible_rows"],
            "calendar_sessions": coverage["calendar_sessions"],
            "median_coverage": coverage["median_coverage"],
            "minimum_median_coverage": gate["minimum_median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "minimum_p05_coverage": gate["minimum_p05_coverage"],
            "eligible_names_p05": coverage["eligible_names_p05"],
            "minimum_p05_eligible_names": gate["minimum_p05_eligible_names"],
            "potential_non_overlapping_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "observed_calendar_year_count": len(coverage["observed_cohort_years"]),
            "coverage_gate_passed": coverage["gate_passed_before_comparison_values"],
            "comparison_factor_count": uniqueness["comparison_factor_count"],
            "comparison_order_matches_preregistration": uniqueness["comparison_order_matches_preregistration"],
            "failed_comparison_factor": failed["comparison_factor"],
            "failed_comparison_median_daily_rank_correlation": failed["median_daily_rank_correlation"],
            "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"],
            "uniqueness_gate_passed": uniqueness["all_required_comparisons_passed"],
            "admissible_factor_count": audit["admissible_factor_count"],
        },
        "semantic_boundary": {
            "all_candidate_and_comparison_snapshot_partition_hashes_verified": True,
            "source_fields_read": audit["source_fields_read"],
            "historical_daily_price_fields_read": audit["historical_daily_price_fields_read"],
            "historical_forward_return_fields_read": audit["historical_forward_return_fields_read"],
            "candidate49_historical_return_read": audit["candidate49_historical_return_read"],
            "candidate49_prospective_ledgers_changed": audit["candidate49_prospective_ledgers_changed"],
            "training_or_model_fitting_performed": audit["training_or_model_fitting_performed"],
            "current_scoring_selection_sizing_or_orders_performed": audit["current_scoring_selection_sizing_or_orders_performed"],
            "predictive_value_established": False,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "uniqueness_after_coverage_before_historical_returns",
            "terminal_reason": "absolute_median_daily_rank_correlation_0.8528583420588608_with_intraday_price_update_share_238m_exceeded_frozen_0.8_limit",
            "historical_walkforward_allowed": False,
            "2024_2025_stress_allowed": False,
            "inversion_rewindow_rescale_threshold_filter_subset_model_combination_rerun_or_rescue_allowed": False,
            "next_action": "Record the terminal attempt and start only an independently preregistered Campaign054 mechanism.",
        },
    })


def attempt_ledger() -> Path:
    protocol = load(PROTOCOL)
    audit, coverage, uniqueness, failed = audit_parts()
    return write_new(ATTEMPT_LEDGER, {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_research_attempt_ledger",
        "status": "terminal_append_only_zero_return_trials",
        "append_only": True,
        "counting_rule": "Every infrastructure-only failure and every distinct formula, direction, parameter set, subset, filter, model, or combination counts once; no-return rejection creates no return-reading development trial.",
        "campaign053_ledger_entry_count": 2,
        "campaign053_attempt_count": 2,
        "campaign053_infrastructure_only_failure_count": 1,
        "campaign053_complete_factor_attempt_count": 1,
        "historical_research_attempt_count_before_campaign053": 300,
        "cumulative_historical_research_attempt_count": 302,
        "campaign053_historical_return_trial_count": 0,
        "cumulative_return_reading_development_trial_count_before_campaign053": 266,
        "cumulative_return_reading_development_trial_count": 266,
        "entries": [
            {
                "sequence": 1,
                "kind": "infrastructure_only_failure",
                "stage": "no_return_audit_campaign051_snapshot_verification",
                "incident_id": "campaign053_shared_output_columns_contaminated_campaign051_verifier",
                "recorded_at": load(REPAIR_AUTHORIZATION)["recorded_at"],
                "research_attempt_count_increment": 1,
                "development_trial_count_increment": 0,
                "outcome": "exit_1_before_campaign051_comparison_value_load_and_without_completed_audit_artifact",
                "correction": "fingerprint_bound_isolated_exact_campaign051_five_column_verifier_then_one_same_parameter_continuation",
                "evidence": {"failure_and_authorization": binding(REPAIR_AUTHORIZATION), "repair_freeze": binding(REPAIR_FREEZE)},
                "comparison_metric_values_persisted": False,
                "historical_daily_price_fields_read": [],
                "historical_forward_return_fields_read": False,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
                "provider_request_issued": False,
            },
            {
                "sequence": 2,
                "kind": "single_factor_ordered_no_return_gate",
                "attempt_id": f"wf053_{FACTOR}_single_higher",
                "recorded_at": audit["created_at"],
                "research_attempt_count_increment": 1,
                "development_trial_count_increment": 0,
                "economic_hypothesis": "Transaction-value mass aligned with absolute-return price discovery may identify more information-efficient intraday participation.",
                "formula": protocol["candidate"]["formula"],
                "direction": "higher",
                "feature_set": [FACTOR],
                "parameter_filter_subset_combination_and_model": "exact frozen 238-endpoint Jensen-Shannon alignment; no alternative pairing, window, direction, transform, filter, subset, combination, model, or fit",
                "outcome": "terminal_no_return_rejection_uniqueness_failed_against_intraday_price_update_share_238m",
                "evidence": {"protocol": binding(PROTOCOL), "snapshot": {**binding(SNAPSHOT), "dataset_sha256": load(SNAPSHOT)["dataset_sha256"]}, "audit": binding(AUDIT), "audit_freeze": binding(NO_RETURN_FREEZE), "effective_runner": binding(FEATURE_RUNNERS[4])},
                "no_return_metrics": {
                    "median_coverage": coverage["median_coverage"],
                    "p05_coverage": coverage["p05_coverage"],
                    "eligible_names_p05": coverage["eligible_names_p05"],
                    "potential_non_overlapping_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
                    "comparison_factor_count": uniqueness["comparison_factor_count"],
                    "failed_comparison_factor": failed["comparison_factor"],
                    "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"],
                    "all_gates_passed": False,
                },
                "source_fields_read": audit["source_fields_read"],
                "historical_daily_price_fields_read": [],
                "historical_forward_return_fields_read": False,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
                "provider_request_issued": False,
            },
        ],
    })


def research_record() -> Path:
    protocol, snapshot = load(PROTOCOL), load(SNAPSHOT)
    audit, coverage, uniqueness, failed = audit_parts()
    gate = coverage["gate"]
    return write_new(RESEARCH_RECORD, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_research_record",
        "status": "completed_zero_admissible_factors_stop_before_historical_returns",
        "recorded_at": "2026-08-03T12:58:00Z",
        "purpose": "Record every Campaign053 attempt, exact amount/price-discovery factor, immutable snapshot, and uniqueness-stage terminal decision.",
        "authoritative_inputs": {"prior_iteration_state": binding(PREDECESSOR), "historical_walkforward_policy": binding(POLICY)},
        "frozen_evidence": {
            "concept_scouting": binding(CONCEPT),
            "mechanism_overlap_audit": binding(MECHANISM),
            "no_return_preregistration": binding(PROTOCOL),
            "feature_implementation_freeze": binding(FEATURE_FREEZE),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "audit_failure_and_repair_authorization": binding(REPAIR_AUTHORIZATION),
            "repair_implementation_freeze": binding(REPAIR_FREEZE),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "feature_and_audit_runners": [binding(path) for path in FEATURE_RUNNERS],
            "finalizer": binding(FINALIZER),
            "feature_tests": binding(FEATURE_TESTS),
            "repair_tests": binding(REPAIR_TESTS),
        },
        "factor_definition": protocol["candidate"],
        "feature_snapshot": {
            **binding(SNAPSHOT),
            "dataset_sha256": snapshot["dataset_sha256"],
            "partitions": snapshot["partitions"],
            "rows": snapshot["rows"],
            "eligible_rows": snapshot["factor_eligible_rows"][FACTOR],
            "all_partition_byte_and_frame_hashes_valid": audit["snapshot_file_verification"]["all_partition_byte_and_frame_hashes_valid"],
            "source_fields_read": snapshot["source_fields_read"],
            "daily_price_fields_read": snapshot["daily_price_fields_read"],
            "forward_return_fields_read": snapshot["forward_return_fields_read"],
        },
        "no_return_result": {
            **binding(AUDIT),
            "status": audit["status"],
            "calendar_sessions": coverage["calendar_sessions"],
            "quality_listing_eligible_rows": coverage["quality_listing_eligible_rows"],
            "candidate_eligible_rows": coverage["candidate_eligible_rows"],
            "median_coverage": coverage["median_coverage"],
            "minimum_median_coverage": gate["minimum_median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "minimum_p05_coverage": gate["minimum_p05_coverage"],
            "median_eligible_names": coverage["eligible_names_median"],
            "p05_eligible_names": coverage["eligible_names_p05"],
            "minimum_p05_eligible_names": gate["minimum_p05_eligible_names"],
            "potential_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "observed_calendar_years": coverage["observed_cohort_years"],
            "coverage_gate_passed": coverage["gate_passed_before_comparison_values"],
            "comparison_factor_count": uniqueness["comparison_factor_count"],
            "comparison_order_matches_preregistration": uniqueness["comparison_order_matches_preregistration"],
            "failed_comparison_count": 1,
            "failed_comparison_factor": failed["comparison_factor"],
            "failed_comparison_median_daily_rank_correlation": failed["median_daily_rank_correlation"],
            "maximum_absolute_median_daily_rank_correlation": uniqueness["maximum_observed_absolute_median_daily_rank_correlation"],
            "uniqueness_gate_passed": uniqueness["all_required_comparisons_passed"],
            "admissible_factor_count": audit["admissible_factor_count"],
            "historical_daily_price_fields_read": audit["historical_daily_price_fields_read"],
            "historical_forward_return_fields_read": audit["historical_forward_return_fields_read"],
        },
        "append_only_attempt_accounting": {
            "ledger": binding(ATTEMPT_LEDGER),
            "prior_historical_research_attempt_count": 300,
            "campaign053_infrastructure_failure_count": 1,
            "campaign053_complete_factor_attempt_count": 1,
            "campaign053_total_attempt_count": 2,
            "cumulative_historical_research_attempt_count": 302,
            "campaign053_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "no_return_uniqueness_gate_before_historical_returns",
            "terminal_reason": "absolute_median_daily_rank_correlation_exceeded_0.8_against_intraday_price_update_share_238m",
            "development_folds_opened": False,
            "development_return_fields_read": False,
            "2024_2025_stress_opened": False,
            "2024_2025_returns_read": False,
            "inversion_rewindow_rescale_threshold_filter_subset_model_combination_rerun_or_rescue_allowed": False,
            "next_campaign_must_be_independently_preregistered": True,
            "new_daily_bar_or_16_30_wait_required_for_next_offline_campaign": False,
        },
        "prospective_boundary": {
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "data_limitation": "The eligible universe derives from a current listing snapshot and can contain survivorship bias; no predictive return claim was evaluated.",
    })


def report_supersession() -> Path:
    return write_new(REPORT_SUPERSESSION, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_unified_report_supersession",
        "status": "campaign052_and_candidate49_failure_bindings_preserved_historically_campaign053_report_current",
        "recorded_at": "2026-08-03T13:02:00Z",
        "bindings": {
            "predecessor_iteration_state": binding(PREDECESSOR),
            "campaign053_terminal_record": binding(RESEARCH_RECORD),
            "current_unified_research_report": binding(REPORT),
            "current_data_pipeline_documentation": binding(PIPELINE_DOC),
            "current_manage_qlib_a_share_data_skill": binding(SKILL),
        },
        "semantic_boundary": {
            "campaign052_candidate49_failure_or_campaign053_result_or_gate_changed": False,
            "report_documentation_and_skill_updates_are_append_only": True,
            "historical_daily_price_or_forward_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def verification() -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    records = [NO_RETURN_FREEZE, RESEARCH_RECORD, REPORT_SUPERSESSION]
    checked = [validator.validate_record(path, data_root=DATA_ROOT) for path in records]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Campaign053 terminal bindings are not current")
    if sha256(AUDIT) != "8228e32422686d020bdf7c6b00e54469d025884c23c234b48088428280bfd3ba":
        raise RuntimeError("Campaign053 audit changed")
    if sha256(SIGNAL_LEDGER) != "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79":
        raise RuntimeError("Candidate49 signal ledger changed")
    if sha256(EXECUTION_LEDGER) != "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f":
        raise RuntimeError("Candidate49 execution ledger changed")
    return write_new(VERIFICATION, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_verification",
        "status": "terminal_campaign053_bindings_tests_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-03T13:04:00Z",
        "bindings": {
            "research_record": binding(RESEARCH_RECORD),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "unified_report_supersession": binding(REPORT_SUPERSESSION),
            "research_attempt_ledger": binding(ATTEMPT_LEDGER),
            "audit_failure_and_repair": binding(REPAIR_AUTHORIZATION),
            "repair_implementation_freeze": binding(REPAIR_FREEZE),
            "terminal_audit_runner": binding(FEATURE_RUNNERS[5]),
            "finalizer": binding(FINALIZER),
            "feature_tests": binding(FEATURE_TESTS),
            "repair_tests": binding(REPAIR_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "unified_research_report": binding(REPORT),
            "data_pipeline_documentation": binding(PIPELINE_DOC),
            "manage_qlib_a_share_data_skill": binding(SKILL),
            "candidate49_signal_ledger": binding(SIGNAL_LEDGER),
            "candidate49_execution_ledger": binding(EXECUTION_LEDGER),
        },
        "verification_summary": {
            "binding_records_checked": len(checked),
            "all_current_campaign053_bindings_passed": True,
            "focused_campaign053_tests_passed": 16,
            "focused_campaign053_tests_failed": 0,
            "candidate_snapshot_partitions_reverified": 33015,
            "candidate_snapshot_rows_reverified": 7724498,
            "comparison_factor_count_replayed": 76,
            "campaign051_isolated_verifier_partitions_reverified": 33015,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign053_attempt_count": 2,
            "cumulative_historical_research_attempt_count": 302,
            "campaign053_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
            "admissible_factor_count": 0,
            "development_folds_opened": False,
            "stress_2024_2025_opened": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    })


def state() -> Path:
    record = load(RESEARCH_RECORD)
    return write_new(STATE, {
        "version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign053_terminal_verified_historical_walkforward_ready_for_independent_campaign054",
        "recorded_at": "2026-08-03T13:06:00Z",
        "authoritative_predecessor": binding(PREDECESSOR),
        "research_policy": {
            "historical_walkforward_policy": binding(POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
            "historical_results_may_generate_current_scores_selections_sizes_or_orders": False,
            "historical_results_may_backfill_candidate49": False,
        },
        "campaign053": {
            "factor": FACTOR,
            "direction": "higher",
            "formula": record["factor_definition"]["formula"],
            "snapshot": record["feature_snapshot"],
            "no_return": record["no_return_result"],
            "attempt_accounting": record["append_only_attempt_accounting"],
            "development": {"folds_opened": False, "return_fields_read": False, "trial_count": 0, "selected_survivor_count": 0},
            "stress_2024_2025": {"status": "not_opened_no_no_return_admissible_factor", "opened": False, "return_fields_read": False},
            "terminal": record["decision"],
            "authoritative_records": {"research_record": binding(RESEARCH_RECORD), "verification": binding(VERIFICATION), "unified_report_supersession": binding(REPORT_SUPERSESSION)},
        },
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign053": 302,
            "cumulative_return_reading_development_trial_count_after_campaign053": 266,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_repository_root": str(ROOT),
            "configured_compatibility_root": "/Users/niyufei/Coding/qlib",
            "configured_compatibility_root_exists": False,
            "active_daily_data_root": "/Volumes/DIsk/Disk-Coding/qlib/data",
            "historical_minute_data_root": str(DATA_ROOT),
            "local_date": "2026-08-03",
            "local_weekday": "Monday",
            "dotenv_path": str(ROOT / ".env"),
            "dotenv_is_regular_non_symlink_file": True,
            "dotenv_is_git_ignored": True,
            "dotenv_mode": "0600",
            "tushare_token_present": True,
            "credential_value_printed_hashed_or_persisted_in_records": False,
            "provider_request_issued_by_campaign053_or_credential_verification": False,
        },
        "prospective_boundary": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_20260803_source_failure_state_preserved": binding(PREDECESSOR),
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "second_prospective_candidate_activation_allowed": False,
        },
        "verification_summary": load(VERIFICATION)["verification_summary"],
        "next_action": {
            "historical": "Begin Campaign054 only from a genuinely independent, pre-value-frozen mechanism; offline work may run at any time.",
            "prospective": "Do not retry Candidate49 on 2026-08-03; use only a later accepted local trading session's same-day post-16:30 ready=true workflow.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start a second prospective candidate",
                "do not invert rewindow rescale threshold filter rerun rescue or combine Campaign053",
                "do not open Campaign053 development folds or 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice",
            ],
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("no-return-freeze", "attempt-ledger", "research-record", "report-supersession", "verification", "state"))
    args = parser.parse_args()
    actions = {
        "no-return-freeze": no_return_freeze,
        "attempt-ledger": attempt_ledger,
        "research-record": research_record,
        "report-supersession": report_supersession,
        "verification": verification,
        "state": state,
    }
    path = actions[args.stage]()
    print(json.dumps({"path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
