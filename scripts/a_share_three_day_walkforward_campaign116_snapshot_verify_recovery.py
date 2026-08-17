#!/usr/bin/env python3
"""Verify the immutable Campaign116 snapshot after a frozen validator-only repair."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign116_features as c116


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_snapshot_verification_recovery_protocol_20260812.json"
)
PROTOCOL_SHA256 = "eb126acf714d86e84595de87c2bb1d9fdb4dfd7967935e8742ef06101953e021"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_snapshot_verification_recovery_implementation_freeze_20260812.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign116_snapshot_verify_recovery.py"
)
ORIGINAL_BUILDER_SHA256 = (
    "84e6dcc40ea50c51a15f04c32c71e086376f2a8c2b3736492a44f219be062286"
)
MANIFEST_PATH = (
    Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
    / "derived/a_share/rich/tushare/minute_walkforward_campaign116_feature_library"
    / c116.OUTPUT_RUN_ID
    / "snapshot_manifest.json"
)
MANIFEST_SHA256 = "d1036a44495206b2329910d71915a7cd861fdc3baf8344a466d66f1cb1787163"
DATASET_SHA256 = "28e9b79514fe905749a3a182d0b3651331c4afb5330e03276c117d58f3b1082a"


class Campaign116SnapshotRecoveryError(RuntimeError):
    """Raised when the narrow frozen recovery boundary changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    target = path.expanduser().resolve()
    if not target.is_file() or _sha256(target) != expected:
        raise Campaign116SnapshotRecoveryError(f"{label} fingerprint changed")


def load_recovery_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "recovery protocol")
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    allowed = spec.get("allowed_recovery") or {}
    expectations = allowed.get("corrected_manifest_expectations") or {}
    snapshot = (
        (spec.get("authoritative_inputs") or {}).get("published_snapshot_manifest")
        or {}
    )
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign116_snapshot_verification_recovery_protocol"
        and spec.get("status")
        == "frozen_after_manifest_metadata_only_failure_diagnosis_before_partition_or_comparator_values"
        and allowed.get("separate_verifier_only") is True
        and allowed.get("original_builder_or_snapshot_modification_allowed") is False
        and expectations
        == {
            "minimum_group_support": 30,
            "positive_total_activity_required": True,
            "endpoint_amount_used": True,
        }
        and allowed.get("comparator_value_use") is False
        and allowed.get("daily_price_or_forward_return_use") is False
        and snapshot.get("byte_sha256") == MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == DATASET_SHA256
        and snapshot.get("partitions") == c116.EXPECTED_PARTITIONS
        and snapshot.get("rows") == c116.EXPECTED_ROWS
    ):
        raise Campaign116SnapshotRecoveryError("recovery protocol semantics changed")
    return spec


def _validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign116SnapshotRecoveryError("recovery implementation freeze absent")
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    code = record.get("recovery_verifier") or {}
    test = record.get("synthetic_test") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign116_snapshot_verification_recovery_implementation_freeze"
        and record.get("status")
        == "separate_verifier_frozen_before_partition_verification_or_comparator_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and code.get("sha256") == _sha256(Path(__file__).resolve())
        and test.get("sha256") == _sha256(TEST_PATH)
        and test.get("exit_code") == 0
        and test.get("passed") == 3
        and boundary.get("partition_values_read_before_freeze") is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign116SnapshotRecoveryError(
            "recovery implementation freeze changed"
        )
    return record


def validate_manifest_metadata(manifest: dict[str, Any]) -> None:
    """Apply the original checks with only the three preregistered corrections."""

    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c116.FACTOR_NAME)
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign116_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c116.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == DATASET_SHA256
        and manifest.get("partitions") == len(files) == c116.EXPECTED_PARTITIONS
        and manifest.get("rows") == c116.EXPECTED_ROWS
        and manifest.get("factor_names") == [c116.FACTOR_NAME]
        and manifest.get("factor_directions") == {c116.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {c116.FACTOR_NAME: [-1.0, 1.0]}
        and manifest.get("factor_formulas")
        == {c116.FACTOR_NAME: c116.FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(c116.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c116.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == c116.SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("minimum_group_support") == 30
        and manifest.get("positive_total_activity_required") is True
        and manifest.get("endpoint_amount_used") is True
        and manifest.get("raw_manifest_sha256") == c116.RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256")
        == c116.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c116.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c116.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c116.MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == c116.EXPECTED_ROWS
        and quality.get(f"{c116.FACTOR_NAME}__eligible_rows") == eligible
        and quality.get(f"{c116.FACTOR_NAME}__missing_rows")
        == c116.EXPECTED_ROWS - eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign116SnapshotRecoveryError("recovered manifest semantics changed")


def verify_snapshot(*, workers: int = 4) -> dict[str, Any]:
    if workers < 1 or workers > 16:
        raise Campaign116SnapshotRecoveryError("workers must be between 1 and 16")
    load_recovery_protocol()
    _validate_implementation_freeze()
    _require(
        REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign116_features.py",
        ORIGINAL_BUILDER_SHA256,
        "original builder",
    )
    _require(MANIFEST_PATH, MANIFEST_SHA256, "published manifest")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_manifest_metadata(manifest)
    partition_root = (MANIFEST_PATH.parent / "partitions").resolve()
    source = c116._generated["source"]

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign116SnapshotRecoveryError(
                f"partition byte hash changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(c116.OUTPUT_COLUMNS))
        if (
            len(frame) != int(item["rows"])
            or source._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign116SnapshotRecoveryError(f"partition frame changed: {path}")
        return c116.validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        verified = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    expected_eligible = manifest["factor_eligible_rows"][c116.FACTOR_NAME]
    rows = sum(item[0] for item in verified)
    eligible = sum(item[1] for item in verified)
    if not (
        _json_digest(digest_rows) == DATASET_SHA256
        and len(verified) == c116.EXPECTED_PARTITIONS
        and rows == c116.EXPECTED_ROWS
        and eligible == expected_eligible
    ):
        raise Campaign116SnapshotRecoveryError("snapshot aggregate identity changed")
    return {
        "status": "verified_by_frozen_separate_recovery_verifier",
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "partitions": len(verified),
        "rows": rows,
        "eligible_rows": eligible,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-verify", action="store_true")
    args = parser.parse_args()
    if not args.confirm_verify:
        raise Campaign116SnapshotRecoveryError("requires --confirm-verify")
    print(json.dumps(verify_snapshot(workers=args.workers), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

