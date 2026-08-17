#!/usr/bin/env python3
"""Verify Campaign117's existing snapshot after a metadata-only verifier mismatch."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign117_features as c117


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    c117.output_root(c117.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
).resolve()
MANIFEST_SHA256 = "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879"
DATASET_SHA256 = "4f5bf6ee2c26f6956178d6954aae92821530c90a6334375e8cf0e9938fa71c18"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_no_return_implementation_freeze_20260813.json"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "aed04a80f21f5e1a6ed2e5a3f51446943a0f924f95d788f2e03a5014f1c3129e"
)
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_snapshot_verifier_failure_20260813.json"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_snapshot_verifier_recovery_freeze_20260813.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign117_snapshot_verify_recovery.py"
)


class Campaign117SnapshotRecoveryError(RuntimeError):
    """Fail closed when the recovery verifier's frozen inputs change."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def validate_manifest_metadata(manifest: dict[str, Any]) -> None:
    """Validate metadata only; this function never opens partition values."""

    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c117.FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign117_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c117.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == DATASET_SHA256
        and manifest.get("partitions") == len(files) == c117.EXPECTED_PARTITIONS
        and manifest.get("rows") == c117.EXPECTED_ROWS
        and manifest.get("factor_names") == [c117.FACTOR_NAME]
        and manifest.get("factor_directions") == {c117.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {c117.FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("factor_formulas") == {c117.FACTOR_NAME: c117.FACTOR_FORMULA}
        and eligible == c117.EXPECTED_ROWS
        and manifest.get("source_fields_read") == list(c117.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c117.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == 241
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("weak_order_state_count") == 13
        and manifest.get("positive_total_amount_required") is True
        and manifest.get("amount_magnitude_used_after_ordinal_encoding") is False
        and manifest.get("raw_manifest_sha256") == c117.RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == c117.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c117.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c117.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c117.MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == c117.EXPECTED_ROWS
        and quality.get(f"{c117.FACTOR_NAME}__eligible_rows") == c117.EXPECTED_ROWS
        and quality.get(f"{c117.FACTOR_NAME}__missing_rows") == 0
        and quality.get("invalid_amount_sessions") == 0
        and int(quality.get("recognized_state_observations", -1)) > 0
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign117SnapshotRecoveryError(
            "Campaign117 recovered manifest semantics changed"
        )


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign117SnapshotRecoveryError("recovery freeze is absent")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_snapshot_verifier_recovery_freeze"
        and record.get("status")
        == "dedicated_verifier_frozen_before_candidate_partition_values_are_reopened"
        and frozen.get("recovery_verifier_path") == _relative(Path(__file__))
        and frozen.get("recovery_verifier_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("manifest_path") == str(MANIFEST_PATH)
        and frozen.get("manifest_sha256") == MANIFEST_SHA256
        and frozen.get("dataset_sha256") == DATASET_SHA256
        and test.get("passed") == 4
        and test.get("exit_code") == 0
        and boundary.get("candidate_partition_values_reopened_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign117SnapshotRecoveryError("recovery freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    for path, expected, label in (
        (MANIFEST_PATH, MANIFEST_SHA256, "candidate manifest"),
        (
            IMPLEMENTATION_FREEZE_PATH,
            IMPLEMENTATION_FREEZE_SHA256,
            "original implementation freeze",
        ),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign117SnapshotRecoveryError(f"{label} changed: {path}")
    if not FAILURE_RECORD_PATH.is_file():
        raise Campaign117SnapshotRecoveryError("infrastructure failure record absent")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_manifest_metadata(manifest)
    freeze = _validate_recovery_freeze()
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "implementation_freeze_sha256": IMPLEMENTATION_FREEZE_SHA256,
        "failure_record_sha256": _sha256(FAILURE_RECORD_PATH),
        "recovery_freeze_sha256": _sha256(RECOVERY_FREEZE_PATH),
        "candidate_partition_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "recovery_status": freeze["status"],
    }


def verify_snapshot(*, workers: int = 8) -> dict[str, Any]:
    if workers < 1 or workers > 16:
        raise Campaign117SnapshotRecoveryError("workers must be between 1 and 16")
    static = validate_static_bindings()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    partition_root = (MANIFEST_PATH.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign117SnapshotRecoveryError(
                f"partition byte hash changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(c117.OUTPUT_COLUMNS))
        if (
            len(frame) != int(item["rows"])
            or c117._generated["source"]._frame_sha256(frame)
            != item["output_frame_sha256"]
        ):
            raise Campaign117SnapshotRecoveryError(
                f"partition frame hash changed: {path}"
            )
        return c117.validate_value_semantics(frame)

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
    if (
        c117._generated["_json_digest"](digest_rows) != DATASET_SHA256
        or len(verified) != c117.EXPECTED_PARTITIONS
        or sum(rows for rows, _eligible in verified) != c117.EXPECTED_ROWS
        or sum(eligible for _rows, eligible in verified) != c117.EXPECTED_ROWS
    ):
        raise Campaign117SnapshotRecoveryError("recovered aggregate identity changed")
    return {
        "status": "verified_by_frozen_recovery_verifier",
        "static_bindings": static,
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "partitions": len(verified),
        "rows": sum(rows for rows, _eligible in verified),
        "eligible_rows": sum(eligible for _rows, eligible in verified),
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(verify_snapshot(workers=args.workers), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
