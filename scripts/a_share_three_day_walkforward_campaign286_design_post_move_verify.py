#!/usr/bin/env python3
"""Read-only verification for Campaign286's atomically moved design output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign286_design as base
from scripts import a_share_three_day_walkforward_campaign286_design_recovery as v2
from scripts import a_share_three_day_walkforward_campaign286_design_recovery_v3 as v3


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = v3.OUTPUT_ROOT
MANIFEST_PATH = OUTPUT_ROOT / "snapshot_manifest.json"
MANIFEST_SHA256 = "31cba0be801ac1421ef9555b862575089589ec08397c1420be3fc4f43b111d4e"
AUDIT_PATH = OUTPUT_ROOT / "structural_audit.json"
AUDIT_SHA256 = "af8feacbfd28b505bc2cddf007e6692c16519f74a1a9f195438d39122705ec8b"
PRESERVED_FAILURE_PATH = OUTPUT_ROOT / "recovery_failure.json"
PRESERVED_FAILURE_SHA256 = (
    "f2df02c4900fccda5f9a197068744db8b81cc75dbc412c56d2922ec6810d1385"
)
PATH_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_post_move_verification_path_failure_20260825.json"
)
PATH_FAILURE_SHA256 = "f45b2803417c5588c164e3cc53993a449320674e3924996bd076e3fa522f9777"
V3_FREEZE_PATH = v3.FREEZE_PATH
V3_FREEZE_SHA256 = "2f3b7dbd58c4def6e264813b56da43634a0f6005797c1e0e14cf0a743338102a"
V3_RUNNER_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign286_design_recovery_v3.py"
)
V3_RUNNER_SHA256 = "429d371ce7087be5cd2e0e2f5f3eaaf71632e3b47e8d817f66e1bf46418d3b74"
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_post_move_verifier_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_design_post_move_verify.py"
)


class Campaign286PostMoveVerifyError(RuntimeError):
    """Fail closed if the published design or verifier changes."""


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign286PostMoveVerifyError("post-move verifier freeze absent")
    record = base.load_json(FREEZE_PATH)
    runner = record.get("verifier") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_post_move_verifier_implementation_freeze"
        and record.get("status")
        == "frozen_after_atomic_move_before_successful_full_output_verification"
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == base.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == base.file_sha256(TEST_PATH)
        and boundary.get("historical_label_or_forward_return_values_read") is False
        and boundary.get("feature_or_threshold_change") is False
        and boundary.get("lockbox_2024_2025_feature_or_return_values_read") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign286PostMoveVerifyError("post-move verifier freeze changed")
    bindings = (
        (V3_FREEZE_PATH, V3_FREEZE_SHA256, "recovery-v3 freeze"),
        (V3_RUNNER_PATH, V3_RUNNER_SHA256, "recovery-v3 runner"),
        (PATH_FAILURE_PATH, PATH_FAILURE_SHA256, "post-move path failure"),
        (MANIFEST_PATH, MANIFEST_SHA256, "published manifest"),
        (AUDIT_PATH, AUDIT_SHA256, "published structural audit"),
        (PRESERVED_FAILURE_PATH, PRESERVED_FAILURE_SHA256, "preserved v2 failure"),
    )
    for path, expected, label in bindings:
        base.require_file(path, expected, label)
    return record


def document_semantics(manifest: dict[str, Any], audit: dict[str, Any]) -> None:
    coverage = audit.get("coverage") or {}
    recovery = manifest.get("recovery") or {}
    _, feature_names = base.feature_config()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign286_alpha158_development_design"
        and manifest.get("status") == "immutable_design_ready_for_model_implementation"
        and manifest.get("feature_count") == base.FEATURE_COUNT
        and manifest.get("feature_names") == feature_names
        and manifest.get("feature_library_sha256") == base.FEATURE_LIBRARY_SHA256
        and manifest.get("minimum_finite_features") == base.MINIMUM_FINITE_FEATURES
        and manifest.get("development_years") == list(base.DEVELOPMENT_YEARS)
        and manifest.get("partitions") == len(manifest.get("files") or []) == 5
        and recovery.get("revision") == 3
        and recovery.get("feature_partition_recomputation") is False
        and recovery.get("threshold_or_model_change") is False
        and audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and audit.get("recovery_revision") == 3
        and audit.get("feature_partitions_recomputed") is False
        and coverage.get("calendar_sessions_observed") == 1214
        and coverage.get("defined_denominator_sessions") == 1147
        and coverage.get("zero_denominator_sessions_excluded_from_defined_domain") == 67
        and coverage.get("zero_denominator_first_session") == "2019-01-02"
        and coverage.get("zero_denominator_last_session") == "2019-04-12"
        and coverage.get("median_daily_feature_row_coverage") == 1.0
        and coverage.get("p05_daily_feature_row_coverage") == 1.0
        and float(coverage.get("eligible_names_p05")) == 110.30000000000001
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 379
        and coverage.get("observed_cohort_years") == list(base.DEVELOPMENT_YEARS)
        and coverage.get("thresholds") == base.COVERAGE_THRESHOLDS
        and coverage.get("threshold_change") is False
        and coverage.get("gate_passed_before_historical_label_or_forward_return_read")
        is True
        and manifest.get("historical_label_or_forward_return_values_read") is False
        and audit.get("historical_label_or_forward_return_values_read") is False
        and manifest.get("model_fitting_performed") is False
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign286PostMoveVerifyError("published document semantics changed")


def verify() -> dict[str, Any]:
    validate_freeze()
    manifest = base.load_json(MANIFEST_PATH)
    audit = base.load_json(AUDIT_PATH)
    document_semantics(manifest, audit)
    records: list[dict[str, Any]] = []
    for year, expected in v3.PARTITIONS.items():
        path = OUTPUT_ROOT / "partitions" / f"{year}.parquet"
        base.require_file(path, expected["sha256"], f"published partition {year}")
        observed = v2.partition_receipt(year, path)
        for key, value in expected.items():
            if observed.get(key) != value:
                raise Campaign286PostMoveVerifyError(
                    f"published partition {year} changed: {key}"
                )
        records.append(observed)
    digest_rows = [
        [
            record["year"],
            record["rows"],
            record["model_support_eligible_rows"],
            record["sha256"],
        ]
        for record in records
    ]
    if not (
        manifest.get("files") == records
        and manifest.get("rows") == 4_918_999
        and manifest.get("model_support_eligible_rows") == 1_001_737
        and manifest.get("dataset_sha256")
        == base.value_sha256(digest_rows)
        == "714f4ccbdf4bfbaccfd04f543ec8c6a0bc345d3cc567ab621d01905130c46252"
        and (manifest.get("structural_audit") or {}).get("sha256") == AUDIT_SHA256
        and (manifest.get("structural_audit") or {}).get("gate_passed") is True
        and (manifest.get("recovery") or {}).get("v2_failure", {}).get("sha256")
        == PRESERVED_FAILURE_SHA256
    ):
        raise Campaign286PostMoveVerifyError("published dataset binding changed")
    return {
        "status": "verified_ready_for_model_implementation_freeze",
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": MANIFEST_SHA256,
        "structural_audit_sha256": AUDIT_SHA256,
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": manifest["rows"],
        "model_support_eligible_rows": manifest["model_support_eligible_rows"],
        "feature_count": manifest["feature_count"],
        "coverage": audit["coverage"],
        "historical_label_or_forward_return_values_read": False,
        "lockbox_2024_2025_feature_or_return_values_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
