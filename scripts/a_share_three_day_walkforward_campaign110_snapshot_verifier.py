#!/usr/bin/env python3
"""Verify the immutable Campaign110 snapshot; this entry point cannot build it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign110_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_snapshot_verifier_protocol_20260808.json"
)
PROTOCOL_SHA256 = "23aa30bdc564c3dca42eb4ed7202dd790a5cba425d640527826df73337d738bc"
VERIFIER_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_snapshot_verifier_implementation_freeze_20260808.json"
)
VERIFIER_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_snapshot_verifier.py"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "e3ae3c01e0a6eadd8dfce0362520e13bc4c047ff8357cdc7be2d1f9b31e93b72"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "3b46c2c1989a7f197fa04f4452ad460a70139a21a1d6e2e05f4566ab92afdc57"
)


def validate_implementation_freeze() -> dict[str, Any]:
    if not VERIFIER_IMPLEMENTATION_FREEZE.is_file():
        raise candidate.Campaign110FeatureError(
            "Campaign110 snapshot verifier implementation freeze is absent"
        )
    record = json.loads(VERIFIER_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_snapshot_verifier_implementation_freeze"
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
        raise candidate.Campaign110FeatureError(
            "Campaign110 snapshot verifier implementation freeze changed"
        )
    return record


def load_protocol() -> dict[str, Any]:
    if candidate._sha256(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise candidate.Campaign110FeatureError(
            "Campaign110 snapshot verifier protocol changed"
        )
    record = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    corrections = record.get("exact_manifest_expectation_corrections") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_snapshot_verifier_protocol"
        and record.get("status")
        == "frozen_after_manifest_metadata_diagnosis_before_partition_values_coverage_or_comparator_values"
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256")
        == "9082b74891ea2e1c107309637941e42acdc9afeec0b44748e2242506c1a68c4b"
        and snapshot.get("partitions") == candidate.EXPECTED_PARTITIONS
        and snapshot.get("rows") == candidate.EXPECTED_ROWS
        and snapshot.get("eligible_rows") == candidate.EXPECTED_ROWS
        and (record.get("implementation_authority") or {}).get("sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and (corrections.get("fixed_denominator") or {}).get(
            "frozen_expectation"
        )
        == 240
        and (corrections.get("fixed_anchor_and_close_support_required") or {}).get(
            "frozen_expectation"
        )
        is True
        and (corrections.get("exact_reference_ties_retained") or {}).get(
            "frozen_expectation"
        )
        is True
        and boundary.get("partition_values_read_before_protocol_freeze") is False
        and boundary.get("coverage_or_comparator_values_read_before_protocol_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_protocol_freeze"
        )
        is False
        and boundary.get("snapshot_modified_after_publication") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise candidate.Campaign110FeatureError(
            "Campaign110 snapshot verifier protocol semantics changed"
        )
    return record


def validate_manifest(manifest: dict[str, Any]) -> None:
    load_protocol()
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(candidate.FACTOR_NAME)
    quality = manifest.get("quality") or {}
    base = candidate._base_generated
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign110_feature_snapshot"
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
        == list(candidate.IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session")
        == candidate.SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == candidate.SELECTED_BAR_COUNT
        and manifest.get("fixed_denominator") == 240
        and manifest.get("fixed_anchor_and_close_support_required") is True
        and manifest.get("exact_reference_ties_retained") is True
        and manifest.get("raw_manifest_sha256") == base["RAW_MANIFEST_SHA256"]
        and manifest.get("joint_clean_manifest_sha256")
        == candidate.CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256")
        == candidate.CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == candidate.PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256")
        == candidate.MECHANISM_AUDIT_SHA256
        and manifest.get("implementation_freeze_sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and quality.get("base_rows") == candidate.EXPECTED_ROWS
        and quality.get(f"{candidate.FACTOR_NAME}__eligible_rows") == eligible
        and quality.get(f"{candidate.FACTOR_NAME}__missing_rows")
        == candidate.EXPECTED_ROWS - eligible
        and quality.get("invalid_anchor_or_close_sessions") == 0
        and quality.get("invalid_fixed_denominator_sessions") == 0
        and quality.get("nonzero_reference_state_bars")
        + quality.get("equal_reference_bars")
        == quality.get("raw_source_sessions") * candidate.FIXED_DENOMINATOR
        and quality.get("raw_source_rows_read")
        == quality.get("raw_source_sessions") * candidate.SOURCE_BAR_COUNT
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise candidate.Campaign110FeatureError(
            "Campaign110 verify-only manifest semantics changed"
        )


candidate._base_generated["_validate_manifest"] = validate_manifest
candidate._generated["_validate_manifest"] = validate_manifest
verify_snapshot_files = candidate.verify_snapshot_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    validate_implementation_freeze()
    if args.manifest.expanduser().resolve() != SNAPSHOT_MANIFEST_PATH.resolve():
        raise candidate.Campaign110FeatureError(
            "Campaign110 verifier accepts only the frozen snapshot manifest"
        )
    if candidate._sha256(SNAPSHOT_MANIFEST_PATH) != SNAPSHOT_MANIFEST_SHA256:
        raise candidate.Campaign110FeatureError(
            "Campaign110 published snapshot manifest changed"
        )
    result = verify_snapshot_files(args.manifest, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
