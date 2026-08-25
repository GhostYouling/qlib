#!/usr/bin/env python3
"""Recover Campaign286's interrupted Alpha158 design without changing its science."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_short_horizon_factor_research as research
from scripts import a_share_three_day_walkforward_campaign286_design as base


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = Path("/Volumes/DIsk/Disk-Coding/qlib")
SOURCE_PARTIAL = (
    SOURCE_REPO / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    ".alpha158_development_design_v1.partial"
)
OUTPUT_ROOT = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    "alpha158_development_design_recovery_v2"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_design_recovery_implementation_freeze_20260825.json"
)
INTERRUPTION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_permission_transition_interruption_20260825.json"
)
INTERRUPTION_SHA256 = "7cec04784b90f747b2eed71364b4970f3df84ed346a54e7beaa6548699fd3b58"
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_design_recovery.py"
)
CORRECTED_BASE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign286_design.py"
)
CORRECTED_BASE_SHA256 = (
    "1e751f214a31131b49fe6a021d9b7e3429da41b07a7b92c4fa5511962b4631fb"
)
BASE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_design.py"
)
BASE_TEST_SHA256 = "f7ce23312e6fdbc56ac082df6c988743e2e274bce8d2c71eb6769a825060662d"
INITIAL_RUNNER_PATH = (
    SOURCE_REPO / "scripts/a_share_three_day_walkforward_campaign286_design.py"
)
INITIAL_RUNNER_SHA256 = (
    "b73dd8bad81ff25572684c4a39de4a57853725a228c745f9164ac60189831e6e"
)
INITIAL_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_design_implementation_freeze_20260825.json"
)
INITIAL_FREEZE_SHA256 = (
    "78db0f692edf5687b0aff9d251d5b623a5448f8af64942ef6dced964ba8776d9"
)
RECOVERY_FAILURES = (
    (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_286_recovery_missing_compiled_extension_failure_20260825.json",
        "6ab48c09301213d1fa8cde472ff880e1666a5b7dbc721bbdf90b2f87ba698e02",
    ),
    (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_286_recovery_legacy_import_chain_failure_20260825.json",
        "fc3c92284ee09151567a565bbf4fd98aaf95ed61d1769d9b6e5292122d70e72e",
    ),
)
SOURCE_PARTITIONS = {
    2019: {
        "sha256": "5860735e85cca233841168ffa4ec49257d122a91348ede4214be4130ccfd2d5a",
        "bytes": 403_920_338,
        "rows": 885_491,
    },
    2020: {
        "sha256": "a49c8dc6c564714a8a9755c20619ca7b88de39a51b992240600ca9369ed719cb",
        "bytes": 420_870_721,
        "rows": 918_981,
    },
}
RECOVERY_YEARS = (2021, 2022, 2023)


class Campaign286RecoveryError(RuntimeError):
    """Fail closed when interrupted design recovery drifts."""


def configure_external_data() -> None:
    """Point only immutable data bindings at the now-read-only source tree."""

    base.PROVIDER_URI = SOURCE_REPO / "data/qlib/cn_a_share"
    base.QUALITY_PATH = (
        SOURCE_REPO / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
    )
    base.QUALITY_MANIFEST_PATH = (
        SOURCE_REPO / "data/metadata/quarterly_quality_manifest.json"
    )
    base.PRICE_BASIS_PATH = base.PROVIDER_URI / "price_basis.json"
    base.CALENDAR_PATH = base.PROVIDER_URI / "calendars/day.txt"
    base.UNIVERSE_PATH = base.PROVIDER_URI / "instruments/buyable_main_chinext.txt"


def source_partition(year: int) -> Path:
    if year not in SOURCE_PARTITIONS:
        raise Campaign286RecoveryError(f"unfrozen source-partition year: {year}")
    path = SOURCE_PARTIAL / "partitions" / f"{year}.parquet"
    receipt = SOURCE_PARTITIONS[year]
    if not (
        path.is_file()
        and path.stat().st_size == receipt["bytes"]
        and base.file_sha256(path) == receipt["sha256"]
    ):
        raise Campaign286RecoveryError(f"source partial changed: {path}")
    return path


def validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign286RecoveryError("Campaign286 recovery freeze absent")
    record = base.load_json(RECOVERY_FREEZE_PATH)
    runner = record.get("recovery_runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_design_recovery_implementation_freeze"
        and record.get("status")
        == "frozen_after_interruption_before_recovery_read_of_2021_2023"
        and (record.get("protocol") or {}).get("sha256") == base.PROTOCOL_SHA256
        and (record.get("interruption") or {}).get("sha256") == INTERRUPTION_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == base.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == base.file_sha256(TEST_PATH)
        and boundary.get("historical_label_or_forward_return_values_read") is False
        and boundary.get("threshold_or_model_change_after_feature_read") is False
        and boundary.get("lockbox_2024_2025_feature_or_return_values_read") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign286RecoveryError("Campaign286 recovery freeze changed")
    base.require_file(INTERRUPTION_PATH, INTERRUPTION_SHA256, "interruption record")
    base.require_file(
        CORRECTED_BASE_PATH, CORRECTED_BASE_SHA256, "corrected base runner"
    )
    base.require_file(BASE_TEST_PATH, BASE_TEST_SHA256, "corrected base tests")
    base.require_file(
        INITIAL_RUNNER_PATH, INITIAL_RUNNER_SHA256, "initial frozen runner"
    )
    base.require_file(
        INITIAL_FREEZE_PATH, INITIAL_FREEZE_SHA256, "initial design freeze"
    )
    for path, expected in RECOVERY_FAILURES:
        base.require_file(path, expected, "recovery infrastructure failure")
    for year in SOURCE_PARTITIONS:
        source_partition(year)
    return record


def daily_counts(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=[
            "stock_day_key",
            "quality_listing_eligible",
            "model_support_eligible",
        ],
    )
    days = frame["stock_day_key"].to_numpy(dtype=np.int64) // 4_000_000
    daily = pd.DataFrame(
        {
            "session": pd.to_datetime(days, unit="D", origin="unix"),
            "quality_listing_names": frame["quality_listing_eligible"].to_numpy(
                dtype=np.int64
            ),
            "eligible_names": frame["model_support_eligible"].to_numpy(dtype=np.int64),
        }
    )
    return (
        daily.groupby("session", sort=True, observed=True)[
            ["quality_listing_names", "eligible_names"]
        ]
        .sum()
        .reset_index()
    )


def partition_receipt(year: int, path: Path) -> dict[str, Any]:
    columns = [
        "stock_day_key",
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    ]
    frame = pd.read_parquet(path, columns=columns)
    support = frame["feature_support_eligible"].to_numpy(dtype=bool)
    quality = frame["quality_listing_eligible"].to_numpy(dtype=bool)
    eligible = frame["model_support_eligible"].to_numpy(dtype=bool)
    if not (
        not frame["stock_day_key"].duplicated().any()
        and np.array_equal(eligible, quality & support)
    ):
        raise Campaign286RecoveryError(f"partition eligibility changed: {year}")
    finite = frame["finite_feature_count"].to_numpy(dtype=np.uint8)
    return {
        "year": year,
        "path": f"partitions/{year}.parquet",
        "rows": len(frame),
        "quality_listing_rows": int(quality.sum()),
        "feature_support_rows": int(support.sum()),
        "model_support_eligible_rows": int(eligible.sum()),
        "finite_feature_count_minimum": int(finite.min()),
        "finite_feature_count_maximum": int(finite.max()),
        "sha256": base.file_sha256(path),
    }


def _copy_frozen_partition(year: int, output: Path) -> dict[str, Any]:
    source = source_partition(year)
    target = output / "partitions" / f"{year}.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.copying"
    if temporary.exists():
        raise Campaign286RecoveryError(f"preserve incomplete copy: {temporary}")
    shutil.copyfile(source, temporary)
    os.replace(temporary, target)
    if base.file_sha256(target) != SOURCE_PARTITIONS[year]["sha256"]:
        raise Campaign286RecoveryError(f"copied partition changed: {year}")
    return partition_receipt(year, target)


def _build_year(
    year: int,
    *,
    output: Path,
    instruments: list[str],
    listing_spans: dict[str, list[tuple[Any, Any]]],
    provider_calendar: pd.DatetimeIndex,
    fundamentals: pd.DataFrame,
    expressions: list[str],
    names: list[str],
    batch_size: int,
) -> dict[str, Any]:
    features = base._load_year_features(
        year,
        instruments=instruments,
        expressions=expressions,
        names=names,
        batch_size=batch_size,
    )
    identity = research.attach_listing_age_sessions(
        features[["instrument", "datetime"]], listing_spans, provider_calendar
    )
    eligibility = research.attach_quality_asof(
        identity,
        fundamentals,
        max_age_days=base.QUALITY_MAX_AGE_DAYS,
        availability_calendar=provider_calendar,
    )
    quality = eligibility["quality_eligible"].fillna(False).to_numpy(dtype=bool)
    matrix = features[names].to_numpy(dtype=np.float32, copy=False)
    finite_count, feature_support = base.support_state(matrix)
    model_support = quality & feature_support
    keys = base.compact_stock_day_keys(features["datetime"], features["instrument"])
    frame = features[names].copy()
    frame.insert(0, "stock_day_key", keys)
    frame["finite_feature_count"] = finite_count
    frame["feature_support_eligible"] = feature_support
    frame["quality_listing_eligible"] = quality
    frame["model_support_eligible"] = model_support
    frame = frame.sort_values("stock_day_key", kind="stable").reset_index(drop=True)
    path = output / "partitions" / f"{year}.parquet"
    base.atomic_parquet(frame, path)
    return partition_receipt(year, path)


def build_recovery(*, batch_size: int = 128, output_root: Path = OUTPUT_ROOT) -> Path:
    payload = plan(output_root=output_root)
    if payload["ready"] is not True:
        raise Campaign286RecoveryError("Campaign286 recovery output is not empty")
    if batch_size < 1:
        raise Campaign286RecoveryError("batch size must be positive")
    configure_external_data()
    base.validate_protocol()
    validate_recovery_freeze()

    import qlib
    from qlib.data import D

    research.require_research_price_basis(base.PROVIDER_URI)
    qlib.init(provider_uri=str(base.PROVIDER_URI), region="cn", kernels=1)
    universe = D.instruments(market="buyable_main_chinext")
    listing_spans = D.list_instruments(universe, as_list=False)
    provider_calendar = pd.DatetimeIndex(D.calendar(freq="day")).normalize()
    instruments = D.list_instruments(
        universe, start_time="2019-01-01", end_time="2023-12-31", as_list=True
    )
    fundamentals = research.load_fundamentals(base.QUALITY_PATH)
    expressions, names = base.feature_config()

    output_root = output_root.expanduser().resolve()
    partial = output_root.parent / f".{output_root.name}.partial"
    partial.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    try:
        for year in sorted(SOURCE_PARTITIONS):
            print(f"Campaign286 recovery: reusing frozen {year} partition", flush=True)
            records.append(_copy_frozen_partition(year, partial))
        for year in RECOVERY_YEARS:
            print(f"Campaign286 recovery: building {year} partition", flush=True)
            records.append(
                _build_year(
                    year,
                    output=partial,
                    instruments=instruments,
                    listing_spans=listing_spans,
                    provider_calendar=provider_calendar,
                    fundamentals=fundamentals,
                    expressions=expressions,
                    names=names,
                    batch_size=batch_size,
                )
            )
        daily = pd.concat(
            [daily_counts(partial / record["path"]) for record in records],
            ignore_index=True,
        )
        coverage = base.coverage_summary(daily)
        audit = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign286_alpha158_structural_audit",
            "status": (
                "passed_ready_for_frozen_model_implementation"
                if coverage[
                    "gate_passed_before_historical_label_or_forward_return_read"
                ]
                else "failed_terminal_before_historical_label_or_forward_return_read"
            ),
            "created_at": datetime.now(UTC).isoformat(),
            "coverage": coverage,
            "recovery_revision": 2,
            "reused_source_partition_years": sorted(SOURCE_PARTITIONS),
            "alpha158_feature_values_read": True,
            "historical_label_or_forward_return_values_read": False,
            "model_fitting_performed": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_ledgers_changed": False,
        }
        base.atomic_json(partial / "structural_audit.json", audit)
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
            "protocol": {
                "path": str(base.PROTOCOL_PATH),
                "sha256": base.PROTOCOL_SHA256,
            },
            "feature_count": base.FEATURE_COUNT,
            "feature_names": names,
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
                "sha256": base.file_sha256(partial / "structural_audit.json"),
                "gate_passed": coverage[
                    "gate_passed_before_historical_label_or_forward_return_read"
                ],
            },
            "recovery": {
                "revision": 2,
                "interruption_record": {
                    "path": str(INTERRUPTION_PATH),
                    "sha256": INTERRUPTION_SHA256,
                },
                "reused_source_partition_years": sorted(SOURCE_PARTITIONS),
                "recomputed_years": list(RECOVERY_YEARS),
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
        base.atomic_json(partial / "snapshot_manifest.json", manifest)
        os.replace(partial, output_root)
        return output_root / "snapshot_manifest.json"
    except BaseException as error:
        base.atomic_json(
            partial / "recovery_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign286_design_recovery_failure",
                "status": "failed_partial_preserved",
                "created_at": datetime.now(UTC).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
                "historical_label_or_forward_return_values_read": False,
                "lockbox_2024_2025_feature_or_return_values_read": False,
                "provider_request_issued": False,
                "candidate49_ledgers_changed": False,
            },
        )
        raise


def verify(manifest_path: Path) -> dict[str, Any]:
    configure_external_data()
    validate_recovery_freeze()
    manifest = base.load_json(manifest_path)
    _, names = base.feature_config()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign286_alpha158_development_design"
        and manifest.get("status") == "immutable_design_ready_for_model_implementation"
        and manifest.get("feature_names") == names
        and manifest.get("feature_count") == base.FEATURE_COUNT
        and manifest.get("feature_library_sha256") == base.FEATURE_LIBRARY_SHA256
        and manifest.get("minimum_finite_features") == base.MINIMUM_FINITE_FEATURES
        and manifest.get("development_years") == list(base.DEVELOPMENT_YEARS)
        and manifest.get("partitions") == len(manifest.get("files") or []) == 5
        and manifest.get("historical_label_or_forward_return_values_read") is False
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
    ):
        raise Campaign286RecoveryError("Campaign286 recovered manifest changed")
    digest_rows: list[list[Any]] = []
    for record in manifest["files"]:
        path = (manifest_path.parent / str(record["path"])).resolve()
        base.require_file(path, str(record["sha256"]), "recovered partition")
        frame = pd.read_parquet(
            path,
            columns=[
                "stock_day_key",
                *names,
                "finite_feature_count",
                "feature_support_eligible",
                "quality_listing_eligible",
                "model_support_eligible",
            ],
        )
        finite, support = base.support_state(
            frame[names].to_numpy(dtype=np.float32, copy=False)
        )
        quality = frame["quality_listing_eligible"].to_numpy(dtype=bool)
        eligible = frame["model_support_eligible"].to_numpy(dtype=bool)
        if not (
            len(frame) == int(record["rows"])
            and not frame["stock_day_key"].duplicated().any()
            and np.array_equal(
                finite, frame["finite_feature_count"].to_numpy(dtype=np.uint8)
            )
            and np.array_equal(
                support, frame["feature_support_eligible"].to_numpy(dtype=bool)
            )
            and np.array_equal(eligible, quality & support)
            and int(eligible.sum()) == int(record["model_support_eligible_rows"])
        ):
            raise Campaign286RecoveryError("recovered partition semantics changed")
        digest_rows.append(
            [
                int(record["year"]),
                len(frame),
                int(eligible.sum()),
                str(record["sha256"]),
            ]
        )
    if base.value_sha256(digest_rows) != manifest.get("dataset_sha256"):
        raise Campaign286RecoveryError("recovered dataset digest changed")
    audit_binding = manifest.get("structural_audit") or {}
    audit_path = (manifest_path.parent / str(audit_binding.get("path"))).resolve()
    base.require_file(audit_path, str(audit_binding.get("sha256")), "structural audit")
    audit = base.load_json(audit_path)
    if not (
        audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and (audit.get("coverage") or {}).get(
            "gate_passed_before_historical_label_or_forward_return_read"
        )
        is True
        and audit.get("historical_label_or_forward_return_values_read") is False
    ):
        raise Campaign286RecoveryError("recovered structural audit changed")
    recovery = manifest.get("recovery") or {}
    if not (
        recovery.get("revision") == 2
        and recovery.get("reused_source_partition_years") == sorted(SOURCE_PARTITIONS)
        and recovery.get("recomputed_years") == list(RECOVERY_YEARS)
        and recovery.get("threshold_or_model_change") is False
    ):
        raise Campaign286RecoveryError("Campaign286 recovery receipt changed")
    return {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": base.file_sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": manifest["rows"],
        "model_support_eligible_rows": manifest["model_support_eligible_rows"],
        "feature_count": manifest["feature_count"],
        "recovery_revision": 2,
        "historical_label_or_forward_return_values_read": False,
    }


def plan(*, output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    configure_external_data()
    base.validate_protocol()
    validate_recovery_freeze()
    root = output_root.expanduser().resolve()
    partial = root.parent / f".{root.name}.partial"
    ready = not root.exists() and not partial.exists()
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_design_recovery_plan",
        "status": (
            "ready_to_reuse_2019_2020_and_build_2021_2023_without_labels"
            if ready
            else "not_ready_preserve_existing_recovery_output_or_partial"
        ),
        "ready": ready,
        "output_root": str(root),
        "reused_source_partition_years": sorted(SOURCE_PARTITIONS),
        "recomputed_years": list(RECOVERY_YEARS),
        "threshold_or_model_change": False,
        "historical_label_or_forward_return_values_read_by_plan": False,
        "lockbox_2024_2025_feature_or_return_values_read_by_plan": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    build = subcommands.add_parser("build")
    build.add_argument("--confirm-recovery", action="store_true")
    build.add_argument("--batch-size", type=int, default=128)
    verify_command = subcommands.add_parser("verify")
    verify_command.add_argument("--manifest", type=Path, required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan":
        payload = plan()
    elif args.command == "build":
        if not args.confirm_recovery:
            raise Campaign286RecoveryError("build requires --confirm-recovery")
        payload = verify(build_recovery(batch_size=args.batch_size))
    elif args.command == "verify":
        payload = verify(args.manifest)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
