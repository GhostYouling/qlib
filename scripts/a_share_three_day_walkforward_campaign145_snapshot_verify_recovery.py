#!/usr/bin/env python3
"""Verify Campaign145's immutable snapshot after a frozen header-check defect.

This recovery verifier never rebuilds or rewrites the snapshot.  ``plan`` reads
metadata only.  ``verify`` requires explicit confirmation, validates every
partition byte and frame hash, and applies the preregistered effective value
range of ``[-1, 1]``.  It emits a receipt payload on stdout; publication remains
an explicit append-only repository step.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign145_features as c145,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_recovery_verification_protocol_20260814.json"
)
RECOVERY_PROTOCOL_SHA256 = (
    "4105cca80458487f8961fc426ba069e45105d5d0c8f6d36157df8ffbe7b0da36"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_manifest_semantics_verification_failure_20260814.json"
)
FAILURE_RECORD_SHA256 = (
    "5d2254afcdc0b19acb05474fc55334ffc7497c56722507a982873a3c245c54cd"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_no_return_implementation_freeze_20260814.json"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "cf4de349f6ef40b8cd4a6bfcc9fb2f6c484632dea84bb34da3287ca1dc01ae44"
)
RECOVERY_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_recovery_verifier_implementation_freeze_20260814.json"
)
RECOVERY_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign145_snapshot_verify_recovery.py"
)
RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_recovery_verification_20260814.json"
)
SNAPSHOT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign145_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign145_feature_library_v1/snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "58d3686906d71da431397576c883e8c4b727225e98cc6791ae5923e5ff5f965f"
)
SNAPSHOT_DATASET_SHA256 = (
    "d7cde236c58871314718febfb72f4e72d2cb6bab6729ee0f979b335e92a2acc0"
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_ELIGIBLE_ROWS = 3_954_911
EFFECTIVE_RANGE = (-1.0, 1.0)
STORED_HEADER_RANGE = (0.0, 1.0)


class Campaign145SnapshotRecoveryError(RuntimeError):
    """Fail closed when an immutable recovery invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected_sha256:
        raise Campaign145SnapshotRecoveryError(f"{label} changed: {path}")


def load_recovery_protocol() -> dict[str, Any]:
    require_file(RECOVERY_PROTOCOL, RECOVERY_PROTOCOL_SHA256, "recovery protocol")
    require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record")
    protocol = json.loads(RECOVERY_PROTOCOL.read_text(encoding="utf-8"))
    authoritative = protocol.get("authoritative_inputs") or {}
    snapshot = authoritative.get("snapshot_manifest") or {}
    discrepancy = protocol.get("known_manifest_header_discrepancy") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign145_snapshot_recovery_verification_protocol"
        and protocol.get("status") == "frozen_before_recovery_partition_reads"
        and (authoritative.get("implementation_freeze") or {}).get("path")
        == str(IMPLEMENTATION_FREEZE.relative_to(REPO_ROOT))
        and (authoritative.get("verification_failure") or {}).get("path")
        == str(FAILURE_RECORD.relative_to(REPO_ROOT))
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST)
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and snapshot.get("partitions") == EXPECTED_PARTITIONS
        and snapshot.get("rows") == EXPECTED_ROWS
        and snapshot.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and discrepancy.get("stored_factor_ranges")
        == {c145.FACTOR_NAME: list(STORED_HEADER_RANGE)}
        and discrepancy.get(
            "effective_formula_range_from_preregistration_and_partition_validator"
        )
        == {c145.FACTOR_NAME: list(EFFECTIVE_RANGE)}
        and discrepancy.get("stored_half_session_pair_count") == 119
        and discrepancy.get("stored_positive_half_denominators_required") is True
        and discrepancy.get("stored_signed_return_and_amount_magnitudes_used") is True
    ):
        raise Campaign145SnapshotRecoveryError("recovery protocol semantics changed")
    return protocol


