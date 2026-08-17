#!/usr/bin/env python3
"""Run Campaign121 Gate 2 after binding the verified immutable snapshot."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign121_no_return_audit as audit
from scripts import (
    a_share_three_day_walkforward_campaign121_snapshot_verify_recovery as snapshot_recovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT_PATH = Path(audit.__file__).resolve()
BASE_AUDIT_SHA256 = "970c7a17de1bdc6e9bffb04fbb104334b088423a85121f603e0a3baca5bd204a"
SNAPSHOT_VERIFICATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_feature_snapshot_verification_result_20260814.json"
)
SNAPSHOT_VERIFICATION_SHA256 = (
    "8f2e306dece976f619f66b8e41231a5e23ecf61e5449888cf44d6f790b7048dc"
)
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_coverage_inherited_manifest_validation_failure_20260814.json"
)
FAILURE_RECORD_SHA256 = (
    "2d816b06a3dce5163be42ea4da41fcf2c02c35a013415706ffff3bfed3b4194c"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_coverage_recovery_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign121_coverage_recovery.py"
)


class Campaign121CoverageRecoveryError(RuntimeError):
    """Fail closed when a recovery binding or the original gate changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def validate_snapshot_verification(record: dict[str, Any]) -> None:
    factor = record.get("factor") or {}
    snapshot = record.get("snapshot") or {}
    discrepancy = record.get("manifest_metadata_discrepancy_preserved") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign121_feature_snapshot_verification_result"
        and record.get("status") == "verified_by_frozen_read_only_recovery_verifier"
        and factor.get("name") == audit.FACTOR_NAME
        and factor.get("truthful_value_range_verified") == [0.0, 1.0]
        and factor.get("truthful_position_lattice_denominator") == 239
        and snapshot.get("manifest_sha256") == snapshot_recovery.MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == snapshot_recovery.DATASET_SHA256
        and snapshot.get("partitions") == audit.candidate.EXPECTED_PARTITIONS
        and snapshot.get("rows") == audit.candidate.EXPECTED_ROWS
        and snapshot.get("eligible_rows") == audit.candidate.EXPECTED_ROWS
        and snapshot.get("all_partition_byte_hashes_verified") is True
        and snapshot.get("all_partition_frame_hashes_verified") is True
        and discrepancy.get("manifest_or_partition_rewritten") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign121CoverageRecoveryError(
            "snapshot verification result semantics changed"
        )


def load_snapshot_verification() -> dict[str, Any]:
    if (
        not SNAPSHOT_VERIFICATION_PATH.is_file()
        or _sha256(SNAPSHOT_VERIFICATION_PATH) != SNAPSHOT_VERIFICATION_SHA256
    ):
        raise Campaign121CoverageRecoveryError(
            "snapshot verification result fingerprint changed"
        )
    record = json.loads(SNAPSHOT_VERIFICATION_PATH.read_text(encoding="utf-8"))
    validate_snapshot_verification(record)
    return record


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign121CoverageRecoveryError("coverage recovery freeze is absent")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign121_coverage_recovery_freeze"
        and record.get("status")
        == "coverage_only_recovery_frozen_before_candidate_coverage_values"
        and frozen.get("runner_path") == _relative(Path(__file__))
        and frozen.get("runner_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("base_audit_path") == _relative(BASE_AUDIT_PATH)
        and frozen.get("base_audit_sha256") == BASE_AUDIT_SHA256
        and frozen.get("snapshot_verification_sha256") == SNAPSHOT_VERIFICATION_SHA256
        and frozen.get("failure_record_sha256") == FAILURE_RECORD_SHA256
        and frozen.get("output_path") == _relative(audit.OUTPUT_PATH)
        and frozen.get("numeric_comparator_count") == 138
        and frozen.get("numeric_comparator_order_sha256")
        == audit.candidate.NUMERIC_COMPARATOR_ORDER_SHA256
        and test.get("passed") == 4
        and test.get("exit_code") == 0
        and boundary.get("candidate_coverage_values_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign121CoverageRecoveryError("coverage recovery freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    if not BASE_AUDIT_PATH.is_file() or _sha256(BASE_AUDIT_PATH) != BASE_AUDIT_SHA256:
        raise Campaign121CoverageRecoveryError("base coverage audit changed")
    if (
        not FAILURE_RECORD_PATH.is_file()
        or _sha256(FAILURE_RECORD_PATH) != FAILURE_RECORD_SHA256
    ):
        raise Campaign121CoverageRecoveryError("coverage failure record changed")
    base = audit.validate_static_bindings()
    snapshot_recovery.validate_static_bindings()
    load_snapshot_verification()
    freeze = _validate_recovery_freeze()
    return {
        **base,
        "snapshot_verification_sha256": SNAPSHOT_VERIFICATION_SHA256,
        "coverage_recovery_freeze_sha256": _sha256(RECOVERY_FREEZE_PATH),
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "recovery_status": freeze["status"],
    }


def build_plan() -> dict[str, Any]:
    static = validate_static_bindings()
    blockers = (
        ["coverage_audit_output_already_exists"] if audit.OUTPUT_PATH.exists() else []
    )
    return {
        "kind": "a_share_three_day_walkforward_campaign121_coverage_recovery_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(audit.OUTPUT_PATH),
        "coverage_gate": audit.expected_gate(),
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def run(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign121CoverageRecoveryError(
            "coverage recovery requires --confirm-coverage-recovery"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign121CoverageRecoveryError("coverage recovery plan is not ready")
    activation = audit._load_activation()
    snapshot_verification = load_snapshot_verification()
    expected_eligible = int(activation["candidate_snapshot"]["eligible_rows"])
    candidate_frame = audit._load_candidate_frame(expected_eligible)
    eligible_keys = audit._quality_listing_eligible_keys()
    coverage = audit.coverage_and_variation(candidate_frame, eligible_keys)
    del candidate_frame, eligible_keys
    gc.collect()
    passed = coverage["gate_passed_before_comparator_values"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign121_coverage_audit",
        "status": (
            "coverage_passed_ready_to_freeze_all_138_ordered_comparator_audit"
            if passed
            else "coverage_failed_terminal_before_all_comparator_values"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": audit.FACTOR_NAME,
        "direction": "higher",
        "static_bindings": plan["static_bindings"],
        "snapshot_verification": {
            "path": _relative(SNAPSHOT_VERIFICATION_PATH),
            "sha256": SNAPSHOT_VERIFICATION_SHA256,
            "status": snapshot_verification["status"],
            "partitions": snapshot_verification["snapshot"]["partitions"],
            "rows": snapshot_verification["snapshot"]["rows"],
            "eligible_rows": snapshot_verification["snapshot"]["eligible_rows"],
        },
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
            "freeze an exact all-138 ordered no-return comparator audit before reading any comparator value"
            if passed
            else "terminalize Campaign121 without reading comparator values, daily prices, or returns"
        ),
    }
    audit._atomic_exclusive_json(audit.OUTPUT_PATH, result)
    return audit.OUTPUT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--confirm-coverage-recovery", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        value = build_plan()
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0 if value["ready"] else 2
    path = run(confirm=args.confirm_coverage_recovery)
    print(json.dumps({"coverage_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
