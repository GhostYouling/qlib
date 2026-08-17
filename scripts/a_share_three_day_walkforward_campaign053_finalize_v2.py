#!/usr/bin/env python3
"""Advance Campaign053 terminal evidence after the preserved report assertion failure."""

from __future__ import annotations

import argparse
import json

try:
    import scripts.a_share_three_day_walkforward_campaign053_finalize as base
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_finalize as base


ROOT = base.ROOT
FAILURE = ROOT / "docs/a_share_three_day_walkforward_campaign_053_terminal_report_assertion_failure_20260803.json"
CURRENT_TESTS = ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign053_terminal_v2.py"
FINALIZER = ROOT / "scripts/a_share_three_day_walkforward_campaign053_finalize_v2.py"
PRIOR_LEDGER = base.ATTEMPT_LEDGER
PRIOR_RECORD = base.RESEARCH_RECORD
PRIOR_REPORT_SUPERSESSION = base.REPORT_SUPERSESSION
PRIOR_VERIFICATION = base.VERIFICATION
PRIOR_STATE = base.STATE
LEDGER = base.CROOT / "research_attempt_ledger_v2.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_053_research_record_v2.json"
REPORT_SUPERSESSION = ROOT / "docs/a_share_three_day_walkforward_campaign_053_unified_report_supersession_20260803_v2.json"
VERIFICATION = ROOT / "docs/a_share_three_day_walkforward_campaign_053_verification_20260803_v2.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign053_verified_v2.json"


def ledger() -> base.Path:
    return base.write_new(LEDGER, {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_research_attempt_ledger_v2",
        "status": "terminal_append_only_post_result_test_failure_recorded",
        "append_only": True,
        "prior_ledger": base.binding(PRIOR_LEDGER),
        "counting_rule": "Preserve the two original Campaign053 attempts and add every post-result infrastructure-only failure once; no test failure creates a return-reading development trial.",
        "campaign053_ledger_entry_count": 3,
        "campaign053_attempt_count": 3,
        "campaign053_infrastructure_only_failure_count": 2,
        "campaign053_complete_factor_attempt_count": 1,
        "historical_research_attempt_count_before_campaign053": 300,
        "cumulative_historical_research_attempt_count": 303,
        "campaign053_historical_return_trial_count": 0,
        "cumulative_return_reading_development_trial_count_before_campaign053": 266,
        "cumulative_return_reading_development_trial_count": 266,
        "post_terminal_delta_entries": [{
            "sequence": 3,
            "kind": "infrastructure_only_failure",
            "stage": "terminal_focused_test_report_literal_assertion",
            "incident_id": "campaign053_terminal_test_omitted_positive_direction_sign",
            "recorded_at": base.load(FAILURE)["recorded_at"],
            "research_attempt_count_increment": 1,
            "development_trial_count_increment": 0,
            "outcome": "15_passed_1_failed_exact_report_literal_assertion",
            "correction": "preserve_v1_test_and_add_current_v2_test_for_exact_signed_literal",
            "evidence": base.binding(FAILURE),
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }],
    })


def record() -> base.Path:
    prior = base.load(PRIOR_RECORD)
    return base.write_new(RECORD, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign053_research_record",
        "status": "completed_zero_admissible_factors_post_terminal_test_failure_recorded",
        "recorded_at": "2026-08-03T13:03:00Z",
        "purpose": "Advance only post-result test and attempt accounting while preserving the immutable Campaign053 no-return result.",
        "authoritative_predecessors": {
            "research_record_v1": base.binding(PRIOR_RECORD),
            "verification_v1_historical": base.binding(PRIOR_VERIFICATION),
            "iteration_state_v1_historical": base.binding(PRIOR_STATE),
        },
        "post_result_infrastructure": {
            "terminal_report_assertion_failure": base.binding(FAILURE),
            "current_terminal_tests": base.binding(CURRENT_TESTS),
            "current_attempt_ledger": base.binding(LEDGER),
            "current_finalizer": base.binding(FINALIZER),
            "factor_formula_direction_snapshot_audit_comparisons_gates_or_decision_changed": False,
        },
        "canonical_campaign053_result": {
            "factor_definition": prior["factor_definition"],
            "feature_snapshot": prior["feature_snapshot"],
            "no_return_result": prior["no_return_result"],
            "decision": prior["decision"],
        },
        "append_only_attempt_accounting": {
            "prior_historical_research_attempt_count": 300,
            "campaign053_pre_terminal_infrastructure_failure_count": 1,
            "campaign053_complete_factor_attempt_count": 1,
            "campaign053_post_terminal_infrastructure_failure_count": 1,
            "campaign053_total_attempt_count": 3,
            "cumulative_historical_research_attempt_count": 303,
            "campaign053_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
        },
        "prospective_boundary": prior["prospective_boundary"],
        "data_limitation": prior["data_limitation"],
    })


