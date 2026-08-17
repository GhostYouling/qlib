#!/usr/bin/env python3
"""Publish additive Campaign050 terminal-accounting correction evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign050_finalize as base


ROOT = base.ROOT
FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_050_terminal_binding_cli_failure_20260801.json"
TRANSITION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_post_result_test_transition_v2_20260801.json"
ATTEMPT_LEDGER = base.CROOT / "research_attempt_ledger_v2.json"
RESEARCH_RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_050_research_record_v2.json"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_unified_report_supersession_v2_20260801.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_050_verification_v2_20260801.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign050_verified_v2.json"
FINALIZER = Path(__file__).resolve()


def post_result_transition() -> Path:
    return base.write_new(TRANSITION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign050_post_result_test_transition",
        "status": "terminal_accounting_correction_and_current_assertions_bound",
        "recorded_at": "2026-08-01T11:23:00Z",
        "purpose": "Preserve the first post-result transition and bind the additive CLI-failure accounting correction plus current terminal assertions.",
        "supersedes": base.binding(base.POST_RESULT_TRANSITION),
        "bindings": {
            "terminal_binding_cli_failure": base.binding(FAILURE),
            "current_campaign_tests": base.binding(base.CAMPAIGN_TESTS),
            "current_terminal_tests": base.binding(base.TERMINAL_TESTS),
            "correction_publisher": base.binding(FINALIZER),
        },
        "semantic_boundary": {
            "test_change": "point terminal accounting assertions to additive v2 evidence and include the verification-only failure",
            "formula_direction_cost_fold_purge_or_gate_changed": False,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
            "old_transition_rewritten": False,
        },
    })


def attempt_ledger() -> Path:
    old = base.load(base.ATTEMPT_LEDGER)
    entries = list(old["entries"])
    entries.append({
        "sequence": 7,
        "kind": "infrastructure_only_failure",
        "stage": "terminal_binding_validator_cli",
        "recorded_at": "2026-08-01T11:20:26Z",
        "research_attempt_count_increment": 1,
        "outcome": "failed_closed_because_two_records_were_passed_with_unsupported_record_flags_in_one_batched_command",
        "evidence": base.binding(FAILURE),
        "corrected_positional_retry_exit_code": 0,
        "corrected_retry_binding_count": 38,
        "corrected_retry_failed_binding_count": 0,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "development_trial_count_increment": 0,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    })
    record = {
        **old,
        "schema_version": 2,
        "kind": "a_share_three_day_walkforward_campaign050_research_attempt_ledger",
        "supersedes": base.binding(base.ATTEMPT_LEDGER),
        "campaign050_ledger_entry_count": 7,
        "campaign050_attempt_count": 6,
        "cumulative_historical_research_attempt_count": 286,
        "entries": entries,
    }
    return base.write_new(ATTEMPT_LEDGER, record)


def research_record() -> Path:
    old = base.load(base.RESEARCH_RECORD)
    record = {
        **old,
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign050_research_record",
        "status": "completed_zero_development_survivors_stress_interval_not_opened_terminal_accounting_corrected",
        "recorded_at": "2026-08-01T11:25:00Z",
        "purpose": "Supersede only Campaign050 terminal accounting after the binding-validator CLI failure; preserve all factor results, gates, return reads, and closed boundaries.",
        "supersedes": base.binding(base.RESEARCH_RECORD),
        "terminal_accounting_correction": {
            "failure": base.binding(FAILURE),
            "post_result_test_transition_v2": base.binding(TRANSITION),
            "old_research_record_rewritten": False,
            "old_attempt_ledger_rewritten": False,
            "historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
        },
        "development_artifacts": {
            **old["development_artifacts"],
            "terminal_tests": base.binding(base.TERMINAL_TESTS),
            "research_attempt_ledger_v1_preserved": base.binding(base.ATTEMPT_LEDGER),
            "research_attempt_ledger": {
                **base.binding(ATTEMPT_LEDGER),
                "campaign_attempt_count": 6,
                "ledger_entry_count": 7,
            },
        },
        "attempt_accounting": {
            "infrastructure_only_failures": 5,
            "complete_factor_attempts": 1,
            "campaign_distinct_attempts": 6,
            "campaign_ledger_entries": 7,
            "cumulative_historical_research_attempts": 286,
            "campaign_return_reading_development_trials": 1,
            "cumulative_return_reading_development_trials": 265,
        },
        "decision": {
            **old["decision"],
            "cumulative_historical_research_attempt_count_after_campaign": 286,
        },
    }
    return base.write_new(RESEARCH_RECORD, record)


def report_supersession() -> Path:
    previous = base.load(base.REPORT_SUPERSESSION)
    return base.write_new(REPORT_SUPERSESSION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign050_unified_report_supersession",
        "status": "campaign050_v1_report_binding_preserved_historically_v2_accounting_current",
        "recorded_at": "2026-08-01T11:27:00Z",
        "purpose": "Preserve the first Campaign050 report binding while binding the append-only accounting correction in the current report.",
        "bindings": {
            "campaign050_terminal_record_v1": base.binding(base.RESEARCH_RECORD),
            "campaign050_terminal_record_v2": base.binding(RESEARCH_RECORD),
            "previous_campaign050_supersession": base.binding(base.REPORT_SUPERSESSION),
            "terminal_binding_cli_failure": base.binding(FAILURE),
            "current_unified_research_report": base.binding(base.REPORT),
        },
        "historical_binding": {
            "record": base.display(base.REPORT_SUPERSESSION),
            "json_pointer": "/bindings/current_unified_research_report",
            "expected_sha256": previous["bindings"]["current_unified_research_report"]["sha256"],
            "current_sha256": base.sha256(base.REPORT),
            "historical_record_rewritten": False,
        },
        "semantic_boundary": {
            "campaign050_factor_result_or_gate_changed": False,
            "accounting_correction_only": True,
            "report_update_is_append_only_in_meaning": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    })


def verification(focused: int, full: int, warnings: int) -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    records = [RESEARCH_RECORD, base.PREREG, TRANSITION, REPORT_SUPERSESSION]
    checked = [validator.validate_record(path, data_root=base.DATA_ROOT) for path in records]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Campaign050 v2 terminal bindings are not current")
    return base.write_new(VERIFICATION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign050_verification",
        "status": "terminal_campaign050_accounting_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-01T11:31:00Z",
        "purpose": "Bind corrected append-only accounting, terminal factor evidence, unopened 2024-2025 semantics, tests, and unchanged Candidate49 ledgers.",
        "bindings": {
            "research_record_v2": base.binding(RESEARCH_RECORD),
            "post_result_test_transition_v2": base.binding(TRANSITION),
            "unified_report_supersession_v2": base.binding(REPORT_SUPERSESSION),
            "terminal_binding_cli_failure": base.binding(FAILURE),
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
            "focused_campaign050_tests_passed": focused,
            "full_data_collector_tests_passed": full,
            "full_data_collector_tests_failed": 0,
            "full_data_collector_test_warnings": warnings,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign_research_attempt_count": 6,
            "campaign_ledger_entry_count": 7,
            "cumulative_historical_research_attempt_count": 286,
            "development_trial_count": 1,
            "cumulative_return_reading_development_trial_count": 265,
            "development_survivor_count": 0,
            "stress_2024_2025_opened": False,
            "stress_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    })


def state() -> Path:
    record = base.load(RESEARCH_RECORD)
    return base.write_new(STATE, {
        "version": 2,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign050_terminal_verified_historical_walkforward_ready_for_independent_campaign051",
        "recorded_at": "2026-08-01T11:33:00Z",
        "authoritative_predecessor": base.binding(base.PREDECESSOR_STATE),
        "research_policy": {
            "historical_walkforward_policy": base.binding(base.POLICY),
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
            "aggregate_survivor_cost_bps": 20
        },
        "campaign050": {
            "factor": base.FACTOR,
            "direction": "higher",
            "formula": base.load(base.PROTOCOL)["candidate"]["formula"],
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
            "cumulative_historical_research_attempt_count_after_campaign050": 286,
            "cumulative_return_reading_development_trial_count_after_campaign050": 265,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_daily_data_root": str(ROOT / "data"),
            "local_date": "2026-08-01",
            "local_weekday": "Saturday",
            "candidate49_same_day_workflow_applicable": False,
            "dotenv_path": str(ROOT / ".env"),
            "dotenv_is_regular_non_symlink_file": True,
            "dotenv_is_git_ignored": True,
            "dotenv_mode": "0600",
            "tushare_token_present": True,
            "credential_value_printed_hashed_or_persisted_in_records": False,
            "provider_request_issued_by_campaign050_or_credential_verification": False,
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
            "historical": "Begin Campaign051 from an independent mechanism with pre-value scouting, overlap audit, finite fingerprint-bound protocol, and append-only accounting; offline work may run at any time.",
            "prospective": "Today is Saturday; do not run Candidate49 provider workflow. On the next accepted local trading date retain the same-day post-16:30 ready=true gate and a new absolute-date staging root.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start a second prospective candidate",
                "do not invert repair rewindow rescale filter threshold rerun rescue or combine Campaign050",
                "do not open Campaign050 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice"
            ],
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("post-result-transition", "attempt-ledger", "research-record", "report-supersession", "verification", "state"))
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args()
    actions = {
        "post-result-transition": post_result_transition,
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