def load_and_validate_manifest_metadata() -> dict[str, Any]:
    load_recovery_protocol()
    require_file(
        IMPLEMENTATION_FREEZE,
        IMPLEMENTATION_FREEZE_SHA256,
        "Campaign145 implementation freeze",
    )
    require_file(SNAPSHOT_MANIFEST, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c145.FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign145_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c145.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("partitions") == len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and eligible == EXPECTED_ELIGIBLE_ROWS
        and manifest.get("factor_names") == [c145.FACTOR_NAME]
        and manifest.get("factor_directions") == {c145.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges")
        == {c145.FACTOR_NAME: list(STORED_HEADER_RANGE)}
        and manifest.get("factor_formulas") == {c145.FACTOR_NAME: c145.FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(c145.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c145.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == c145.SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("half_session_pair_count") == 119
        and manifest.get("positive_half_denominators_required") is True
        and manifest.get("signed_return_and_amount_magnitudes_used") is True
        and manifest.get("raw_manifest_sha256") == c145.RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == c145.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c145.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c145.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c145.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{c145.FACTOR_NAME}__eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get(f"{c145.FACTOR_NAME}__missing_rows")
        == EXPECTED_ROWS - EXPECTED_ELIGIBLE_ROWS
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign145SnapshotRecoveryError("snapshot manifest semantics changed")
    return manifest


def resolve_partition_path(item: dict[str, Any], *, partition_root: Path) -> Path:
    root = partition_root.expanduser().resolve()
    path = Path(str(item.get("path", ""))).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise Campaign145SnapshotRecoveryError(
            f"partition path escapes snapshot: {path}"
        ) from exc
    relative = Path(str(item.get("relative_path", "")))
    if relative.is_absolute() or (root.parent / relative).resolve() != path:
        raise Campaign145SnapshotRecoveryError(
            f"partition relative path changed: {path}"
        )
    return path


def validate_recovery_implementation_freeze() -> dict[str, Any]:
    if not RECOVERY_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign145SnapshotRecoveryError(
            "recovery verifier implementation freeze is absent"
        )
    freeze = json.loads(RECOVERY_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    frozen = freeze.get("frozen_implementation") or {}
    tests = freeze.get("synthetic_verification") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign145_snapshot_recovery_verifier_implementation_freeze"
        and freeze.get("status")
        == "recovery_verifier_and_synthetic_semantics_frozen_before_recovery_partition_reads"
        and (freeze.get("authoritative_inputs") or {})
        .get("recovery_protocol", {})
        .get("sha256")
        == RECOVERY_PROTOCOL_SHA256
        and frozen.get("recovery_verifier_sha256")
        == file_sha256(Path(__file__).resolve())
        and frozen.get("recovery_test_sha256") == file_sha256(RECOVERY_TEST)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 5
        and boundary.get("recovery_partition_values_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign145SnapshotRecoveryError(
            "recovery verifier implementation freeze changed"
        )
    return freeze


def plan() -> dict[str, Any]:
    manifest = load_and_validate_manifest_metadata()
    validate_recovery_implementation_freeze()
    if RECEIPT.exists():
        raise Campaign145SnapshotRecoveryError("recovery receipt already exists")
    return {
        "status": "ready",
        "ready": True,
        "snapshot_manifest": str(SNAPSHOT_MANIFEST),
        "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "partitions": len(manifest["files"]),
        "rows": manifest["rows"],
        "eligible_rows": EXPECTED_ELIGIBLE_ROWS,
        "stored_header_range": list(STORED_HEADER_RANGE),
        "effective_verified_range": list(EFFECTIVE_RANGE),
        "partition_values_read_by_plan": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _verify_partition(
    item: dict[str, Any], *, partition_root: Path
) -> tuple[int, int, float | None, float | None]:
    path = resolve_partition_path(item, partition_root=partition_root)
    if not path.is_file() or file_sha256(path) != item.get("output_byte_sha256"):
        raise Campaign145SnapshotRecoveryError(f"partition byte hash changed: {path}")
    frame = pd.read_parquet(path, columns=list(c145.OUTPUT_COLUMNS))
    source = c145._generated["source"]
    if (
        tuple(frame.columns) != tuple(c145.OUTPUT_COLUMNS)
        or len(frame) != item.get("rows")
        or source._frame_sha256(frame) != item.get("output_frame_sha256")
    ):
        raise Campaign145SnapshotRecoveryError(f"partition frame changed: {path}")
    rows, eligible_rows = c145.validate_value_semantics(frame)
    stored_eligible = (item.get("factor_eligible_rows") or {}).get(c145.FACTOR_NAME)
    if not (
        item.get("kind")
        == "a_share_three_day_walkforward_campaign145_feature_partition"
        and item.get("status") == "complete_pending_aggregate_publication"
        and item.get("schema_version") == 1
        and stored_eligible == eligible_rows
        and item.get("protocol_sha256") == c145.PROTOCOL_SHA256
        and item.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and item.get("daily_price_fields_read") == []
        and item.get("forward_return_fields_read") is False
        and item.get("comparison_factor_values_read") is False
        and item.get("provider_request_issued") is False
    ):
        raise Campaign145SnapshotRecoveryError(
            f"partition metadata semantics changed: {path}"
        )
    eligible = frame.loc[
        frame[f"{c145.FACTOR_NAME}_eligible"].astype(bool), c145.FACTOR_NAME
    ]
    if eligible.empty:
        return rows, eligible_rows, None, None
    return rows, eligible_rows, float(eligible.min()), float(eligible.max())


def verify(*, workers: int, confirm_snapshot_verification: bool) -> dict[str, Any]:
    if not confirm_snapshot_verification:
        raise Campaign145SnapshotRecoveryError(
            "recovery verification requires --confirm-snapshot-verification"
        )
    if workers < 1 or workers > 16:
        raise Campaign145SnapshotRecoveryError("--workers must be between 1 and 16")
    manifest = load_and_validate_manifest_metadata()
    validate_recovery_implementation_freeze()
    if RECEIPT.exists():
        raise Campaign145SnapshotRecoveryError("recovery receipt already exists")
    files = list(manifest["files"])
    partition_root = (SNAPSHOT_MANIFEST.parent / "partitions").resolve()
    verified: list[tuple[int, int, float | None, float | None]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_verify_partition, item, partition_root=partition_root)
            for item in files
        ]
        for completed, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            verified.append(future.result())
            if completed % 2500 == 0 or completed == len(futures):
                print(
                    f"Campaign145 recovery verified partitions={completed}/{len(futures)}",
                    file=sys.stderr,
                    flush=True,
                )
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in files
    ]
    rows = sum(item[0] for item in verified)
    eligible_rows = sum(item[1] for item in verified)
    minima = [item[2] for item in verified if item[2] is not None]
    maxima = [item[3] for item in verified if item[3] is not None]
    dataset_sha256 = json_digest(digest_rows)
    if not (
        len(verified) == EXPECTED_PARTITIONS
        and rows == EXPECTED_ROWS
        and eligible_rows == EXPECTED_ELIGIBLE_ROWS
        and dataset_sha256 == SNAPSHOT_DATASET_SHA256
        and file_sha256(SNAPSHOT_MANIFEST) == SNAPSHOT_MANIFEST_SHA256
        and minima
        and maxima
        and min(minima) >= EFFECTIVE_RANGE[0]
        and max(maxima) <= EFFECTIVE_RANGE[1]
    ):
        raise Campaign145SnapshotRecoveryError(
            "snapshot recovery aggregate identity changed"
        )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign145_snapshot_recovery_verification",
        "status": "verified_immutable_snapshot_with_effective_formula_range",
        "snapshot_manifest": {
            "path": str(SNAPSHOT_MANIFEST),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": dataset_sha256,
            "partitions": len(verified),
            "rows": rows,
            "eligible_rows": eligible_rows,
        },
        "known_header_correction": {
            "stored_manifest_range": {c145.FACTOR_NAME: list(STORED_HEADER_RANGE)},
            "effective_verified_range": {c145.FACTOR_NAME: list(EFFECTIVE_RANGE)},
            "snapshot_manifest_or_partition_rewritten": False,
        },
        "observed_eligible_value_range": {
            "minimum": min(minima),
            "maximum": max(maxima),
        },
        "recovery_protocol_sha256": RECOVERY_PROTOCOL_SHA256,
        "recovery_implementation_freeze_sha256": file_sha256(
            RECOVERY_IMPLEMENTATION_FREEZE
        ),
        "receipt_path": str(RECEIPT.relative_to(REPO_ROOT)),
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "stress_2024_2025_returns_opened": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--workers", type=int, default=4)
    verify_parser.add_argument("--confirm-snapshot-verification", action="store_true")
    args = parser.parse_args()
    payload = (
        plan()
        if args.command == "plan"
        else verify(
            workers=args.workers,
            confirm_snapshot_verification=args.confirm_snapshot_verification,
        )
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
