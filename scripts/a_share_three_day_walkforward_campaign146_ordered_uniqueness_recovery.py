#!/usr/bin/env python3
"""Recover Campaign146's all-141 audit after a frozen receipt-key defect."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign146_ordered_uniqueness as frozen,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_ordered_uniqueness_recovery_protocol_20260814.json"
)
RECOVERY_PROTOCOL_SHA256 = (
    "58f3d4508ecb4fb257b3b77597015444d0ec35d643bc6892ab35870d21b7e4e9"
)
ORIGINAL_RUNNER_SHA256 = (
    "fe9101c169b00be739b39d9ea4c983a8b0a7ee5f1910158a5ca908fdb2f5afe1"
)
ORIGINAL_FREEZE_SHA256 = (
    "b0070093183dee8dc7d36fc3fd6983a1f3f62c8873daeda834d4da3705374876"
)
PLAN_FAILURE_SHA256 = "bc5f190f9c6b24621ab19a32369e0a980cb2c4a5d2905fbb13a6c14a7665b9e0"
RECOVERY_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_ordered_uniqueness_recovery_implementation_freeze_20260814.json"
)
RECOVERY_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_ordered_uniqueness_recovery.py"
)


class Campaign146OrderedUniquenessRecoveryError(RuntimeError):
    """Fail closed when the receipt-only recovery boundary changes."""


def load_recovery_protocol() -> dict[str, Any]:
    frozen.require_file(
        RECOVERY_PROTOCOL, RECOVERY_PROTOCOL_SHA256, "recovery protocol"
    )
    spec = frozen.load_json(RECOVERY_PROTOCOL)
    inputs = spec.get("authoritative_inputs") or {}
    correction = spec.get("allowed_correction") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign146_ordered_uniqueness_recovery_protocol"
        and spec.get("status") == "frozen_before_comparator_values"
        and (inputs.get("ordered_uniqueness_implementation_freeze") or {}).get("sha256")
        == ORIGINAL_FREEZE_SHA256
        and (inputs.get("frozen_runner") or {}).get("sha256") == ORIGINAL_RUNNER_SHA256
        and (inputs.get("plan_failure") or {}).get("sha256") == PLAN_FAILURE_SHA256
        and correction.get("defective_expression") == "len(c136_manifest['files'])"
        and correction.get("correct_expression") == "len(c136_manifest['partitions'])"
        and correction.get(
            "formula_direction_sources_order_alignment_gate_output_or_decision_change_allowed"
        )
        is False
        and correction.get("frozen_runner_or_data_rewrite_allowed") is False
        and boundary.get("comparator_values_read_before_recovery_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign146OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery protocol changed"
        )
    return spec


def validate_recovery_implementation_freeze() -> dict[str, Any]:
    if not RECOVERY_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign146OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery implementation freeze is absent"
        )
    record = frozen.load_json(RECOVERY_IMPLEMENTATION_FREEZE)
    implementation = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign146_ordered_uniqueness_recovery_implementation_freeze"
        and record.get("status")
        == "receipt_key_recovery_wrapper_frozen_before_comparator_values"
        and implementation.get("recovery_runner_sha256")
        == frozen.file_sha256(Path(__file__).resolve())
        and implementation.get("recovery_test_sha256")
        == frozen.file_sha256(RECOVERY_TEST)
        and implementation.get("recovery_protocol_sha256") == RECOVERY_PROTOCOL_SHA256
        and implementation.get("original_runner_sha256") == ORIGINAL_RUNNER_SHA256
        and implementation.get("original_freeze_sha256") == ORIGINAL_FREEZE_SHA256
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 5
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign146OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery implementation freeze changed"
        )
    return record


def corrected_validate_static_bindings() -> dict[str, Any]:
    load_recovery_protocol()
    frozen.load_protocol()
    frozen.candidate._validate_implementation_freeze()
    design_manifest = frozen.validate_design_manifest_metadata()
    c136_manifest = frozen.validate_c136_manifest_metadata()
    original_freeze = frozen.validate_implementation_freeze()
    for path, expected, label in (
        (frozen.COVERAGE_PATH, frozen.COVERAGE_SHA256, "coverage result"),
        (
            frozen.recovery.SNAPSHOT_MANIFEST,
            frozen.recovery.SNAPSHOT_MANIFEST_SHA256,
            "candidate manifest",
        ),
        (
            frozen.CANDIDATE49_SIGNAL_LEDGER,
            frozen.CANDIDATE49_SIGNAL_LEDGER_SHA256,
            "Candidate49 signal ledger",
        ),
        (
            frozen.CANDIDATE49_EXECUTION_LEDGER,
            frozen.CANDIDATE49_EXECUTION_LEDGER_SHA256,
            "Candidate49 execution ledger",
        ),
    ):
        frozen.require_file(path, expected, label)
    result = frozen.load_json(frozen.COVERAGE_PATH)
    gate = result.get("coverage_and_variation") or {}
    if not (
        result.get("status")
        == "coverage_passed_ready_to_freeze_all_141_ordered_comparator_audit"
        and gate.get("gate_passed_before_comparator_values") is True
        and gate.get("candidate_eligible_rows")
        == frozen.EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and result.get("comparator_values_read") is False
        and result.get("numeric_comparator_count_read") == 0
        and result.get("historical_forward_return_fields_read") is False
    ):
        raise Campaign146OrderedUniquenessRecoveryError("coverage authority changed")
    return {
        "implementation_freeze_sha256": frozen.file_sha256(
            frozen.IMPLEMENTATION_FREEZE_PATH
        ),
        "coverage_sha256": frozen.COVERAGE_SHA256,
        "candidate_manifest_sha256": frozen.recovery.SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": frozen.recovery.SNAPSHOT_DATASET_SHA256,
        "design_manifest_sha256": frozen.DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": frozen.DESIGN_DATASET_SHA256,
        "design_partition_count": len(design_manifest["files"]),
        "campaign136_manifest_sha256": frozen.C136_MANIFEST_SHA256,
        "campaign136_dataset_sha256": frozen.C136_DATASET_SHA256,
        "campaign136_partition_count": len(c136_manifest["partitions"]),
        "candidate49_signal_ledger_sha256": frozen.CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": frozen.CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "freeze_status": original_freeze["status"],
        "receipt_key_correction": "files_to_partitions_only",
    }


def build_plan() -> dict[str, Any]:
    validate_recovery_implementation_freeze()
    static = corrected_validate_static_bindings()
    static["recovery_implementation_freeze_sha256"] = frozen.file_sha256(
        RECOVERY_IMPLEMENTATION_FREEZE
    )
    blockers = (
        ["uniqueness_output_already_exists"] if frozen.OUTPUT_PATH.exists() else []
    )
    return {
        "kind": "a_share_three_day_walkforward_campaign146_ordered_uniqueness_recovery_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(frozen.OUTPUT_PATH),
        "comparison_count": frozen.EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": frozen.EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def run_ordered_uniqueness(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign146OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery requires --confirm-run"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign146OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery plan is not ready"
        )
    original_build_plan = frozen.build_plan
    frozen.build_plan = build_plan
    try:
        return frozen.run_ordered_uniqueness(confirm=True)
    finally:
        frozen.build_plan = original_build_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    run = sub.add_parser("run")
    run.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            value = build_plan()
            print(json.dumps(value, ensure_ascii=False, sort_keys=True))
            return 0 if value["ready"] else 2
        path = run_ordered_uniqueness(confirm=args.confirm_run)
        print(json.dumps({"uniqueness_audit_path": str(path)}, sort_keys=True))
        return 0
    except (
        Campaign146OrderedUniquenessRecoveryError,
        frozen.Campaign146OrderedUniquenessError,
    ) as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign146_ordered_uniqueness_recovery_failure",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
