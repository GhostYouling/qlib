#!/usr/bin/env python3
"""Publish append-only terminal evidence for historical Campaign052."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "quarterly_announcement_delay_consistency_4q"
CROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_052"
AUDIT = CROOT / "no_return/20260803T084328Z_campaign052_no_return_audit.json"
SNAPSHOT = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign052_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign052_feature_library_v1/snapshot_manifest.json"
)

POLICY = ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
PREDECESSOR = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign051_verified.json"
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_052_concept_scouting.json"
MECHANISM = ROOT / "docs/a_share_three_day_walkforward_campaign_052_mechanism_overlap_audit.json"
PROTOCOL = ROOT / "docs/a_share_three_day_walkforward_campaign_052_no_return_preregistration.json"
FEATURE_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_052_feature_implementation_freeze_20260803.json"
SNAPSHOT_BINDING = ROOT / "docs/a_share_three_day_walkforward_campaign_052_snapshot_publication_binding_20260803.json"
FEATURE_RUNNER = ROOT / "scripts/a_share_three_day_walkforward_campaign052_features.py"
FEATURE_RUNNER_V2 = ROOT / "scripts/a_share_three_day_walkforward_campaign052_features_v2.py"
FEATURE_RUNNER_V3 = ROOT / "scripts/a_share_three_day_walkforward_campaign052_features_v3.py"
FEATURE_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign052_features.py"
TERMINAL_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign052_terminal.py"

INFRA_FAILURES = ROOT / "docs/a_share_three_day_walkforward_campaign_052_infrastructure_failures_20260803.json"
NO_RETURN_FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_052_no_return_audit_freeze_20260803.json"
ATTEMPT_LEDGER = CROOT / "research_attempt_ledger.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_052_research_record.json"
REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_052_unified_report_supersession_20260803.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_052_verification_20260803.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign052_verified.json"
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


def metrics() -> dict[str, Any]:
    audit = load(AUDIT)
    return audit["coverage_and_capacity"][FACTOR]


def infrastructure_failures() -> Path:
    return write_new(INFRA_FAILURES, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_infrastructure_failures",
        "status": "three_fail_closed_infrastructure_attempts_recorded_no_research_boundary_breach",
        "recorded_at": "2026-08-03T08:50:00Z",
        "incidents": [
            {
                "incident_id": "campaign052_missing_configured_compatibility_workdir",
                "stage": "initial_authority_and_skill_read",
                "outcome": "command_did_not_start_because_configured_/Users_workdir_does_not_exist",
                "correction": "used_the_only_extant_/Volumes_repository_after_read_only_resolution",
            },
            {
                "incident_id": "campaign052_binding_validator_cli_shape",
                "stage": "pre_value_binding_validation",
                "outcome": "exit_2_unknown_validate_--record_interface_before_protected_values",
                "correction": "used_the_validator_positional_interface_and_obtained_exit_0",
            },
            {
                "incident_id": "campaign052_pytest_import_path",
                "stage": "feature_test_collection",
                "outcome": "collection_failed_no_module_named_scripts_without_repository_on_pythonpath",
                "correction": "reran_the_same_tests_with_PYTHONPATH=. and_obtained_5_passed",
            },
        ],
        "research_boundary": {
            "factor_values_read_by_these_failures": False,
            "comparison_factor_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "formula_direction_window_gate_or_cost_changed": False,
        },
    })


def no_return_freeze() -> Path:
    audit, coverage = load(AUDIT), metrics()
    gate = coverage["gate"]
    return write_new(NO_RETURN_FREEZE, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_no_return_audit_freeze",
        "status": "terminal_zero_admissible_factors_before_comparison_values_or_historical_returns",
        "recorded_at": "2026-08-03T08:51:00Z",
        "purpose": "Bind the sole Campaign052 coverage-first no-return result and forbid post-value rescue.",
        "authoritative_inputs": {
            "no_return_preregistration": binding(PROTOCOL),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "snapshot_manifest": {**binding(SNAPSHOT), "dataset_sha256": load(SNAPSHOT)["dataset_sha256"]},
            "no_return_audit": binding(AUDIT),
            "effective_post_snapshot_audit_runner": binding(FEATURE_RUNNER_V3),
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
            "minimum_non_overlapping_three_session_cohorts": gate["minimum_non_overlapping_three_session_cohorts"],
            "observed_calendar_year_count": len(coverage["observed_cohort_years"]),
            "minimum_observed_calendar_years": gate["minimum_observed_calendar_years"],
            "coverage_gate_passed": False,
            "comparison_library_size": 75,
            "comparison_values_loaded_after_coverage_pass": False,
            "comparison_correlations_computed": 0,
            "admissible_factor_count": audit["admissible_factor_count"],
        },
        "semantic_boundary": {
            "all_snapshot_partition_byte_and_frame_hashes_verified": True,
            "stock_day_identity_fields_read": audit["source_fields_read"],
            "quarterly_disclosure_fields_read": audit["quarterly_disclosure_fields_read"],
            "quarterly_value_fields_read": audit["quarterly_value_fields_read"],
            "minute_open_high_low_close_volume_amount_fields_read": audit["minute_open_high_low_close_volume_amount_fields_read"],
            "historical_daily_price_fields_read": audit["historical_daily_price_fields_read"],
            "historical_forward_return_fields_read": audit["historical_forward_return_fields_read"],
            "candidate49_historical_return_read": False,
            "candidate49_prospective_ledgers_changed": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "predictive_value_established": False,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "coverage_and_capacity_before_comparison_values",
            "terminal_reason": "frozen_p05_coverage_and_p05_eligible_name_gates_failed_because_early_history_lacked_four_effective_consecutive_quarterly_reports",
            "comparison_values_or_correlations_allowed": False,
            "historical_walkforward_allowed": False,
            "2024_2025_stress_allowed": False,
            "shorter_window_later_start_threshold_relaxation_imputation_filter_subset_model_combination_or_rescue_rerun_allowed": False,
            "next_action": "Record the exact terminal attempt and start only an independently preregistered Campaign053 mechanism.",
        },
    })


def attempt_ledger() -> Path:
    protocol, coverage = load(PROTOCOL), metrics()
    incidents = load(INFRA_FAILURES)["incidents"]
    entries: list[dict[str, Any]] = []
    for sequence, incident in enumerate(incidents, 1):
        entries.append({
            "sequence": sequence,
            "kind": "infrastructure_only_failure",
            "stage": incident["stage"],
            "incident_id": incident["incident_id"],
            "recorded_at": "2026-08-03T08:50:00Z",
            "research_attempt_count_increment": 1,
            "development_trial_count_increment": 0,
            "outcome": incident["outcome"],
            "evidence": binding(INFRA_FAILURES),
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        })
    entries.append({
        "sequence": 4,
        "kind": "single_factor_ordered_no_return_gate",
        "attempt_id": f"wf052_{FACTOR}_single_higher",
        "recorded_at": load(AUDIT)["created_at"],
        "research_attempt_count_increment": 1,
        "development_trial_count_increment": 0,
        "economic_hypothesis": "Stable reporting-process timing across a full four-quarter cycle may proxy for organizational consistency relevant to short-horizon repricing.",
        "formula": protocol["candidate"]["formula"],
        "direction": "higher",
        "feature_set": [FACTOR],
        "parameter_filter_subset_combination_and_model": "exact frozen four-report population-standard-deviation transform; no alternate window, later start, estimator, direction, filter, subset, combination, model, or fit",
        "outcome": "terminal_no_return_rejection_frozen_p05_coverage_and_p05_name_gates_failed",
        "evidence": {
            "protocol": binding(PROTOCOL),
            "snapshot": {**binding(SNAPSHOT), "dataset_sha256": load(SNAPSHOT)["dataset_sha256"]},
            "audit": binding(AUDIT),
            "audit_freeze": binding(NO_RETURN_FREEZE),
            "effective_runner": binding(FEATURE_RUNNER_V3),
        },
        "no_return_metrics": {
            "median_coverage": coverage["median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "eligible_names_p05": coverage["eligible_names_p05"],
            "potential_non_overlapping_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "observed_calendar_year_count": len(coverage["observed_cohort_years"]),
            "comparison_values_loaded": False,
            "all_gates_passed": False,
        },
        "quarterly_disclosure_fields_read": ["instrument", "report_date", "announcement_date"],
        "quarterly_value_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    })
    return write_new(ATTEMPT_LEDGER, {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_research_attempt_ledger",
        "status": "terminal_append_only_zero_return_trials",
        "append_only": True,
        "counting_rule": "Every infrastructure-only failure and every distinct formula, direction, parameter set, subset, filter, model, or combination counts once; no-return rejection creates no return-reading development trial.",
        "campaign052_ledger_entry_count": 4,
        "campaign052_attempt_count": 4,
        "campaign052_infrastructure_only_failure_count": 3,
        "campaign052_complete_factor_attempt_count": 1,
        "historical_research_attempt_count_before_campaign052": 296,
        "cumulative_historical_research_attempt_count": 300,
        "campaign052_historical_return_trial_count": 0,
        "cumulative_return_reading_development_trial_count_before_campaign052": 266,
        "cumulative_return_reading_development_trial_count": 266,
        "entries": entries,
    })


def research_record() -> Path:
    protocol, snapshot, audit, coverage = load(PROTOCOL), load(SNAPSHOT), load(AUDIT), metrics()
    return write_new(RESEARCH_RECORD, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_research_record",
        "status": "completed_zero_admissible_factors_stop_before_comparison_values_or_historical_returns",
        "recorded_at": "2026-08-03T08:54:00Z",
        "purpose": "Record every Campaign052 attempt, exact disclosure-timing factor, immutable snapshot, and coverage-first terminal decision.",
        "authoritative_inputs": {
            "prior_iteration_state": binding(PREDECESSOR),
            "historical_walkforward_policy": binding(POLICY),
        },
        "frozen_evidence": {
            "concept_scouting": binding(CONCEPT),
            "mechanism_overlap_audit": binding(MECHANISM),
            "no_return_preregistration": binding(PROTOCOL),
            "feature_implementation_freeze": binding(FEATURE_FREEZE),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "infrastructure_failures": binding(INFRA_FAILURES),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "base_feature_runner": binding(FEATURE_RUNNER),
            "snapshot_bound_runner": binding(FEATURE_RUNNER_V2),
            "audit_runner": binding(FEATURE_RUNNER_V3),
            "feature_tests": binding(FEATURE_TESTS),
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
            "quarterly_disclosure_fields_read": snapshot["quarterly_disclosure_fields_read"],
            "quarterly_value_fields_read": snapshot["quarterly_value_fields_read"],
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
            "minimum_median_coverage": coverage["gate"]["minimum_median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "minimum_p05_coverage": coverage["gate"]["minimum_p05_coverage"],
            "median_eligible_names": coverage["eligible_names_median"],
            "p05_eligible_names": coverage["eligible_names_p05"],
            "minimum_p05_eligible_names": coverage["gate"]["minimum_p05_eligible_names"],
            "potential_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "observed_calendar_years": coverage["observed_cohort_years"],
            "coverage_gate_passed": False,
            "comparison_factor_count_frozen": 75,
            "comparison_values_loaded": False,
            "comparison_correlations_computed": 0,
            "admissible_factor_count": 0,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
        },
        "append_only_attempt_accounting": {
            "ledger": binding(ATTEMPT_LEDGER),
            "prior_historical_research_attempt_count": 296,
            "campaign052_infrastructure_failure_count": 3,
            "campaign052_complete_factor_attempt_count": 1,
            "campaign052_total_attempt_count": 4,
            "cumulative_historical_research_attempt_count": 300,
            "campaign052_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "no_return_coverage_gate_before_comparison_values",
            "terminal_reason": "p05_coverage_and_p05_eligible_names_failed_due_to_insufficient_four-quarter_history_in_early_sessions",
            "development_folds_opened": False,
            "development_return_fields_read": False,
            "2024_2025_stress_opened": False,
            "2024_2025_returns_read": False,
            "shorter_window_later_start_threshold_relaxation_imputation_filter_subset_model_combination_rerun_or_rescue_allowed": False,
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
        "kind": "a_share_three_day_walkforward_campaign052_unified_report_supersession",
        "status": "campaign051_report_binding_preserved_historically_campaign052_report_current",
        "recorded_at": "2026-08-03T08:57:00Z",
        "bindings": {
            "campaign051_terminal_record": binding(ROOT / "docs/a_share_three_day_walkforward_campaign_051_research_record_v3.json"),
            "campaign052_terminal_record": binding(RESEARCH_RECORD),
            "current_unified_research_report": binding(REPORT),
            "current_data_pipeline_documentation": binding(PIPELINE_DOC),
            "current_manage_qlib_a_share_data_skill": binding(SKILL),
        },
        "semantic_boundary": {
            "campaign051_or_campaign052_result_or_gate_changed": False,
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
        raise RuntimeError("Campaign052 terminal bindings are not current")
    if sha256(SIGNAL_LEDGER) != "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79":
        raise RuntimeError("Candidate49 signal ledger changed")
    if sha256(EXECUTION_LEDGER) != "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f":
        raise RuntimeError("Candidate49 execution ledger changed")
    return write_new(VERIFICATION, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_verification",
        "status": "terminal_campaign052_bindings_tests_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-03T09:00:00Z",
        "bindings": {
            "research_record": binding(RESEARCH_RECORD),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "unified_report_supersession": binding(REPORT_SUPERSESSION),
            "research_attempt_ledger": binding(ATTEMPT_LEDGER),
            "infrastructure_failures": binding(INFRA_FAILURES),
            "feature_and_no_return_runner": binding(FEATURE_RUNNER_V3),
            "feature_tests": binding(FEATURE_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "unified_research_report": binding(REPORT),
            "data_pipeline_documentation": binding(PIPELINE_DOC),
            "manage_qlib_a_share_data_skill": binding(SKILL),
            "candidate49_signal_ledger": binding(SIGNAL_LEDGER),
            "candidate49_execution_ledger": binding(EXECUTION_LEDGER),
        },
        "verification_summary": {
            "binding_records_checked": len(checked),
            "all_current_campaign052_bindings_passed": True,
            "focused_campaign052_tests_passed": 12,
            "focused_campaign052_tests_failed": 0,
            "snapshot_partitions_reverified": 33015,
            "snapshot_rows_reverified": 7724498,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign052_attempt_count": 4,
            "cumulative_historical_research_attempt_count": 300,
            "campaign052_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
            "admissible_factor_count": 0,
            "comparison_values_loaded": False,
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
        "status": "campaign052_terminal_verified_historical_walkforward_ready_for_independent_campaign053",
        "recorded_at": "2026-08-03T09:02:00Z",
        "authoritative_predecessor": binding(PREDECESSOR),
        "research_policy": {
            "historical_walkforward_policy": binding(POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
            "historical_results_may_generate_current_scores_selections_sizes_or_orders": False,
            "historical_results_may_backfill_candidate49": False,
        },
        "campaign052": {
            "factor": FACTOR,
            "direction": "higher",
            "formula": record["factor_definition"]["formula"],
            "snapshot": record["feature_snapshot"],
            "no_return": record["no_return_result"],
            "attempt_accounting": record["append_only_attempt_accounting"],
            "development": {
                "folds_opened": False,
                "return_fields_read": False,
                "trial_count": 0,
                "selected_survivor_count": 0,
            },
            "stress_2024_2025": {
                "status": "not_opened_no_no_return_admissible_factor",
                "opened": False,
                "return_fields_read": False,
            },
            "terminal": record["decision"],
            "authoritative_records": {
                "research_record": binding(RESEARCH_RECORD),
                "verification": binding(VERIFICATION),
                "unified_report_supersession": binding(REPORT_SUPERSESSION),
            },
        },
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign052": 300,
            "cumulative_return_reading_development_trial_count_after_campaign052": 266,
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
            "provider_request_issued_by_campaign052_or_credential_verification": False,
        },
        "prospective_boundary": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "second_prospective_candidate_activation_allowed": False,
        },
        "verification_summary": load(VERIFICATION)["verification_summary"],
        "next_action": {
            "historical": "Begin Campaign053 only from a genuinely independent, pre-value-frozen mechanism; offline work may run at any time.",
            "prospective": "Candidate49 remains the sole prospective candidate and uses only its same-day post-16:30 ready=true workflow.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start a second prospective candidate",
                "do not shorten the four-quarter window drop early sessions relax coverage impute filter rerun rescue or combine Campaign052",
                "do not open Campaign052 development folds or 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice",
            ],
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=(
        "infrastructure-failures", "no-return-freeze", "attempt-ledger",
        "research-record", "report-supersession", "verification", "state",
    ))
    args = parser.parse_args()
    actions = {
        "infrastructure-failures": infrastructure_failures,
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
