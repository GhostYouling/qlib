#!/usr/bin/env python3
"""Verify the immutable Campaign109 snapshot; this entry point cannot build it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign109_features_v2 as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_snapshot_verifier_protocol_20260808.json"
)
PROTOCOL_SHA256 = "cbc4962ad833d1d099d98b7687290de3521037f60cdc568d19978d0424fb81e2"
VERIFIER_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_snapshot_verifier_implementation_freeze_20260808.json"
)
VERIFIER_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign109_snapshot_verifier.py"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "b212eac0921bbca2c3a84c6eceb7f6741939c52ccb96a21e3897d1533c8b6aba"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "911c6d748a11d99ecbace961310acc3bd90a18ada1392d0b6f7e3461ceb37ca0"
)


def validate_implementation_freeze() -> dict[str, Any]:
    if not VERIFIER_IMPLEMENTATION_FREEZE.is_file():
        raise candidate.Campaign109FeatureError(
            "Campaign109 snapshot verifier implementation freeze is absent"
        )
    record = json.loads(
        VERIFIER_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8")
    )
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign109_snapshot_verifier_implementation_freeze"
        and record.get("status")
        == "frozen_before_partition_values_coverage_or_comparator_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("verifier") or {}).get("sha256")
        == candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == candidate._sha256(VERIFIER_TEST_PATH)
        and (record.get("candidate_snapshot") or {}).get("sha256")
        == SNAPSHOT_MANIFEST_SHA256
        and boundary.get("partition_values_read_before_implementation_freeze")
        is False
        and boundary.get(
            "coverage_or_comparator_values_read_before_implementation_freeze"
        )
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_implementation_freeze"
        )
        is False
        and boundary.get("snapshot_modified_after_publication") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise candidate.Campaign109FeatureError(
            "Campaign109 snapshot verifier implementation freeze changed"
        )
    return record


def load_protocol() -> dict[str, Any]:
    if candidate._sha256(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise candidate.Campaign109FeatureError(
            "Campaign109 snapshot verifier protocol changed"
        )
    record = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    corrections = record.get("exact_manifest_expectation_corrections") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign109_snapshot_verifier_protocol"
        and record.get("status")
        == "frozen_after_manifest_metadata_diagnosis_before_partition_values_coverage_or_comparator_values"
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256")
        == "f222c80e80acb9872cc7e29a0fc89ab37e51bc1ee02f40f19f683c3757fcdb90"
        and snapshot.get("partitions") == candidate.EXPECTED_PARTITIONS
        and snapshot.get("rows") == candidate.EXPECTED_ROWS
        and snapshot.get("eligible_rows") == 7694849
        and (record.get("implementation_authority") or {}).get("sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and (corrections.get("fixed_pair_count") or {}).get(
            "frozen_expectation"
        )
        == 238
        and (corrections.get("positive_body_variance_required") or {}).get(
            "frozen_expectation"
        )
        is True
        and (corrections.get("absolute_body_magnitude_used") or {}).get(
            "frozen_expectation"
        )
        is True
        and boundary.get("partition_values_read_before_protocol_freeze") is False
        and boundary.get(
            "coverage_or_comparator_values_read_before_protocol_freeze"
        )
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_protocol_freeze"
        )
        is False
        and boundary.get("snapshot_modified_after_publication") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise candidate.Campaign109FeatureError(
            "Campaign109 snapshot verifier protocol semantics changed"
        )
    return record


def validate_manifest(manifest: dict[str, Any]) -> None:
    load_protocol()
    base = candidate.base
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(
        candidate.FACTOR_NAME
    )
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign109_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == candidate.OUTPUT_RUN_ID
        and manifest.get("partitions")
        == len(files)
        == candidate.EXPECTED_PARTITIONS
        and manifest.get("rows") == candidate.EXPECTED_ROWS
        and manifest.get("factor_names") == [candidate.FACTOR_NAME]
        and manifest.get("factor_directions")
        == {candidate.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges")
        == {candidate.FACTOR_NAME: [-1.0, 1.0]}
        and manifest.get("factor_formulas")
        == {candidate.FACTOR_NAME: candidate.FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(candidate.RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(base.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session")
        == base.SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == base.SELECTED_BAR_COUNT
        and manifest.get("fixed_pair_count") == 238
        and manifest.get("positive_body_variance_required") is True
        and manifest.get("absolute_body_magnitude_used") is True
        and manifest.get("raw_manifest_sha256")
        == candidate._generated["RAW_MANIFEST_SHA256"]
        and manifest.get("joint_clean_manifest_sha256")
        == candidate.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256")
        == candidate.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == base.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == base.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == candidate.EXPECTED_ROWS
        and quality.get(f"{candidate.FACTOR_NAME}__eligible_rows") == eligible
        and quality.get(f"{candidate.FACTOR_NAME}__missing_rows")
        == candidate.EXPECTED_ROWS - eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise candidate.Campaign109FeatureError(
            "Campaign109 verify-only manifest semantics changed"
        )


candidate._generated["_validate_manifest"] = validate_manifest
verify_snapshot_files = candidate.verify_snapshot_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    validate_implementation_freeze()
    if args.manifest.expanduser().resolve() != SNAPSHOT_MANIFEST_PATH.resolve():
        raise candidate.Campaign109FeatureError(
            "Campaign109 verifier accepts only the frozen snapshot manifest"
        )
    if candidate._sha256(SNAPSHOT_MANIFEST_PATH) != SNAPSHOT_MANIFEST_SHA256:
        raise candidate.Campaign109FeatureError(
            "Campaign109 published snapshot manifest changed"
        )
    result = verify_snapshot_files(args.manifest, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
