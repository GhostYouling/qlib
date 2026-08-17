#!/usr/bin/env python3
"""Verify Campaign121's published snapshot without rewriting stale metadata."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign121_features as c121


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    c121.output_root(c121.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
).resolve()
MANIFEST_SHA256 = "e5789da9896535d8d67e0f0f3a7b2704f41292e4694b127a27999224abfad724"
DATASET_SHA256 = "cb476bcc93e7c88df6e2666af9d60d470c90f8a7670ea4553d2e9b877ab8a5b2"
RAW_MANIFEST_SHA256 = "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
IMPLEMENTATION_FREEZE_PATH = c121.DEFAULT_IMPLEMENTATION_FREEZE.resolve()
IMPLEMENTATION_FREEZE_SHA256 = (
    "394a56dddea4cf6648ac9a3b53edd6b02891fcec328d0af038ae07e9cf50a007"
)
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_snapshot_manifest_semantic_failure_20260814.json"
)
FAILURE_RECORD_SHA256 = (
    "c5349c8a0bef8de40b075295b74c515c835158e4179765a2f3e7dda34f7e4431"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_snapshot_verifier_recovery_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign121_snapshot_verify_recovery.py"
)


class Campaign121SnapshotRecoveryError(RuntimeError):
    """Fail closed when a frozen recovery input or snapshot byte changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def validate_manifest_metadata(manifest: dict[str, Any]) -> None:
    """Validate metadata only; never open a candidate partition here."""

    protocol = c121.load_protocol()
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c121.FACTOR_NAME)
    if not (
        protocol["candidate"]["exact_formula"]["valid_range_inclusive"] == [0.0, 1.0]
        and protocol["candidate"]["exact_formula"]["normalization"]
        == "fixed 239-position span"
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign121_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c121.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == DATASET_SHA256
        and manifest.get("partitions") == len(files) == c121.EXPECTED_PARTITIONS
        and manifest.get("rows") == c121.EXPECTED_ROWS
        and manifest.get("factor_names") == [c121.FACTOR_NAME]
        and manifest.get("factor_directions") == {c121.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {c121.FACTOR_NAME: [-1.0, 1.0]}
        and manifest.get("fixed_denominator") == 240
        and manifest.get("factor_formulas") == {c121.FACTOR_NAME: c121.FACTOR_FORMULA}
        and manifest.get("terminal_first_attainment_rule") == c121.FACTOR_FORMULA
        and eligible == c121.EXPECTED_ROWS
        and manifest.get("source_fields_read") == list(c121.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c121.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == 241
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == c121.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c121.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c121.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c121.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == c121.EXPECTED_ROWS
        and quality.get(f"{c121.FACTOR_NAME}__eligible_rows") == c121.EXPECTED_ROWS
        and quality.get(f"{c121.FACTOR_NAME}__missing_rows") == 0
        and quality.get("invalid_anchor_or_close_sessions") == 0
        and quality.get("invalid_fixed_denominator_sessions") == 0
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("training_or_model_fitting_performed") is False
    ):
        raise Campaign121SnapshotRecoveryError(
            "Campaign121 recovered manifest semantics changed"
        )


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign121SnapshotRecoveryError("recovery freeze is absent")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign121_snapshot_verifier_recovery_freeze"
        and record.get("status")
        == "dedicated_read_only_verifier_frozen_before_candidate_partition_values_are_reopened"
        and frozen.get("recovery_verifier_path") == _relative(Path(__file__))
        and frozen.get("recovery_verifier_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("manifest_path") == str(MANIFEST_PATH)
        and frozen.get("manifest_sha256") == MANIFEST_SHA256
        and frozen.get("dataset_sha256") == DATASET_SHA256
        and frozen.get("expected_partitions") == c121.EXPECTED_PARTITIONS
        and frozen.get("expected_rows") == c121.EXPECTED_ROWS
        and frozen.get("expected_eligible_rows") == c121.EXPECTED_ROWS
        and frozen.get("observed_stale_factor_range") == [-1.0, 1.0]
        and frozen.get("truthful_frozen_factor_range") == [0.0, 1.0]
        and frozen.get("observed_stale_fixed_denominator") == 240
        and frozen.get("truthful_frozen_position_span") == 239
        and test.get("passed") == 4
        and test.get("exit_code") == 0
        and boundary.get("candidate_partition_values_reopened_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign121SnapshotRecoveryError("recovery freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    for path, expected, label in (
        (MANIFEST_PATH, MANIFEST_SHA256, "candidate manifest"),
        (
            IMPLEMENTATION_FREEZE_PATH,
            IMPLEMENTATION_FREEZE_SHA256,
            "implementation freeze v2",
        ),
        (FAILURE_RECORD_PATH, FAILURE_RECORD_SHA256, "failure record"),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign121SnapshotRecoveryError(f"{label} changed: {path}")
    c121._validate_implementation_freeze()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_manifest_metadata(manifest)
    freeze = _validate_recovery_freeze()
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "implementation_freeze_sha256": IMPLEMENTATION_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "recovery_freeze_sha256": _sha256(RECOVERY_FREEZE_PATH),
        "candidate_partition_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "recovery_status": freeze["status"],
    }


def verify_snapshot(*, workers: int = 8) -> dict[str, Any]:
    if workers < 1 or workers > 16:
        raise Campaign121SnapshotRecoveryError("workers must be between 1 and 16")
    static = validate_static_bindings()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    partition_root = (MANIFEST_PATH.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int, float, float]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign121SnapshotRecoveryError(
                f"partition byte hash changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(c121.OUTPUT_COLUMNS))
        if (
            len(frame) != int(item["rows"])
            or c121.source._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign121SnapshotRecoveryError(
                f"partition frame hash changed: {path}"
            )
        rows, eligible = c121.validate_value_semantics(frame)
        values = pd.to_numeric(frame.loc[frame.iloc[:, -1], c121.FACTOR_NAME])
        return rows, eligible, float(values.min()), float(values.max())

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
    rows = sum(item_rows for item_rows, _eligible, _minimum, _maximum in verified)
    eligible = sum(
        item_eligible for _rows, item_eligible, _minimum, _maximum in verified
    )
    minimum = min(item_minimum for _rows, _eligible, item_minimum, _maximum in verified)
    maximum = max(item_maximum for _rows, _eligible, _minimum, item_maximum in verified)
    if (
        c121._base_generated["_json_digest"](digest_rows) != DATASET_SHA256
        or len(verified) != c121.EXPECTED_PARTITIONS
        or rows != c121.EXPECTED_ROWS
        or eligible != c121.EXPECTED_ROWS
        or minimum < 0.0
        or maximum > 1.0
    ):
        raise Campaign121SnapshotRecoveryError("recovered aggregate identity changed")
    return {
        "status": "verified_by_frozen_read_only_recovery_verifier",
        "static_bindings": static,
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "partitions": len(verified),
        "rows": rows,
        "eligible_rows": eligible,
        "observed_value_minimum": minimum,
        "observed_value_maximum": maximum,
        "truthful_value_range_verified": [0.0, 1.0],
        "truthful_position_lattice_denominator": 239,
        "manifest_metadata_discrepancy_preserved": {
            "factor_range": {"observed": [-1.0, 1.0], "truthful": [0.0, 1.0]},
            "fixed_denominator": {"observed": 240, "truthful": 239},
        },
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
