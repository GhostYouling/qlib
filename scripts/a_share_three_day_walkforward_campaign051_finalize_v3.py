#!/usr/bin/env python3
"""Publish additive Campaign051 full-suite infrastructure evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign051_finalize as base
import scripts.a_share_three_day_walkforward_campaign051_finalize_v2 as v2


ROOT = base.ROOT
FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_051_full_suite_cross_clone_failure_20260803.json"
TRANSITION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_post_result_test_transition_v3_20260803.json"
ATTEMPT_LEDGER = base.CROOT / "research_attempt_ledger_v3.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_051_research_record_v3.json"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_unified_report_supersession_v3_20260803.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_verification_v3_20260803.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign051_verified.json"
FINALIZER = Path(__file__).resolve()


def failure_record() -> Path:
    return base.write_new(FAILURE, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign051_full_suite_cross_clone_failure",
        "status": "full_suite_legacy_cross_clone_failures_recorded_campaign051_focused_green",
        "recorded_at": "2026-08-03T08:15:00Z",
        "test_run": {
            "command": "PYTHONPATH=. python -m pytest -q tests/data_collector_tests",
            "working_tree": "/Volumes/DIsk/Disk-Coding/qlib",
            "passed": 1709,
            "failed": 69,
            "warnings": 13,
            "duration_seconds": 164.27,
            "campaign051_focused_passed": 27,
            "campaign051_focused_failed": 0,
        },
        "root_cause_evidence": {
            "compatibility_path": "/Users/niyufei/Coding/qlib",
            "compatibility_path_exists": False,
            "only_extant_worktree": "/Volumes/DIsk/Disk-Coding/qlib",
            "dominant_failures": [
                "legacy ledgers and preregistrations bind absolute /Users/niyufei/Coding/qlib paths that cannot equal the current /Volumes path",
                "legacy terminal tests bind historical unified-report hashes superseded by later append-only report additions",
                "some old negative controls observe additive-wrapper module globals when the full suite shares one interpreter",
            ],
            "campaign051_factor_formula_gate_or_result_regression_observed": False,
        },
        "bindings": {
            "campaign051_research_record_v2": base.binding(v2.RESEARCH_RECORD),
            "post_result_test_transition_v2": base.binding(v2.TRANSITION),
            "current_campaign051_tests": base.binding(base.CAMPAIGN_TESTS),
            "current_campaign051_terminal_tests": base.binding(base.TERMINAL_TESTS),
        },
        "research_boundary": {
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    })


def transition() -> Path:
    return base.write_new(TRANSITION, {
        "version": 3,
        "kind": "a_share_three_day_walkforward_campaign051_post_result_test_transition",
        "status": "full_suite_infrastructure_failure_and_current_focused_assertions_bound",
        "recorded_at": "2026-08-03T08:16:00Z",
        "supersedes": base.binding(v2.TRANSITION),
        "bindings": {
            "full_suite_cross_clone_failure": base.binding(FAILURE),
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "current_terminal_tests": base.binding(base.TERMINAL_TESTS),
            "publisher": base.binding(FINALIZER),
        },
        "semantic_boundary": {
            "campaign051_focused_tests_passed": 27,
            "formula_direction_cost_fold_purge_or_gate_changed": False,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def attempt_ledger() -> Path:
    old = base.load(v2.ATTEMPT_LEDGER)
    entries = list(old["entries"])
    entries.append({
        "sequence": 11,
        "kind": "infrastructure_only_failure",
        "stage": "full_data_collector_cross_clone_validation",
        "recorded_at": "2026-08-03T08:15:00Z",
        "research_attempt_count_increment": 1,
        "development_trial_count_increment": 0,
        "outcome": "1709_passed_69_legacy_absolute_path_report_binding_or_shared_module_state_failures_campaign051_focused_27_passed",
        "evidence": base.binding(FAILURE),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    })
    return base.write_new(ATTEMPT_LEDGER, {
        **old,
        "schema_version": 3,
        "supersedes": base.binding(v2.ATTEMPT_LEDGER),
        "campaign051_ledger_entry_count": 11,
        "campaign051_attempt_count": 10,
        "campaign051_infrastructure_only_failure_count": 9,
        "cumulative_historical_research_attempt_count": 296,
        "entries": entries,
    })


def research_record() -> Path:
    old = base.load(v2.RESEARCH_RECORD)
    return base.write_new(RESEARCH_RECORD, {
        **old,
        "version": 3,
        "status": "completed_zero_development_survivors_stress_interval_not_opened_full_suite_cross_clone_failure_recorded",
        "recorded_at": "2026-08-03T08:17:00Z",
        "purpose": "Supersede only Campaign051 infrastructure accounting after the full legacy suite; preserve all factor values, returns, gates, and closed boundaries.",
        "supersedes": base.binding(v2.RESEARCH_RECORD),
        "full_suite_infrastructure_evidence": {
            "failure": base.binding(FAILURE),
            "post_result_test_transition_v3": base.binding(TRANSITION),
            "campaign051_focused_tests_passed": 27,
            "campaign051_focused_tests_failed": 0,
            "full_suite_passed": 1709,
            "full_suite_failed": 69,
            "full_suite_warnings": 13,
            "historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
        },
        "development_artifacts": {
            **old["development_artifacts"],
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "terminal_tests": base.binding(base.TERMINAL_TESTS),
            "research_attempt_ledger_v2_preserved": base.binding(v2.ATTEMPT_LEDGER),
            "research_attempt_ledger": {**base.binding(ATTEMPT_LEDGER), "campaign_attempt_count": 10, "ledger_entry_count": 11},
        },
        "attempt_accounting": {
            "infrastructure_only_failures": 9,
            "complete_factor_attempts": 1,
            "campaign_distinct_attempts": 10,
            "campaign_ledger_entries": 11,
            "cumulative_historical_research_attempts": 296,
            "campaign_return_reading_development_trials": 1,
            "cumulative_return_reading_development_trials": 266,
        },
    })


def report_supersession() -> Path:
    return base.write_new(REPORT_SUPERSESSION, {
        "version": 3,
        "kind": "a_share_three_day_walkforward_campaign051_unified_report_supersession",
        "status": "campaign051_prior_bindings_preserved_v3_infrastructure_accounting_current",
        "recorded_at": "2026-08-03T08:19:00Z",
        "bindings": {
            "campaign051_terminal_record_v2": base.binding(v2.RESEARCH_RECORD),
            "campaign051_terminal_record_v3": base.binding(RESEARCH_RECORD),
            "previous_unified_report_supersession": base.binding(v2.REPORT_SUPERSESSION),
            "full_suite_cross_clone_failure": base.binding(FAILURE),
            "current_unified_research_report": base.binding(base.REPORT),
        },
        "semantic_boundary": {
            "factor_result_or_gate_changed": False,
            "infrastructure_accounting_only": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def verification() -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    records = [RESEARCH_RECORD, TRANSITION, REPORT_SUPERSESSION]
    checked = [validator.validate_record(path, data_root=base.DATA_ROOT) for path in records]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Campaign051 v3 terminal bindings are not current")
    return base.write_new(VERIFICATION, {
        "version": 3,
        "kind": "a_share_three_day_walkforward_campaign051_verification",
        "status": "campaign051_focused_and_bindings_verified_full_legacy_suite_cross_clone_failures_recorded",
        "recorded_at": "2026-08-03T08:22:00Z",
        "bindings": {
            "research_record_v3": base.binding(RESEARCH_RECORD),
            "post_result_test_transition_v3": base.binding(TRANSITION),
            "unified_report_supersession_v3": base.binding(REPORT_SUPERSESSION),
            "research_attempt_ledger_v3": base.binding(ATTEMPT_LEDGER),
            "full_suite_cross_clone_failure": base.binding(FAILURE),
            "trial_ledger": base.binding(base.TRIAL_LEDGER),
            "development_survivors": base.binding(base.SURVIVORS),
            "unopened_stress_record": base.binding(base.STRESS),
            "campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "terminal_tests": base.binding(base.TERMINAL_TESTS),
            "unified_research_report": base.binding(base.REPORT),
            "candidate49_signal_ledger": base.binding(base.SIGNAL_LEDGER),
            "candidate49_execution_ledger": base.binding(base.EXECUTION_LEDGER),
        },
        "verification_summary": {
            "binding_records_checked": len(checked),
            "all_current_campaign051_bindings_passed": True,
            "focused_campaign051_tests_passed": 27,
            "focused_campaign051_tests_failed": 0,
            "full_data_collector_tests_passed": 1709,
            "full_data_collector_tests_failed": 69,
            "full_data_collector_test_warnings": 13,
            "full_suite_failures_classified_as_legacy_cross_clone_report_or_module_state": True,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign_research_attempt_count": 10,
            "campaign_ledger_entry_count": 11,
            "cumulative_historical_research_attempt_count": 296,
            "development_trial_count": 1,
            "cumulative_return_reading_development_trial_count": 266,
            "development_survivor_count": 0,
            "stress_2024_2025_opened": False,
            "stress_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    })


def state() -> Path:
    record = base.load(RESEARCH_RECORD)
    return base.write_new(STATE, {
        "version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign051_terminal_focused_verified_full_suite_cross_clone_failures_recorded_ready_for_independent_campaign052",
        "recorded_at": "2026-08-03T08:24:00Z",
        "authoritative_predecessor": base.binding(base.PREDECESSOR_STATE),
        "research_policy": {
            "historical_walkforward_policy": base.binding(base.POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
            "historical_results_may_generate_current_scores_selections_sizes_or_orders": False,
            "historical_results_may_backfill_candidate49": False,
        },
        "campaign051": {
            "factor": base.FACTOR,
            "direction": "higher",
            "no_return": record["no_return_result"],
            "development": {
                "trial_id": base.TRIAL_ID,
                "trial_count": 1,
                "validation_fold_results": base.validation_rows(),
                "development_aggregate_result": record["development_aggregate_result"],
                "development_survivor_count": 0,
                "2024_2025_stress_opened": False,
                "2024_2025_returns_read": False,
            },
            "attempt_accounting": record["attempt_accounting"],
            "terminal": record["decision"],
            "authoritative_records": {
                "research_record": base.binding(RESEARCH_RECORD),
                "verification": base.binding(VERIFICATION),
                "unified_report_supersession": base.binding(REPORT_SUPERSESSION),
            },
        },
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign051": 296,
            "cumulative_return_reading_development_trial_count_after_campaign051": 266,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_repository_root": "/Volumes/DIsk/Disk-Coding/qlib",
            "configured_compatibility_root": "/Users/niyufei/Coding/qlib",
            "configured_compatibility_root_exists": False,
            "active_daily_data_root": "/Volumes/DIsk/Disk-Coding/qlib/data",
            "local_date": "2026-08-03",
            "local_weekday": "Monday",
            "dotenv_path": "/Volumes/DIsk/Disk-Coding/qlib/.env",
            "dotenv_is_regular_non_symlink_file": True,
            "dotenv_is_git_ignored": True,
            "dotenv_mode": "0600",
            "tushare_token_present": True,
            "credential_value_printed_hashed_or_persisted_in_records": False,
            "provider_request_issued_by_campaign051_or_credential_verification": False,
        },
        "prospective_boundary": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "candidate49_signal_ledger": {**base.binding(base.SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**base.binding(base.EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "second_prospective_candidate_activation_allowed": False,
        },
        "verification_summary": base.load(VERIFICATION)["verification_summary"],
        "next_action": {
            "historical": "Begin Campaign052 only from an independent pre-value mechanism; offline work may run at any time.",
            "test_infrastructure": "Treat the 69 legacy failures as a separate cross-clone absolute-path/report-binding/module-state repair campaign; never rewrite immutable historical ledgers merely to make them pass.",
            "prospective": "Candidate49 remains the sole prospective candidate and retains the same-day post-16:30 ready=true boundary.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start a second prospective candidate",
                "do not invert repair rebin rewindow rescale filter threshold rerun rescue or combine Campaign051",
                "do not open Campaign051 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice",
            ],
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("failure-record", "transition", "attempt-ledger", "research-record", "report-supersession", "verification", "state"))
    args = parser.parse_args()
    actions = {
        "failure-record": failure_record,
        "transition": transition,
        "attempt-ledger": attempt_ledger,
        "research-record": research_record,
        "report-supersession": report_supersession,
        "verification": verification,
        "state": state,
    }
    path = actions[args.stage]()
    print(json.dumps({"path": str(path), "sha256": base.sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
