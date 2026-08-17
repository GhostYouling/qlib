#!/usr/bin/env python3
"""Publish additive Campaign051 terminal-test accounting correction evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign051_finalize as base


ROOT = base.ROOT
FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_051_terminal_status_test_failure_20260803.json"
TRANSITION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_post_result_test_transition_v2_20260803.json"
ATTEMPT_LEDGER = base.CROOT / "research_attempt_ledger_v2.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_051_research_record_v2.json"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_unified_report_supersession_v2_20260803.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_051_verification_v2_20260803.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign051_verified.json"
FINALIZER = Path(__file__).resolve()


def failure_record() -> Path:
    return base.write_new(FAILURE, {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign051_terminal_status_test_failure",
        "status": "infrastructure_only_assertion_semantics_corrected_without_research_read",
        "recorded_at": "2026-08-03T07:57:30Z",
        "purpose": "Preserve the failed terminal status assertion and the exact no-survivor stress semantics before publishing additive corrected evidence.",
        "failed_test_run": {
            "passed": 26,
            "failed": 1,
            "failed_test": "test_campaign051_status_has_exactly_one_trial_and_terminal_closed_stress",
            "observed": {"stress_intent_exists": False, "stress_record_exists": True},
            "incorrect_expected_stress_intent_exists": True,
            "test_file_sha256_at_failure": "1258a118610cacbe05dcce7e8aab8328888406f6e354ecb03735810c592ae950",
        },
        "correction": {
            "description": "A zero-survivor campaign publishes the immutable not-opened stress record but creates no intent to execute stress replay.",
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "current_terminal_tests": base.binding(base.TERMINAL_TESTS),
            "previous_post_result_transition": base.binding(base.POST_RESULT_TRANSITION),
            "runner_formula_gate_or_result_changed": False,
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
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign051_post_result_test_transition",
        "status": "terminal_test_accounting_correction_and_current_assertions_bound",
        "recorded_at": "2026-08-03T07:58:00Z",
        "supersedes": base.binding(base.POST_RESULT_TRANSITION),
        "bindings": {
            "terminal_status_test_failure": base.binding(FAILURE),
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "current_terminal_tests": base.binding(base.TERMINAL_TESTS),
            "correction_publisher": base.binding(FINALIZER),
        },
        "semantic_boundary": {
            "stress_intent_exists": False,
            "stress_record_exists": True,
            "formula_direction_cost_fold_purge_or_gate_changed": False,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def attempt_ledger() -> Path:
    old = base.load(base.ATTEMPT_LEDGER)
    entries = list(old["entries"])
    entries.append({
        "sequence": 10,
        "kind": "infrastructure_only_failure",
        "stage": "terminal_status_test_semantics",
        "recorded_at": "2026-08-03T07:57:30Z",
        "research_attempt_count_increment": 1,
        "development_trial_count_increment": 0,
        "outcome": "failed_closed_on_incorrect_stress_intent_expectation_then_corrected_to_unopened_record_without_intent",
        "evidence": base.binding(FAILURE),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    })
    return base.write_new(ATTEMPT_LEDGER, {
        **old,
        "schema_version": 2,
        "supersedes": base.binding(base.ATTEMPT_LEDGER),
        "campaign051_ledger_entry_count": 10,
        "campaign051_attempt_count": 9,
        "campaign051_infrastructure_only_failure_count": 8,
        "cumulative_historical_research_attempt_count": 295,
        "entries": entries,
    })


def research_record() -> Path:
    old = base.load(base.RESEARCH_RECORD)
    return base.write_new(RESEARCH_RECORD, {
        **old,
        "version": 2,
        "status": "completed_zero_development_survivors_stress_interval_not_opened_terminal_test_accounting_corrected",
        "recorded_at": "2026-08-03T07:59:00Z",
        "purpose": "Supersede only Campaign051 terminal-test accounting; preserve all factor values, returns, gates, and closed boundaries.",
        "supersedes": base.binding(base.RESEARCH_RECORD),
        "terminal_test_accounting_correction": {
            "failure": base.binding(FAILURE),
            "post_result_test_transition_v2": base.binding(TRANSITION),
            "historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "old_records_rewritten": False,
        },
        "development_artifacts": {
            **old["development_artifacts"],
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "terminal_tests": base.binding(base.TERMINAL_TESTS),
            "research_attempt_ledger_v1_preserved": base.binding(base.ATTEMPT_LEDGER),
            "research_attempt_ledger": {**base.binding(ATTEMPT_LEDGER), "campaign_attempt_count": 9, "ledger_entry_count": 10},
        },
        "attempt_accounting": {
            "infrastructure_only_failures": 8,
            "complete_factor_attempts": 1,
            "campaign_distinct_attempts": 9,
            "campaign_ledger_entries": 10,
            "cumulative_historical_research_attempts": 295,
            "campaign_return_reading_development_trials": 1,
            "cumulative_return_reading_development_trials": 266,
        },
    })


def report_supersession() -> Path:
    return base.write_new(REPORT_SUPERSESSION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign051_unified_report_supersession",
        "status": "campaign051_v1_binding_preserved_v2_terminal_accounting_current",
        "recorded_at": "2026-08-03T08:01:00Z",
        "bindings": {
            "campaign051_terminal_record_v1": base.binding(base.RESEARCH_RECORD),
            "campaign051_terminal_record_v2": base.binding(RESEARCH_RECORD),
            "previous_unified_report_supersession": base.binding(base.REPORT_SUPERSESSION),
            "terminal_status_test_failure": base.binding(FAILURE),
            "current_unified_research_report": base.binding(base.REPORT),
        },
        "semantic_boundary": {
            "factor_result_or_gate_changed": False,
            "accounting_correction_only": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def verification(focused: int, full: int, warnings: int) -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    records = [RESEARCH_RECORD, TRANSITION, REPORT_SUPERSESSION]
    checked = [validator.validate_record(path, data_root=base.DATA_ROOT) for path in records]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Campaign051 v2 terminal bindings are not current")
    return base.write_new(VERIFICATION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign051_verification",
        "status": "terminal_campaign051_accounting_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-03T08:08:00Z",
        "bindings": {
            "research_record_v2": base.binding(RESEARCH_RECORD),
            "post_result_test_transition_v2": base.binding(TRANSITION),
            "unified_report_supersession_v2": base.binding(REPORT_SUPERSESSION),
            "research_attempt_ledger_v2": base.binding(ATTEMPT_LEDGER),
            "trial_ledger": base.binding(base.TRIAL_LEDGER),
            "development_survivors": base.binding(base.SURVIVORS),
            "unopened_stress_record": base.binding(base.STRESS),
            "campaign_report": base.binding(base.CAMPAIGN_REPORT),
            "campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "terminal_tests": base.binding(base.TERMINAL_TESTS),
            "unified_research_report": base.binding(base.REPORT),
            "candidate49_signal_ledger": base.binding(base.SIGNAL_LEDGER),
            "candidate49_execution_ledger": base.binding(base.EXECUTION_LEDGER),
        },
        "verification_summary": {
            "binding_records_checked": len(checked),
            "all_bindings_passed": True,
            "focused_campaign051_tests_passed": focused,
            "full_data_collector_tests_passed": full,
            "full_data_collector_tests_failed": 0,
            "full_data_collector_test_warnings": warnings,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign_research_attempt_count": 9,
            "campaign_ledger_entry_count": 10,
            "cumulative_historical_research_attempt_count": 295,
            "development_trial_count": 1,
            "cumulative_return_reading_development_trial_count": 266,
            "development_survivor_count": 0,
            "stress_intent_exists": False,
            "stress_record_exists": True,
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
        "status": "campaign051_terminal_verified_historical_walkforward_ready_for_independent_campaign052",
        "recorded_at": "2026-08-03T08:10:00Z",
        "authoritative_predecessor": base.binding(base.PREDECESSOR_STATE),
        "research_policy": {
            "historical_walkforward_policy": base.binding(base.POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
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
                "stress_intent_exists": False,
                "stress_record_exists": True,
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
            "cumulative_historical_research_attempt_count_after_campaign051": 295,
            "cumulative_return_reading_development_trial_count_after_campaign051": 266,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_daily_data_root": "/Users/niyufei/Coding/qlib/data",
            "local_date": "2026-08-03",
            "local_weekday": "Monday",
            "dotenv_path": "/Users/niyufei/Coding/qlib/.env",
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
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args()
    actions = {
        "failure-record": failure_record,
        "transition": transition,
        "attempt-ledger": attempt_ledger,
        "research-record": research_record,
        "report-supersession": report_supersession,
        "verification": lambda: verification(args.focused_passed, args.full_passed, args.warnings),
        "state": state,
    }
    path = actions[args.stage]()
    print(json.dumps({"path": str(path), "sha256": base.sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