def report_supersession() -> base.Path:
    return base.write_new(REPORT_SUPERSESSION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign053_unified_report_supersession",
        "status": "post_terminal_test_failure_accounting_current_report_and_boundaries_verified",
        "recorded_at": "2026-08-03T13:06:00Z",
        "bindings": {
            "report_supersession_v1_historical": base.binding(PRIOR_REPORT_SUPERSESSION),
            "research_record_v2": base.binding(RECORD),
            "terminal_assertion_failure": base.binding(FAILURE),
            "current_attempt_ledger": base.binding(LEDGER),
            "current_unified_research_report": base.binding(base.REPORT),
            "current_data_pipeline_documentation": base.binding(base.PIPELINE_DOC),
            "current_manage_qlib_a_share_data_skill": base.binding(base.SKILL),
        },
        "semantic_boundary": {
            "campaign053_factor_result_or_gate_changed": False,
            "historical_daily_price_or_forward_return_read": False,
            "candidate49_ledgers_changed": False,
            "attempt_count_advanced_from_302_to_303": True,
        },
    })


def verification() -> base.Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    checked = [
        validator.validate_record(RECORD, data_root=base.DATA_ROOT),
        validator.validate_record(REPORT_SUPERSESSION, data_root=base.DATA_ROOT),
    ]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Campaign053 current bindings failed")
    if base.sha256(base.SIGNAL_LEDGER) != "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79":
        raise RuntimeError("Candidate49 signal ledger changed")
    if base.sha256(base.EXECUTION_LEDGER) != "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f":
        raise RuntimeError("Candidate49 execution ledger changed")
    return base.write_new(VERIFICATION, {
        "version": 2,
        "kind": "a_share_three_day_walkforward_campaign053_verification",
        "status": "terminal_campaign053_current_tests_bindings_and_candidate49_isolation_verified",
        "recorded_at": "2026-08-03T13:08:00Z",
        "historical_verification": base.binding(PRIOR_VERIFICATION),
        "bindings": {
            "research_record_v2": base.binding(RECORD),
            "report_supersession_v2": base.binding(REPORT_SUPERSESSION),
            "attempt_ledger_v2": base.binding(LEDGER),
            "terminal_assertion_failure": base.binding(FAILURE),
            "current_terminal_tests": base.binding(CURRENT_TESTS),
            "current_finalizer": base.binding(FINALIZER),
            "unified_research_report": base.binding(base.REPORT),
            "data_pipeline_documentation": base.binding(base.PIPELINE_DOC),
            "manage_qlib_a_share_data_skill": base.binding(base.SKILL),
            "candidate49_signal_ledger": base.binding(base.SIGNAL_LEDGER),
            "candidate49_execution_ledger": base.binding(base.EXECUTION_LEDGER),
        },
        "verification_summary": {
            "historical_focused_run_passed": 15,
            "historical_focused_run_failed": 1,
            "current_focused_campaign053_tests_passed": 16,
            "current_focused_campaign053_tests_failed": 0,
            "all_current_bindings_passed": True,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "terminal_decision": {
            "campaign053_attempt_count": 3,
            "cumulative_historical_research_attempt_count": 303,
            "campaign053_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 266,
            "admissible_factor_count": 0,
            "development_folds_opened": False,
            "stress_2024_2025_opened": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    })


def state() -> base.Path:
    prior = base.load(PRIOR_STATE)
    campaign = dict(prior["campaign053"])
    campaign["attempt_accounting"] = base.load(RECORD)["append_only_attempt_accounting"]
    campaign["authoritative_records"] = {
        "research_record_v2": base.binding(RECORD),
        "verification_v2": base.binding(VERIFICATION),
        "unified_report_supersession_v2": base.binding(REPORT_SUPERSESSION),
        "terminal_assertion_failure": base.binding(FAILURE),
    }
    return base.write_new(STATE, {
        "version": 2,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign053_terminal_verified_post_test_failure_recorded_ready_for_independent_campaign054",
        "recorded_at": "2026-08-03T13:10:00Z",
        "authoritative_predecessor": base.binding(PRIOR_STATE),
        "research_policy": prior["research_policy"],
        "campaign053": campaign,
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign053": 303,
            "cumulative_return_reading_development_trial_count_after_campaign053": 266,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": prior["local_data_context"],
        "prospective_boundary": prior["prospective_boundary"],
        "verification_summary": base.load(VERIFICATION)["verification_summary"],
        "next_action": prior["next_action"],
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("ledger", "record", "report-supersession", "verification", "state"))
    args = parser.parse_args()
    path = {
        "ledger": ledger,
        "record": record,
        "report-supersession": report_supersession,
        "verification": verification,
        "state": state,
    }[args.stage]()
    print(json.dumps({"path": str(path), "sha256": base.sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
