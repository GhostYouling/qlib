#!/usr/bin/env python3
"""Finalize Campaign286 on the established nonempty quality-universe domain."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign286_design as base
from scripts import a_share_three_day_walkforward_campaign286_design_recovery as v2


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PARTIAL = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    ".alpha158_development_design_recovery_v2.partial"
)
OUTPUT_ROOT = SOURCE_PARTIAL.parent / "alpha158_development_design_recovery_v3"
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_design_recovery_v3_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_design_recovery_v3.py"
)
V2_FREEZE_PATH = v2.RECOVERY_FREEZE_PATH
V2_FREEZE_SHA256 = "fd853c3957b5a593138b2b94b29912279706a1c5e6b5e0c92e86b26bb192bb74"
V2_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign286_design_recovery.py"
)
V2_RUNNER_SHA256 = "c1514ffba05f9fd93e7d2b85fb9e937e6ef5792f7478668215d112422a133fd0"
FAILURE_EVIDENCE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_zero_denominator_coverage_audit_failure_20260825.json"
)
FAILURE_EVIDENCE_SHA256 = (
    "5976d78f8e835c6273e7a6289277cde7bfdee625c4e9ed206b42f2d057149042"
)
V2_FAILURE_PATH = SOURCE_PARTIAL / "recovery_failure.json"
V2_FAILURE_SHA256 = "f2df02c4900fccda5f9a197068744db8b81cc75dbc412c56d2922ec6810d1385"
SEMANTIC_REFERENCE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign004_features.py"
)
SEMANTIC_REFERENCE_SHA256 = (
    "46b4c8b36698e64612b4b2c98e8cb4e81041100327d93e862722a3c5fb84b33c"
)
PARTITIONS = {
    2019: {
        "sha256": "5860735e85cca233841168ffa4ec49257d122a91348ede4214be4130ccfd2d5a",
        "rows": 885_491,
        "quality_listing_rows": 105_761,
        "feature_support_rows": 885_358,
        "model_support_eligible_rows": 105_761,
        "finite_feature_count_minimum": 83,
        "finite_feature_count_maximum": 158,
    },
    2020: {
        "sha256": "a49c8dc6c564714a8a9755c20619ca7b88de39a51b992240600ca9369ed719cb",
        "rows": 918_981,
        "quality_listing_rows": 184_069,
        "feature_support_rows": 918_730,
        "model_support_eligible_rows": 184_069,
        "finite_feature_count_minimum": 83,
        "finite_feature_count_maximum": 158,
    },
    2021: {
        "sha256": "6cc0536673438dae0ba81a9b91e498092d19d7255f6f67e0031f3e3df7baa456",
        "rows": 989_689,
        "quality_listing_rows": 260_062,
        "feature_support_rows": 989_332,
        "model_support_eligible_rows": 260_044,
        "finite_feature_count_minimum": 83,
        "finite_feature_count_maximum": 158,
    },
    2022: {
        "sha256": "ca91585aa8010f1395c7371af6df5cd746db19ea55144255e175d1fa95ba018d",
        "rows": 1_043_113,
        "quality_listing_rows": 258_274,
        "feature_support_rows": 1_042_662,
        "model_support_eligible_rows": 258_248,
        "finite_feature_count_minimum": 83,
        "finite_feature_count_maximum": 158,
    },
    2023: {
        "sha256": "a0476b145987a5698b989880979f28ee1a6be65435787a1df911d531c3a6ec25",
        "rows": 1_081_725,
        "quality_listing_rows": 193_615,
        "feature_support_rows": 1_081_536,
        "model_support_eligible_rows": 193_615,
        "finite_feature_count_minimum": 83,
        "finite_feature_count_maximum": 158,
    },
}


class Campaign286RecoveryV3Error(RuntimeError):
    """Fail closed when the coverage-domain repair changes."""


def partition_path(year: int, root: Path = SOURCE_PARTIAL) -> Path:
    if year not in PARTITIONS:
        raise Campaign286RecoveryV3Error(f"unfrozen partition year: {year}")
    path = root / "partitions" / f"{year}.parquet"
    base.require_file(path, PARTITIONS[year]["sha256"], f"partition {year}")
    return path


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign286RecoveryV3Error("Campaign286 recovery-v3 freeze absent")
    record = base.load_json(FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_design_recovery_v3_implementation_freeze"
        and record.get("status")
        == "frozen_after_complete_features_before_defined_domain_coverage_audit"
        and (record.get("protocol") or {}).get("sha256") == base.PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == base.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == base.file_sha256(TEST_PATH)
        and boundary.get("historical_label_or_forward_return_values_read") is False
        and boundary.get("threshold_or_model_change") is False
        and boundary.get("feature_partition_recomputation") is False
        and boundary.get("lockbox_2024_2025_feature_or_return_values_read") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign286RecoveryV3Error("Campaign286 recovery-v3 freeze changed")
    bindings = (
        (V2_FREEZE_PATH, V2_FREEZE_SHA256, "recovery-v2 freeze"),
        (V2_RUNNER_PATH, V2_RUNNER_SHA256, "recovery-v2 runner"),
        (FAILURE_EVIDENCE_PATH, FAILURE_EVIDENCE_SHA256, "coverage failure evidence"),
        (V2_FAILURE_PATH, V2_FAILURE_SHA256, "recovery-v2 failure"),
        (
            SEMANTIC_REFERENCE_PATH,
            SEMANTIC_REFERENCE_SHA256,
            "coverage semantic reference",
        ),
    )
    for path, expected, label in bindings:
        base.require_file(path, expected, label)
    for year in PARTITIONS:
        partition_path(year)
    return record


def coverage_summary_defined_domain(daily: pd.DataFrame) -> dict[str, Any]:
    required = {"session", "quality_listing_names", "eligible_names"}
    if set(daily) != required:
        raise Campaign286RecoveryV3Error("daily coverage columns changed")
    ordered = daily.sort_values("session", kind="stable").reset_index(drop=True)
    if (
        len(ordered) == 0
        or ordered["session"].duplicated().any()
        or (ordered[["quality_listing_names", "eligible_names"]] < 0).any().any()
        or (ordered["eligible_names"] > ordered["quality_listing_names"]).any()
    ):
        raise Campaign286RecoveryV3Error("daily coverage identity changed")
    defined = ordered.loc[ordered["quality_listing_names"].gt(0)].reset_index(drop=True)
    excluded = ordered.loc[ordered["quality_listing_names"].eq(0)].reset_index(
        drop=True
    )
    if defined.empty:
        raise Campaign286RecoveryV3Error("coverage denominator domain is empty")
    ratios = defined["eligible_names"] / defined["quality_listing_names"]
    indices = np.arange(0, max(len(defined) - 3, 0), 3)
    potential_mask = defined.iloc[indices]["eligible_names"].ge(50)
    potential = int(potential_mask.sum())
    cohort_dates = pd.to_datetime(
        defined.iloc[indices].loc[potential_mask, "session"], errors="raise"
    )
    years = sorted(int(value) for value in cohort_dates.dt.year.unique())
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    p05_names = float(defined["eligible_names"].quantile(0.05))
    gate = base.COVERAGE_THRESHOLDS
    passed = bool(
        median >= gate["median_daily_feature_row_coverage_minimum"]
        and p05 >= gate["p05_daily_feature_row_coverage_minimum"]
        and p05_names >= gate["p05_eligible_names_minimum"]
        and potential >= gate["non_overlapping_three_session_cohorts_minimum"]
        and len(years) >= gate["cohort_years_minimum"]
    )
    return {
        "quality_listing_rows": int(defined["quality_listing_names"].sum()),
        "model_support_eligible_rows": int(defined["eligible_names"].sum()),
        "calendar_sessions_observed": len(ordered),
        "defined_denominator_sessions": len(defined),
        "zero_denominator_sessions_excluded_from_defined_domain": len(excluded),
        "zero_denominator_first_session": (
            pd.Timestamp(excluded["session"].min()).date().isoformat()
            if not excluded.empty
            else None
        ),
        "zero_denominator_last_session": (
            pd.Timestamp(excluded["session"].max()).date().isoformat()
            if not excluded.empty
            else None
        ),
        "coverage_domain_semantics": "Sessions produced by grouping point-in-time quality/listing eligible keys; zero-row sessions have no defined denominator.",
        "semantic_reference": {
            "path": str(SEMANTIC_REFERENCE_PATH.relative_to(REPO_ROOT)),
            "sha256": SEMANTIC_REFERENCE_SHA256,
            "function": "coverage_and_capacity",
        },
        "median_daily_feature_row_coverage": median,
        "p05_daily_feature_row_coverage": p05,
        "eligible_names_minimum": int(defined["eligible_names"].min()),
        "eligible_names_p05": p05_names,
        "eligible_names_median": float(defined["eligible_names"].median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": years,
        "all_session_counts_sha256": hashlib.sha256(
            ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")
        ).hexdigest(),
        "defined_domain_counts_sha256": hashlib.sha256(
            defined.to_csv(index=False, lineterminator="\n").encode("utf-8")
        ).hexdigest(),
        "thresholds": gate,
        "threshold_change": False,
        "gate_passed_before_historical_label_or_forward_return_read": passed,
    }


def receipts(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for year, expected in PARTITIONS.items():
        path = partition_path(year, root)
        observed = v2.partition_receipt(year, path)
        for key, value in expected.items():
            if observed.get(key) != value:
                raise Campaign286RecoveryV3Error(
                    f"partition {year} receipt changed: {key}"
                )
        records.append(observed)
    return records


def plan() -> dict[str, Any]:
    validate_freeze()
    ready = bool(
        SOURCE_PARTIAL.is_dir()
        and not OUTPUT_ROOT.exists()
        and not (SOURCE_PARTIAL / "snapshot_manifest.json").exists()
        and not (SOURCE_PARTIAL / "structural_audit.json").exists()
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_design_recovery_v3_plan",
        "status": (
            "ready_to_finalize_defined_domain_coverage_without_feature_recompute_or_labels"
            if ready
            else "not_ready_preserve_existing_state"
        ),
        "ready": ready,
        "source_partial": str(SOURCE_PARTIAL),
        "output_root": str(OUTPUT_ROOT),
        "partition_years": list(PARTITIONS),
        "feature_partition_recomputation": False,
        "threshold_or_model_change": False,
        "historical_label_or_forward_return_values_read_by_plan": False,
        "lockbox_2024_2025_feature_or_return_values_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def finalize() -> Path:
    payload = plan()
    if payload["ready"] is not True:
        raise Campaign286RecoveryV3Error("recovery-v3 plan is not ready")
    records = receipts(SOURCE_PARTIAL)
    daily = pd.concat(
        [v2.daily_counts(partition_path(year)) for year in PARTITIONS],
        ignore_index=True,
    )
    coverage = coverage_summary_defined_domain(daily)
    audit = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_alpha158_structural_audit",
        "status": (
            "passed_ready_for_frozen_model_implementation"
            if coverage["gate_passed_before_historical_label_or_forward_return_read"]
            else "failed_terminal_before_historical_label_or_forward_return_read"
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "coverage": coverage,
        "recovery_revision": 3,
        "feature_partitions_recomputed": False,
        "alpha158_feature_values_read": True,
        "historical_label_or_forward_return_values_read": False,
        "model_fitting_performed": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }
    base.atomic_json(SOURCE_PARTIAL / "structural_audit.json", audit)
    digest_rows = [
        [
            record["year"],
            record["rows"],
            record["model_support_eligible_rows"],
            record["sha256"],
        ]
        for record in records
    ]
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_alpha158_development_design",
        "status": (
            "immutable_design_ready_for_model_implementation"
            if audit["status"] == "passed_ready_for_frozen_model_implementation"
            else "immutable_design_failed_structural_gate"
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "protocol": {"path": str(base.PROTOCOL_PATH), "sha256": base.PROTOCOL_SHA256},
        "feature_count": base.FEATURE_COUNT,
        "feature_names": base.feature_config()[1],
        "feature_library_sha256": base.FEATURE_LIBRARY_SHA256,
        "minimum_finite_features": base.MINIMUM_FINITE_FEATURES,
        "development_years": list(base.DEVELOPMENT_YEARS),
        "rows": int(sum(record["rows"] for record in records)),
        "model_support_eligible_rows": int(
            sum(record["model_support_eligible_rows"] for record in records)
        ),
        "partitions": len(records),
        "files": records,
        "dataset_sha256": base.value_sha256(digest_rows),
        "structural_audit": {
            "path": "structural_audit.json",
            "sha256": base.file_sha256(SOURCE_PARTIAL / "structural_audit.json"),
            "gate_passed": coverage[
                "gate_passed_before_historical_label_or_forward_return_read"
            ],
        },
        "recovery": {
            "revision": 3,
            "v2_failure": {
                "path": "recovery_failure.json",
                "sha256": V2_FAILURE_SHA256,
            },
            "coverage_failure_evidence": {
                "path": str(FAILURE_EVIDENCE_PATH),
                "sha256": FAILURE_EVIDENCE_SHA256,
            },
            "reused_partition_years": list(PARTITIONS),
            "feature_partition_recomputation": False,
            "threshold_or_model_change": False,
        },
        "alpha158_feature_values_read": True,
        "historical_label_or_forward_return_values_read": False,
        "model_fitting_performed": False,
        "lockbox_2024_2025_feature_or_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    base.atomic_json(SOURCE_PARTIAL / "snapshot_manifest.json", manifest)
    os.replace(SOURCE_PARTIAL, OUTPUT_ROOT)
    return OUTPUT_ROOT / "snapshot_manifest.json"


def verify(
    manifest_path: Path = OUTPUT_ROOT / "snapshot_manifest.json",
) -> dict[str, Any]:
    validate_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    manifest = base.load_json(manifest_path)
    records = receipts(manifest_path.parent)
    digest_rows = [
        [
            record["year"],
            record["rows"],
            record["model_support_eligible_rows"],
            record["sha256"],
        ]
        for record in records
    ]
    recovery = manifest.get("recovery") or {}
    audit_binding = manifest.get("structural_audit") or {}
    audit_path = manifest_path.parent / str(audit_binding.get("path"))
    base.require_file(
        audit_path, str(audit_binding.get("sha256")), "v3 structural audit"
    )
    audit = base.load_json(audit_path)
    base.require_file(
        manifest_path.parent / "recovery_failure.json",
        V2_FAILURE_SHA256,
        "preserved v2 failure",
    )
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign286_alpha158_development_design"
        and manifest.get("status") == "immutable_design_ready_for_model_implementation"
        and manifest.get("files") == records
        and manifest.get("dataset_sha256") == base.value_sha256(digest_rows)
        and recovery.get("revision") == 3
        and recovery.get("feature_partition_recomputation") is False
        and recovery.get("threshold_or_model_change") is False
        and audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and (audit.get("coverage") or {}).get(
            "gate_passed_before_historical_label_or_forward_return_read"
        )
        is True
        and manifest.get("historical_label_or_forward_return_values_read") is False
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
    ):
        raise Campaign286RecoveryV3Error("Campaign286 recovery-v3 output changed")
    return {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": base.file_sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": manifest["rows"],
        "model_support_eligible_rows": manifest["model_support_eligible_rows"],
        "feature_count": manifest["feature_count"],
        "coverage": audit["coverage"],
        "recovery_revision": 3,
        "historical_label_or_forward_return_values_read": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    finalize_command = subcommands.add_parser("finalize")
    finalize_command.add_argument("--confirm-finalize", action="store_true")
    verify_command = subcommands.add_parser("verify")
    verify_command.add_argument(
        "--manifest", type=Path, default=OUTPUT_ROOT / "snapshot_manifest.json"
    )
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan":
        payload = plan()
    elif args.command == "finalize":
        if not args.confirm_finalize:
            raise Campaign286RecoveryV3Error("finalize requires --confirm-finalize")
        payload = verify(finalize())
    elif args.command == "verify":
        payload = verify(args.manifest)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
