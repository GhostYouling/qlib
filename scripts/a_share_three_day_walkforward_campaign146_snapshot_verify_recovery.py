#!/usr/bin/env python3
"""Verify Campaign146's immutable snapshot after a frozen header-check defect."""

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
    a_share_three_day_walkforward_campaign146_features as c146,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_snapshot_recovery_verification_protocol_20260814.json"
)
RECOVERY_PROTOCOL_SHA256 = (
    "737f2191a147125aa8f159133618b86248f4d0713f6b7659b6969524448e1d39"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_snapshot_verification_failure_20260814.json"
)
FAILURE_RECORD_SHA256 = (
    "a20a3e2c91acd9b26b746985039cc8b37719233088b8dfe0fbcc32f716ea9d7c"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_no_return_implementation_freeze_20260814.json"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "673eff0bf3190a7af6c02dc9439c2688ed4e514e28888ef929f7c7c3c5da887d"
)
RECOVERY_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_snapshot_recovery_verifier_implementation_freeze_20260814.json"
)
RECOVERY_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_snapshot_verify_recovery.py"
)
RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_snapshot_recovery_verification_20260814.json"
)
SNAPSHOT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign146_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign146_feature_library_v1/snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "951872dbdcfa2b00e9603d3be44b059c7d24204fba5757551afbcd46ee8a3f74"
)
SNAPSHOT_DATASET_SHA256 = (
    "7278ae76407215eab75e9ff0119d8c6a073e4d7ac9df5b7d349bc09e6cf889c4"
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_ELIGIBLE_ROWS = 7_630_332
EFFECTIVE_RANGE = (-1.0, 1.0)
EXPECTED_POSITIVE_FREQUENCIES = 59


class Campaign146SnapshotRecoveryError(RuntimeError):
    """Fail closed when an immutable Campaign146 recovery invariant changes."""


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
        raise Campaign146SnapshotRecoveryError(f"{label} changed: {path}")


def load_recovery_protocol() -> dict[str, Any]:
    require_file(RECOVERY_PROTOCOL, RECOVERY_PROTOCOL_SHA256, "recovery protocol")
    require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record")
    protocol = json.loads(RECOVERY_PROTOCOL.read_text(encoding="utf-8"))
    authoritative = protocol.get("authoritative_inputs") or {}
    snapshot = authoritative.get("snapshot_manifest") or {}
    discrepancy = protocol.get("known_frozen_verifier_predicate_discrepancy") or {}
    published = discrepancy.get("published_manifest_values") or {}
    effective = (
        discrepancy.get(
            "effective_values_from_preregistration_formula_and_builder_publication"
        )
        or {}
    )
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign146_snapshot_recovery_verification_protocol"
        and protocol.get("status") == "frozen_before_recovery_partition_reads"
        and (authoritative.get("implementation_freeze") or {}).get("sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and (authoritative.get("verification_failure") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST)
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and snapshot.get("partitions") == EXPECTED_PARTITIONS
        and snapshot.get("rows") == EXPECTED_ROWS
        and snapshot.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and published.get("positive_frequency_count_per_half")
        == EXPECTED_POSITIVE_FREQUENCIES
        and published.get("positive_half_spectral_denominators_required") is True
        and published.get("signed_return_and_amount_magnitudes_used") is True
        and effective.get("factor_range_inclusive") == list(EFFECTIVE_RANGE)
        and discrepancy.get("snapshot_manifest_or_partition_rewrite_allowed") is False
        and discrepancy.get(
            "formula_direction_source_support_gate_or_catalog_change_allowed"
        )
        is False
    ):
        raise Campaign146SnapshotRecoveryError("recovery protocol semantics changed")
    return protocol


def load_and_validate_manifest_metadata() -> dict[str, Any]:
    load_recovery_protocol()
    require_file(
        IMPLEMENTATION_FREEZE,
        IMPLEMENTATION_FREEZE_SHA256,
        "Campaign146 implementation freeze",
    )
    require_file(SNAPSHOT_MANIFEST, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c146.FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign146_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c146.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("partitions") == len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and eligible == EXPECTED_ELIGIBLE_ROWS
        and manifest.get("factor_names") == [c146.FACTOR_NAME]
        and manifest.get("factor_directions") == {c146.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {c146.FACTOR_NAME: list(EFFECTIVE_RANGE)}
        and manifest.get("factor_formulas") == {c146.FACTOR_NAME: c146.FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(c146.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c146.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == c146.SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("positive_frequency_count_per_half")
        == EXPECTED_POSITIVE_FREQUENCIES
        and manifest.get("positive_half_spectral_denominators_required") is True
        and manifest.get("signed_return_and_amount_magnitudes_used") is True
        and manifest.get("raw_manifest_sha256") == c146.RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == c146.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c146.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c146.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c146.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{c146.FACTOR_NAME}__eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get(f"{c146.FACTOR_NAME}__missing_rows")
        == EXPECTED_ROWS - EXPECTED_ELIGIBLE_ROWS
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign146SnapshotRecoveryError("snapshot manifest semantics changed")
    return manifest


def resolve_partition_path(item: dict[str, Any], *, partition_root: Path) -> Path:
    root = partition_root.expanduser().resolve()
    path = Path(str(item.get("path", ""))).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise Campaign146SnapshotRecoveryError(
            f"partition path escapes snapshot: {path}"
        ) from exc
    relative = Path(str(item.get("relative_path", "")))
    if relative.is_absolute() or (root.parent / relative).resolve() != path:
        raise Campaign146SnapshotRecoveryError(
            f"partition relative path changed: {path}"
        )
    return path


def validate_recovery_implementation_freeze() -> dict[str, Any]:
    if not RECOVERY_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign146SnapshotRecoveryError(
            "recovery verifier implementation freeze is absent"
        )
    freeze = json.loads(RECOVERY_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    frozen = freeze.get("frozen_implementation") or {}
    tests = freeze.get("synthetic_verification") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign146_snapshot_recovery_verifier_implementation_freeze"
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
        and boundary.get("coverage_statistics_read") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign146SnapshotRecoveryError(
            "recovery verifier implementation freeze changed"
        )
    return freeze


def plan() -> dict[str, Any]:
    manifest = load_and_validate_manifest_metadata()
    validate_recovery_implementation_freeze()
    if RECEIPT.exists():
        raise Campaign146SnapshotRecoveryError("recovery receipt already exists")
    return {
        "status": "ready",
        "ready": True,
        "snapshot_manifest": str(SNAPSHOT_MANIFEST),
        "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "partitions": len(manifest["files"]),
        "rows": manifest["rows"],
        "eligible_rows": EXPECTED_ELIGIBLE_ROWS,
        "effective_verified_range": list(EFFECTIVE_RANGE),
        "positive_frequency_count_per_half": EXPECTED_POSITIVE_FREQUENCIES,
        "partition_values_read_by_plan": False,
        "coverage_statistics_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _verify_partition(
    item: dict[str, Any], *, partition_root: Path
) -> tuple[int, int, float | None, float | None]:
    path = resolve_partition_path(item, partition_root=partition_root)
    if not path.is_file() or file_sha256(path) != item.get("output_byte_sha256"):
        raise Campaign146SnapshotRecoveryError(f"partition byte hash changed: {path}")
    frame = pd.read_parquet(path, columns=list(c146.OUTPUT_COLUMNS))
    source = c146._generated["source"]
    if (
        tuple(frame.columns) != tuple(c146.OUTPUT_COLUMNS)
        or len(frame) != item.get("rows")
        or source._frame_sha256(frame) != item.get("output_frame_sha256")
    ):
        raise Campaign146SnapshotRecoveryError(f"partition frame changed: {path}")
    rows, eligible_rows = c146.validate_value_semantics(frame)
    stored_eligible = (item.get("factor_eligible_rows") or {}).get(c146.FACTOR_NAME)
    if not (
        item.get("kind")
        == "a_share_three_day_walkforward_campaign146_feature_partition"
        and item.get("status") == "complete_pending_aggregate_publication"
        and item.get("schema_version") == 1
        and item.get("source_fields_read") == list(c146.RAW_COLUMNS)
        and stored_eligible == eligible_rows
        and item.get("protocol_sha256") == c146.PROTOCOL_SHA256
        and item.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and item.get("daily_price_fields_read") == []
        and item.get("forward_return_fields_read") is False
        and item.get("comparison_factor_values_read") is False
        and item.get("provider_request_issued") is False
    ):
        raise Campaign146SnapshotRecoveryError(
            f"partition metadata semantics changed: {path}"
        )
    eligible = frame.loc[
        frame[f"{c146.FACTOR_NAME}_eligible"].astype(bool), c146.FACTOR_NAME
    ]
    if eligible.empty:
        return rows, eligible_rows, None, None
    return rows, eligible_rows, float(eligible.min()), float(eligible.max())


def verify(*, workers: int, confirm_snapshot_verification: bool) -> dict[str, Any]:
    if not confirm_snapshot_verification:
        raise Campaign146SnapshotRecoveryError(
            "recovery verification requires --confirm-snapshot-verification"
        )
    if workers < 1 or workers > 16:
        raise Campaign146SnapshotRecoveryError("--workers must be between 1 and 16")
    manifest = load_and_validate_manifest_metadata()
    validate_recovery_implementation_freeze()
    if RECEIPT.exists():
        raise Campaign146SnapshotRecoveryError("recovery receipt already exists")
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
                    f"Campaign146 recovery verified partitions={completed}/{len(futures)}",
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
        raise Campaign146SnapshotRecoveryError(
            "snapshot recovery aggregate identity changed"
        )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign146_snapshot_recovery_verification",
        "status": "verified_immutable_snapshot_with_corrected_support_header_predicates",
        "snapshot_manifest": {
            "path": str(SNAPSHOT_MANIFEST),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": dataset_sha256,
            "partitions": len(verified),
            "rows": rows,
            "eligible_rows": eligible_rows,
        },
        "known_verifier_predicate_correction": {
            "positive_frequency_count_per_half": EXPECTED_POSITIVE_FREQUENCIES,
            "positive_half_spectral_denominators_required": True,
            "signed_return_and_amount_magnitudes_used": True,
            "snapshot_manifest_or_partition_rewritten": False,
        },
        "observed_eligible_value_range": {
            "minimum": min(minima),
            "maximum": max(maxima),
        },
        "verification": {
            "all_partition_paths_contained": True,
            "all_partition_byte_sha256_verified": True,
            "all_partition_frame_sha256_verified": True,
            "all_partition_rows_and_output_schema_verified": True,
            "all_effective_value_semantics_verified": True,
            "ordered_dataset_digest_recomputed": True,
            "snapshot_manifest_sha256_rechecked_after_partitions": True,
            "exit_code": 0,
        },
        "recovery_protocol_sha256": RECOVERY_PROTOCOL_SHA256,
        "recovery_implementation_freeze_sha256": file_sha256(
            RECOVERY_IMPLEMENTATION_FREEZE
        ),
        "receipt_path": str(RECEIPT.relative_to(REPO_ROOT)),
        "coverage_statistics_read": False,
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
