#!/usr/bin/env python3
"""Verify Campaign120's published snapshot without rewriting stale metadata."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign120_features as c120


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    c120.output_root(c120.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
).resolve()
MANIFEST_SHA256 = "d5b08574c1b0aff1d8a359bf0409b92ddde2ce5caeb7d99b243c434130e94412"
DATASET_SHA256 = "25958413d6238c70bc0b5b9f3ac8b65dca352f3479f04a1867bc23603032af12"
IMPLEMENTATION_FREEZE_PATH = c120.DEFAULT_IMPLEMENTATION_FREEZE.resolve()
IMPLEMENTATION_FREEZE_SHA256 = (
    "b9a46d0a97d251bb1cacd5f8f2e9fd35292ba10ea16c73c50e0178bb38168712"
)
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_120_snapshot_manifest_semantic_failure_20260814.json"
)
FAILURE_RECORD_SHA256 = (
    "8ebfffaf0e9cbf97c587dcf0b74c95ead2ed4959d67b6a2fa7943469c3ed3cce"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_120_snapshot_verifier_recovery_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign120_snapshot_verify_recovery.py"
)


class Campaign120SnapshotRecoveryError(RuntimeError):
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

    protocol = c120.load_protocol()
    exact = protocol["candidate"]["exact_formula"]
    search = protocol["candidate"]["search_space"]
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(c120.FACTOR_NAME)
    if not (
        search.get("parser_count") == 1
        and exact.get("support")
        == "Require exactly 240 valid closes, 238 recognized ternary symbols, exact consumption of both 119-symbol sequences and a finite integer score in [2,238]; constant paths remain valid."
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign120_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == c120.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == DATASET_SHA256
        and manifest.get("partitions") == len(files) == c120.EXPECTED_PARTITIONS
        and manifest.get("rows") == c120.EXPECTED_ROWS
        and manifest.get("factor_names") == [c120.FACTOR_NAME]
        and manifest.get("factor_directions") == {c120.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {c120.FACTOR_NAME: [2.0, 238.0]}
        and manifest.get("factor_formulas") == {c120.FACTOR_NAME: c120.FACTOR_FORMULA}
        and eligible == c120.EXPECTED_ROWS
        and manifest.get("source_fields_read") == list(c120.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(c120.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == 241
        and manifest.get("source_selected_bar_count") == 240
        and manifest.get("dictionary_rule") == c120.FACTOR_FORMULA
        and manifest.get("dictionary_parser_count") == 0
        and manifest.get("exact_symbol_support_required") is False
        and manifest.get("return_magnitude_used_after_direction_encoding") is False
        and manifest.get("raw_manifest_sha256") == c120.RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == c120.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == c120.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == c120.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == c120.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == c120.EXPECTED_ROWS
        and quality.get(f"{c120.FACTOR_NAME}__eligible_rows") == c120.EXPECTED_ROWS
        and quality.get(f"{c120.FACTOR_NAME}__missing_rows") == 0
        and quality.get("invalid_close_sessions") == 0
        and quality.get("parser_support_mismatch_sessions") == 0
        and int(quality.get("recognized_direction_symbol_observations", -1)) > 0
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("training_or_model_fitting_performed") is False
    ):
        raise Campaign120SnapshotRecoveryError(
            "Campaign120 recovered manifest semantics changed"
        )


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign120SnapshotRecoveryError("recovery freeze is absent")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign120_snapshot_verifier_recovery_freeze"
        and record.get("status")
        == "dedicated_read_only_verifier_frozen_before_candidate_partition_values_are_reopened"
        and frozen.get("recovery_verifier_path") == _relative(Path(__file__))
        and frozen.get("recovery_verifier_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("manifest_path") == str(MANIFEST_PATH)
        and frozen.get("manifest_sha256") == MANIFEST_SHA256
        and frozen.get("dataset_sha256") == DATASET_SHA256
        and frozen.get("expected_partitions") == c120.EXPECTED_PARTITIONS
        and frozen.get("expected_rows") == c120.EXPECTED_ROWS
        and frozen.get("expected_eligible_rows") == c120.EXPECTED_ROWS
        and frozen.get("observed_stale_dictionary_parser_count") == 0
        and frozen.get("truthful_frozen_dictionary_parser_count") == 1
        and frozen.get("observed_stale_exact_symbol_support_required") is False
        and frozen.get("truthful_frozen_exact_symbol_support_required") is True
        and test.get("passed") == 4
        and test.get("exit_code") == 0
        and boundary.get("candidate_partition_values_reopened_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign120SnapshotRecoveryError("recovery freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    for path, expected, label in (
        (MANIFEST_PATH, MANIFEST_SHA256, "candidate manifest"),
        (
            IMPLEMENTATION_FREEZE_PATH,
            IMPLEMENTATION_FREEZE_SHA256,
            "original implementation freeze",
        ),
        (FAILURE_RECORD_PATH, FAILURE_RECORD_SHA256, "failure record"),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign120SnapshotRecoveryError(f"{label} changed: {path}")
    c120._validate_implementation_freeze()
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
        raise Campaign120SnapshotRecoveryError("workers must be between 1 and 16")
    static = validate_static_bindings()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    partition_root = (MANIFEST_PATH.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign120SnapshotRecoveryError(
                f"partition byte hash changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(c120.OUTPUT_COLUMNS))
        if (
            len(frame) != int(item["rows"])
            or c120._generated["source"]._frame_sha256(frame)
            != item["output_frame_sha256"]
        ):
            raise Campaign120SnapshotRecoveryError(
                f"partition frame hash changed: {path}"
            )
        return c120.validate_value_semantics(frame)

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
    rows = sum(item_rows for item_rows, _eligible in verified)
    eligible = sum(item_eligible for _rows, item_eligible in verified)
    if (
        c120._generated["_json_digest"](digest_rows) != DATASET_SHA256
        or len(verified) != c120.EXPECTED_PARTITIONS
        or rows != c120.EXPECTED_ROWS
        or eligible != c120.EXPECTED_ROWS
    ):
        raise Campaign120SnapshotRecoveryError("recovered aggregate identity changed")
    return {
        "status": "verified_by_frozen_read_only_recovery_verifier",
        "static_bindings": static,
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "partitions": len(verified),
        "rows": rows,
        "eligible_rows": eligible,
        "integer_value_range_verified": [2, 238],
        "manifest_metadata_discrepancy_preserved": {
            "dictionary_parser_count": {"observed": 0, "truthful_frozen": 1},
            "exact_symbol_support_required": {
                "observed": False,
                "truthful_frozen": True,
            },
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
