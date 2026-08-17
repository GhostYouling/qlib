#!/usr/bin/env python3
"""Run Campaign145's frozen coverage gate from its recovery-verified snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign145_no_return_audit as frozen_audit,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign145_snapshot_verify_recovery as recovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_AUDIT_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign145_no_return_audit.py"
)
FROZEN_AUDIT_SHA256 = "4ae095ce04d835c72c64a3e263357387269c87ba255b6c112f0b4c3ba4aafb53"
RECOVERY_RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_recovery_verification_20260814.json"
)
RECOVERY_RECEIPT_SHA256 = (
    "6c953d3dd989e919fd82a65a21a1942fc2adc4afc63de459dfb8c6f9dd3dd263"
)
ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_coverage_activation_binding_v2_20260814.json"
)
RUNNER_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_coverage_recovery_runner_implementation_freeze_20260814.json"
)
RUNNER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign145_no_return_audit_recovery.py"
)
OUTPUT_PATH = frozen_audit.OUTPUT_PATH


class Campaign145CoverageRecoveryError(RuntimeError):
    """Fail closed when a recovery-bound coverage invariant changes."""


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign145CoverageRecoveryError(f"expected JSON object: {path}")
    return value


def validate_recovery_receipt() -> dict[str, Any]:
    recovery.require_file(RECOVERY_RECEIPT, RECOVERY_RECEIPT_SHA256, "recovery receipt")
    receipt = _load_json(RECOVERY_RECEIPT)
    snapshot = receipt.get("snapshot_manifest") or {}
    correction = receipt.get("known_header_correction") or {}
    verification = receipt.get("verification") or {}
    boundary = receipt.get("research_boundary") or {}
    if not (
        receipt.get("kind")
        == "a_share_three_day_walkforward_campaign145_snapshot_recovery_verification"
        and receipt.get("status")
        == "verified_immutable_snapshot_with_effective_formula_range"
        and snapshot.get("path") == str(recovery.SNAPSHOT_MANIFEST)
        and snapshot.get("sha256") == recovery.SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == recovery.SNAPSHOT_DATASET_SHA256
        and snapshot.get("partitions") == recovery.EXPECTED_PARTITIONS
        and snapshot.get("rows") == recovery.EXPECTED_ROWS
        and snapshot.get("eligible_rows") == recovery.EXPECTED_ELIGIBLE_ROWS
        and correction.get("stored_manifest_range")
        == {recovery.c145.FACTOR_NAME: list(recovery.STORED_HEADER_RANGE)}
        and correction.get("effective_verified_range")
        == {recovery.c145.FACTOR_NAME: list(recovery.EFFECTIVE_RANGE)}
        and correction.get("snapshot_manifest_or_partition_rewritten") is False
        and all(
            verification.get(key) is True
            for key in (
                "all_partition_paths_contained",
                "all_partition_byte_sha256_verified",
                "all_partition_frame_sha256_verified",
                "all_partition_rows_and_output_schema_verified",
                "all_effective_value_semantics_verified",
                "ordered_dataset_digest_recomputed",
                "snapshot_manifest_sha256_rechecked_after_partitions",
            )
        )
        and verification.get("exit_code") == 0
        and boundary.get(
            "candidate_partition_values_read_only_for_integrity_and_semantic_verification"
        )
        is True
        and boundary.get("candidate_coverage_statistics_read") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign145CoverageRecoveryError("recovery receipt semantics changed")
    return receipt


def validate_runner_implementation_freeze() -> dict[str, Any]:
    if not RUNNER_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign145CoverageRecoveryError(
            "coverage recovery runner implementation freeze is absent"
        )
    freeze = _load_json(RUNNER_IMPLEMENTATION_FREEZE)
    frozen = freeze.get("frozen_implementation") or {}
    tests = freeze.get("synthetic_verification") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign145_coverage_recovery_runner_implementation_freeze"
        and freeze.get("status")
        == "coverage_recovery_runner_and_tests_frozen_before_coverage_statistics"
        and frozen.get("coverage_recovery_runner_sha256")
        == recovery.file_sha256(Path(__file__).resolve())
        and frozen.get("coverage_recovery_test_sha256")
        == recovery.file_sha256(RUNNER_TEST)
        and frozen.get("original_frozen_coverage_runner_sha256") == FROZEN_AUDIT_SHA256
        and frozen.get("recovery_receipt_sha256") == RECOVERY_RECEIPT_SHA256
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 5
        and boundary.get("candidate_coverage_statistics_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign145CoverageRecoveryError(
            "coverage recovery runner implementation freeze changed"
        )
    return freeze


def validate_activation_record(record: dict[str, Any]) -> None:
    implementations = record.get("implementation_freezes") or {}
    snapshot = record.get("candidate_snapshot") or {}
    receipt = record.get("recovery_verification_receipt") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign145_coverage_activation_binding_v2"
        and record.get("status")
        == "frozen_after_recovery_verified_snapshot_before_candidate_coverage_statistics"
        and (implementations.get("original_campaign145") or {}).get("sha256")
        == recovery.IMPLEMENTATION_FREEZE_SHA256
        and (implementations.get("recovery_verifier") or {}).get("sha256")
        == recovery.file_sha256(recovery.RECOVERY_IMPLEMENTATION_FREEZE)
        and (implementations.get("coverage_recovery_runner") or {}).get("sha256")
        == recovery.file_sha256(RUNNER_IMPLEMENTATION_FREEZE)
        and snapshot.get("path") == str(recovery.SNAPSHOT_MANIFEST)
        and snapshot.get("sha256") == recovery.SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == recovery.SNAPSHOT_DATASET_SHA256
        and snapshot.get("partitions") == recovery.EXPECTED_PARTITIONS
        and snapshot.get("rows") == recovery.EXPECTED_ROWS
        and snapshot.get("eligible_rows") == recovery.EXPECTED_ELIGIBLE_ROWS
        and snapshot.get("effective_factor_range")
        == {recovery.c145.FACTOR_NAME: list(recovery.EFFECTIVE_RANGE)}
        and receipt.get("path") == _relative(RECOVERY_RECEIPT)
        and receipt.get("sha256") == RECOVERY_RECEIPT_SHA256
        and record.get("coverage_gate") == frozen_audit.expected_gate()
        and record.get("numeric_comparator_count")
        == recovery.c145.NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == recovery.c145.NUMERIC_COMPARATOR_ORDER_SHA256
        and record.get("output_path") == _relative(OUTPUT_PATH)
        and record.get("single_use") is True
        and boundary.get(
            "candidate_partition_values_read_only_for_integrity_verification_before_activation"
        )
        is True
        and boundary.get("candidate_coverage_statistics_read_before_activation")
        is False
        and boundary.get("comparator_values_read_before_activation") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("credential_loaded") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign145CoverageRecoveryError("coverage activation semantics changed")


def validate_static_bindings() -> dict[str, Any]:
    recovery.require_file(FROZEN_AUDIT_PATH, FROZEN_AUDIT_SHA256, "frozen audit")
    recovery.c145._validate_implementation_freeze()
    validate_recovery_receipt()
    validate_runner_implementation_freeze()
    if not ACTIVATION_BINDING.is_file():
        raise Campaign145CoverageRecoveryError("coverage activation is absent")
    activation = _load_json(ACTIVATION_BINDING)
    validate_activation_record(activation)
    for path, expected, label in (
        (
            recovery.SNAPSHOT_MANIFEST,
            recovery.SNAPSHOT_MANIFEST_SHA256,
            "snapshot manifest",
        ),
        (
            frozen_audit.CANDIDATE49_SIGNAL_LEDGER,
            frozen_audit.CANDIDATE49_SIGNAL_LEDGER_SHA256,
            "Candidate49 signal ledger",
        ),
        (
            frozen_audit.CANDIDATE49_EXECUTION_LEDGER,
            frozen_audit.CANDIDATE49_EXECUTION_LEDGER_SHA256,
            "Candidate49 execution ledger",
        ),
    ):
        recovery.require_file(path, expected, label)
    return {
        "original_implementation_freeze_sha256": recovery.IMPLEMENTATION_FREEZE_SHA256,
        "recovery_receipt_sha256": RECOVERY_RECEIPT_SHA256,
        "coverage_recovery_runner_freeze_sha256": recovery.file_sha256(
            RUNNER_IMPLEMENTATION_FREEZE
        ),
        "activation_binding_sha256": recovery.file_sha256(ACTIVATION_BINDING),
        "candidate_manifest_sha256": recovery.SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": recovery.SNAPSHOT_DATASET_SHA256,
        "candidate49_signal_ledger_sha256": frozen_audit.CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": frozen_audit.CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "candidate_coverage_statistics_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def build_plan() -> dict[str, Any]:
    static = validate_static_bindings()
    blockers = ["coverage_audit_output_already_exists"] if OUTPUT_PATH.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign145_coverage_recovery_audit_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(OUTPUT_PATH.resolve()),
        "coverage_gate": frozen_audit.expected_gate(),
        "static_bindings": static,
        "candidate_coverage_statistics_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def verify_current_partition_bytes(*, workers: int) -> dict[str, Any]:
    manifest = recovery.load_and_validate_manifest_metadata()
    partition_root = (recovery.SNAPSHOT_MANIFEST.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> int:
        path = recovery.resolve_partition_path(item, partition_root=partition_root)
        if recovery.file_sha256(path) != item.get("output_byte_sha256"):
            raise Campaign145CoverageRecoveryError(
                f"partition byte hash changed after recovery: {path}"
            )
        return int(item["rows"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        rows = sum(pool.map(verify, manifest["files"]))
    if rows != recovery.EXPECTED_ROWS:
        raise Campaign145CoverageRecoveryError("partition row metadata changed")
    return {
        "snapshot_manifest_sha256": recovery.SNAPSHOT_MANIFEST_SHA256,
        "partitions": len(manifest["files"]),
        "rows": rows,
        "all_partition_byte_sha256_rechecked": True,
    }


def run_coverage_audit(*, workers: int, confirm: bool) -> Path:
    if not confirm:
        raise Campaign145CoverageRecoveryError(
            "coverage audit requires --confirm-coverage-audit"
        )
    if workers < 1 or workers > 16:
        raise Campaign145CoverageRecoveryError("--workers must be between 1 and 16")
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign145CoverageRecoveryError("coverage audit plan is not ready")
    byte_recheck = verify_current_partition_bytes(workers=workers)
    load_candidate = frozen_audit._generated["_load_candidate_frame"]
    load_eligible_keys = frozen_audit._generated["_quality_listing_eligible_keys"]
    atomic_json = frozen_audit._generated["_atomic_exclusive_json"]
    candidate_frame = load_candidate(recovery.EXPECTED_ELIGIBLE_ROWS)
    eligible_keys = load_eligible_keys()
    coverage = frozen_audit.coverage_and_variation(candidate_frame, eligible_keys)
    passed = coverage["gate_passed_before_comparator_values"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign145_coverage_audit",
        "status": (
            "coverage_passed_ready_to_freeze_all_141_ordered_comparator_audit"
            if passed
            else "coverage_failed_terminal_before_all_comparator_values"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": recovery.c145.FACTOR_NAME,
        "direction": "higher",
        "static_bindings": plan["static_bindings"],
        "snapshot_verification": validate_recovery_receipt(),
        "precoverage_partition_byte_recheck": byte_recheck,
        "coverage_and_variation": coverage,
        "comparator_values_read": False,
        "numeric_comparator_count_read": 0,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "stress_2024_2025_opened": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze an exact all-141 ordered no-return comparator audit before reading any comparator value"
            if passed
            else "terminalize Campaign145 without reading comparator values, daily prices, or returns"
        ),
    }
    atomic_json(OUTPUT_PATH, result)
    return OUTPUT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--workers", type=int, default=4)
    run_parser.add_argument("--confirm-coverage-audit", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        value = build_plan()
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0 if value["ready"] else 2
    path = run_coverage_audit(
        workers=args.workers,
        confirm=args.confirm_coverage_audit,
    )
    print(json.dumps({"coverage_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
