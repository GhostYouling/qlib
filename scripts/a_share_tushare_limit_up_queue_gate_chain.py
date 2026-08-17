#!/usr/bin/env python3
"""Validate the Campaign115 zero-network gate chain without hiding exits."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

STAGES: tuple[dict[str, Any], ...] = (
    {
        "name": "acceptance_plan",
        "script": "a_share_tushare_limit_up_queue_acceptance.py",
        "arguments": ("plan",),
        "kind": "plan",
    },
    {
        "name": "acceptance_inspection",
        "script": "a_share_tushare_limit_up_queue_acceptance.py",
        "arguments": ("inspect-attempt",),
        "kind": "inspection",
    },
    {
        "name": "development_source_plan",
        "script": "a_share_tushare_limit_up_queue_development.py",
        "arguments": ("plan",),
        "kind": "plan",
    },
    {
        "name": "semantic_verification_plan",
        "script": "a_share_tushare_limit_up_queue_development_verify.py",
        "arguments": ("plan",),
        "kind": "plan",
    },
    {
        "name": "semantic_receipt_inspection",
        "script": "a_share_tushare_limit_up_queue_development_verify.py",
        "arguments": ("inspect-receipt",),
        "kind": "inspection",
    },
    {
        "name": "ordered_no_return_plan",
        "script": "a_share_tushare_limit_up_queue_no_return_audit.py",
        "arguments": ("plan",),
        "kind": "plan",
    },
    {
        "name": "ordered_no_return_inspection",
        "script": "a_share_tushare_limit_up_queue_no_return_audit.py",
        "arguments": ("inspect-audit",),
        "kind": "inspection",
    },
    {
        "name": "development_trial_plan",
        "script": "a_share_tushare_limit_up_queue_walkforward.py",
        "arguments": ("plan",),
        "kind": "plan",
    },
    {
        "name": "development_trial_inspection",
        "script": "a_share_tushare_limit_up_queue_walkforward.py",
        "arguments": ("inspect-trial",),
        "kind": "inspection",
    },
)

FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "candidate49_historical_backfill_performed",
        "candidate49_ledgers_changed",
        "candidate_or_comparator_values_read",
        "comparison_values_read",
        "credential_loaded",
        "credential_value_printed_hashed_or_persisted",
        "current_scoring_selection_sizing_or_orders_performed",
        "daily_price_or_forward_return_values_read",
        "historical_daily_price_or_forward_return_values_read",
        "historical_daily_price_or_forward_return_values_read_by_inspection",
        "parquet_candidate_values_read",
        "parquet_comparator_values_read",
        "partition_year_2024_or_2025_values_read",
        "provider_request_issued",
        "provider_request_issued_by_inspection",
        "stress_2024_2025_opened",
    }
)


class GateChainError(RuntimeError):
    """Raised when a gate command cannot be semantically validated."""


def _sanitized_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("TUSHARE_TOKEN", None)
    environment.pop("QLIB_A_SHARE_DATA_ROOT", None)
    environment.pop("PYTHONPATH", None)
    return environment


def _forbidden_true_paths(value: Any, prefix: str = "") -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_TRUE_FIELDS and item is not False:
                failures.append(path)
            failures.extend(_forbidden_true_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            failures.extend(_forbidden_true_paths(item, f"{prefix}[{index}]"))
    return failures


def _run_stage(stage: dict[str, Any]) -> tuple[int, str, str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / stage["script"]),
        *stage["arguments"],
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_sanitized_environment(),
        capture_output=True,
        check=False,
        text=True,
        timeout=180,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _validate_stage(stage: dict[str, Any]) -> dict[str, Any]:
    returncode, stdout, stderr = _run_stage(stage)
    if stderr:
        raise GateChainError(f"{stage['name']} wrote stderr")
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise GateChainError(f"{stage['name']} did not emit one JSON object") from error
    if not isinstance(payload, dict):
        raise GateChainError(f"{stage['name']} JSON payload is not an object")

    forbidden = _forbidden_true_paths(payload)
    if forbidden:
        raise GateChainError(
            f"{stage['name']} crossed zero-value boundary: {', '.join(forbidden)}"
        )

    summary: dict[str, Any] = {
        "command": [stage["script"], *stage["arguments"]],
        "process_exit_code": returncode,
        "zero_network_and_zero_research_value_semantics": True,
    }
    if stage["kind"] == "plan":
        ready = payload.get("ready")
        declared_exit = payload.get("exit_code_if_executed")
        if type(ready) is not bool or declared_exit not in (0, 2):
            raise GateChainError(f"{stage['name']} plan contract changed")
        expected_exit = 0 if ready else 2
        if returncode != expected_exit or declared_exit != expected_exit:
            raise GateChainError(f"{stage['name']} plan exit semantics changed")
        blockers = payload.get("blockers")
        if not isinstance(blockers, list) or any(
            not isinstance(item, str) for item in blockers
        ):
            raise GateChainError(f"{stage['name']} blockers contract changed")
        if ready == bool(blockers):
            raise GateChainError(f"{stage['name']} ready/blocker semantics changed")
        summary.update({"ready": ready, "blockers": blockers})
    else:
        if returncode != 0 or payload.get("valid") is not True:
            raise GateChainError(f"{stage['name']} inspection is not valid")
        declared_exit = payload.get("exit_code")
        if declared_exit is not None and declared_exit != returncode:
            raise GateChainError(f"{stage['name']} inspection exit semantics changed")
        status = payload.get("status")
        if not isinstance(status, str) or not status:
            raise GateChainError(f"{stage['name']} inspection status changed")
        summary.update({"valid": True, "status": status})
    return summary


def build_status() -> dict[str, Any]:
    stages = {stage["name"]: _validate_stage(stage) for stage in STAGES}
    plan_names = [stage["name"] for stage in STAGES if stage["kind"] == "plan"]
    all_plans_ready = all(stages[name]["ready"] for name in plan_names)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_zero_network_gate_chain_status",
        "status": (
            "all_scientific_plans_ready_for_their_separate_confirmed_commands"
            if all_plans_ready
            else "gate_chain_validated_with_one_or_more_scientific_plans_closed"
        ),
        "valid": True,
        "all_scientific_plans_ready": all_plans_ready,
        "stage_order": [stage["name"] for stage in STAGES],
        "stages": stages,
        "provider_action_authorized_by_this_command": False,
        "confirmed_scientific_command_executed": False,
        "provider_request_issued": False,
        "credential_value_printed_hashed_or_persisted": False,
        "candidate_or_comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "partition_year_2024_or_2025_values_read": False,
        "candidate49_historical_backfill_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    return value


def main() -> int:
    parser().parse_args()
    try:
        print(json.dumps(build_status(), ensure_ascii=False, sort_keys=True))
        return 0
    except (GateChainError, subprocess.SubprocessError) as error:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "provider_action_authorized_by_this_command": False,
                    "provider_request_issued": False,
                    "credential_value_printed_hashed_or_persisted": False,
                    "candidate_or_comparator_values_read": False,
                    "historical_daily_price_or_forward_return_values_read": False,
                    "partition_year_2024_or_2025_values_read": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
