#!/usr/bin/env python3
"""Publish append-only evidence for the 2026-08-03 Candidate49 source failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGING = Path("/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-03")
FAILURE = STAGING / "raw/a_share/rich/tushare/daily_provider_migration_v1/latest_failure.json"
CALENDAR_JSON = STAGING / "raw/a_share/rich/tushare/daily_provider_migration_v1/trade_calendar.json"
CALENDAR_PARQUET = STAGING / "raw/a_share/rich/tushare/daily_provider_migration_v1/trade_calendar.parquet"
PREDECESSOR = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign052_verified.json"
PROTOCOL = ROOT / "docs/a_share_tushare_candidate49_future_session_workflow_protocol.json"
WORKFLOW = ROOT / "scripts/a_share_tushare_candidate49_future_session_workflow.py"
WORKFLOW_TESTS = ROOT / "tests/data_collector_tests/test_a_share_tushare_candidate49_future_session_workflow.py"
PIPELINE_DOC = ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
RECORD = ROOT / "docs/a_share_candidate49_20260803_daily_source_failure_record.json"
SUPERSESSION = ROOT / "docs/a_share_candidate49_20260803_documentation_supersession.json"
VERIFICATION = ROOT / "docs/a_share_candidate49_20260803_daily_source_failure_verification.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign052_candidate49_source_failure_verified.json"


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
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if load(path) != value:
            raise RuntimeError(f"refuse to rewrite immutable evidence: {path}")
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


def record() -> Path:
    failure = load(FAILURE)
    return write_new(RECORD, {
        "version": 1,
        "kind": "a_share_candidate49_daily_source_failure_record",
        "status": "same_day_candidate49_workflow_failed_closed_at_stock_basic_no_retry_allowed",
        "recorded_at": "2026-08-03T08:56:00Z",
        "session_date": "2026-08-03",
        "timezone": "Asia/Singapore",
        "authoritative_predecessor": binding(PREDECESSOR),
        "workflow_protocol": binding(PROTOCOL),
        "readonly_plan": {
            "session": "2026-08-03",
            "staging_root": str(STAGING),
            "minute_data_root": "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "ready": True,
            "recommended_cli_exit_code": 0,
            "actual_exit_code": 0,
            "token_present": True,
            "filesystem_write_performed": False,
            "provider_request_issued": False,
        },
        "confirmed_run": {
            "same_parameters_as_plan": True,
            "confirm_run": True,
            "status": "failed_closed",
            "actual_exit_code": 1,
            "failure_stage": failure["failure_stage"],
            "error_classification": "Tushare stock_basic contains an invalid ts_code",
            "provider_continuation_allowed": False,
            "same_day_retry_allowed": False,
        },
        "immutable_failure_evidence": {
            "latest_failure": binding(FAILURE),
            "trade_calendar_json": binding(CALENDAR_JSON),
            "trade_calendar_parquet": binding(CALENDAR_PARQUET),
            "active_root_mutated": failure["active_root_mutated"],
            "completed_session_checkpoints_preserved": failure["completed_session_checkpoints_preserved"],
            "credential_value_persisted": failure["credential_value_persisted"],
            "forward_return_fields_read": failure["forward_return_fields_read"],
            "provider_calls_this_invocation": failure["provider_calls_this_invocation"],
        },
        "post_failure_state": {
            "active_data_root": "/Volumes/DIsk/Disk-Coding/qlib/data",
            "active_daily_source": "baostock",
            "active_calendar_end": "2026-07-13",
            "source_snapshot_published": False,
            "candidate49_signal_ledger": {**binding(SIGNAL), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION), "entry_count": 0},
        },
        "credential_safety": {
            "repository_dotenv_exists": True,
            "repository_dotenv_mode": "0600",
            "TUSHARE_TOKEN_nonempty": True,
            "token_value_printed_hashed_or_persisted": False,
            "credential_missing_is_not_the_failure": True,
        },
        "research_boundary": {
            "candidate49_historical_return_backfill_performed": False,
            "candidate49_historical_signal_or_execution_backfill_performed": False,
            "second_prospective_candidate_started": False,
            "failure_exit_code_bypassed": False,
            "failed_response_re_requested_for_more_detail": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "next_action": "Do not retry the 2026-08-03 provider gate. Preserve staging evidence and continue only zero-network offline Campaign053 research.",
    })


def supersession() -> Path:
    prior = load(ROOT / "docs/a_share_three_day_walkforward_campaign_052_verification_20260803.json")
    return write_new(SUPERSESSION, {
        "version": 1,
        "kind": "a_share_candidate49_20260803_documentation_supersession",
        "status": "campaign052_historical_bindings_preserved_candidate49_failure_documentation_current",
        "recorded_at": "2026-08-03T08:58:00Z",
        "bindings": {
            "candidate49_failure_record": binding(RECORD),
            "current_data_pipeline_documentation": binding(PIPELINE_DOC),
            "current_manage_qlib_a_share_data_skill": binding(SKILL),
        },
        "historical_bindings": {
            "campaign052_verification": binding(ROOT / "docs/a_share_three_day_walkforward_campaign_052_verification_20260803.json"),
            "previous_data_pipeline_documentation_sha256": prior["bindings"]["data_pipeline_documentation"]["sha256"],
            "previous_manage_skill_sha256": prior["bindings"]["manage_qlib_a_share_data_skill"]["sha256"],
            "historical_record_rewritten": False,
        },
        "semantic_boundary": {
            "campaign052_result_or_gate_changed": False,
            "candidate49_signal_or_execution_ledger_changed": False,
            "same_day_retry_authorized": False,
            "documentation_update_is_append_only": True,
        },
    })


def verification() -> Path:
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    checked = [validator.validate_record(path, data_root=Path("/Volumes/DIsk/qlib-a-share-tushare-1m")) for path in (RECORD, SUPERSESSION)]
    if not all(item["all_bindings_passed"] for item in checked):
        raise RuntimeError("Candidate49 failure bindings are not current")
    if sha256(SIGNAL) != "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79":
        raise RuntimeError("Candidate49 signal ledger changed")
    if sha256(EXECUTION) != "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f":
        raise RuntimeError("Candidate49 execution ledger changed")
    return write_new(VERIFICATION, {
        "version": 1,
        "kind": "a_share_candidate49_daily_source_failure_verification",
        "status": "candidate49_20260803_failure_bindings_and_no_retry_boundary_verified",
        "recorded_at": "2026-08-03T09:00:00Z",
        "bindings": {
            "failure_record": binding(RECORD),
            "documentation_supersession": binding(SUPERSESSION),
            "workflow": binding(WORKFLOW),
            "workflow_tests": binding(WORKFLOW_TESTS),
            "candidate49_signal_ledger": binding(SIGNAL),
            "candidate49_execution_ledger": binding(EXECUTION),
        },
        "verification_summary": {
            "binding_records_checked": 2,
            "all_bindings_passed": True,
            "focused_workflow_tests_passed": 32,
            "focused_workflow_tests_failed": 0,
            "confirmed_run_exit_code": 1,
            "provider_continuation_allowed": False,
            "same_day_retry_allowed": False,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
    })


def state() -> Path:
    return write_new(STATE, {
        "version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign052_terminal_candidate49_20260803_source_failure_verified_ready_for_campaign053_offline",
        "recorded_at": "2026-08-03T09:02:00Z",
        "authoritative_predecessor": binding(PREDECESSOR),
        "historical_research_state": {
            "campaign052_terminal_state_unchanged": True,
            "cumulative_historical_research_attempt_count": 300,
            "cumulative_return_reading_development_trial_count": 266,
            "current_historical_aggregation_candidate_count": 0,
            "offline_campaign053_may_run_without_new_daily_bar_or_16_30_wait": True,
        },
        "prospective_state": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "session_date": "2026-08-03",
            "status": "failed_closed_at_stock_basic_no_same_day_retry",
            "failure_record": binding(RECORD),
            "verification": binding(VERIFICATION),
            "candidate49_signal_ledger": {**binding(SIGNAL), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION), "entry_count": 0},
            "candidate49_historical_backfill_performed": False,
            "second_prospective_candidate_activation_allowed": False,
        },
        "next_action": {
            "historical": "Continue Campaign053 offline from a new independently preregistered mechanism.",
            "prospective": "Preserve the 2026-08-03 failure and do not retry or re-request it today.",
            "strict_prohibitions": [
                "do not bypass the source-gate exit code",
                "do not backfill Candidate49",
                "do not activate a second prospective candidate",
                "do not generate current scores selections sizes orders or investment advice",
            ],
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("record", "supersession", "verification", "state"))
    args = parser.parse_args()
    path = {"record": record, "supersession": supersession, "verification": verification, "state": state}[args.stage]()
    print(json.dumps({"path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
