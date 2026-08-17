#!/usr/bin/env python3
"""Freshly build and verify the additive Campaign068 signed-range repair."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign068_features as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_snapshot_repair_protocol_v2_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = "fe90acaa8c89ec6c750441ed3c4704249d6415d5e9102c40f82799792d421f7f"
V1_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_snapshot_verification_failure_20260806.json"
)
V1_FAILURE_SHA256 = "89bebd40288eca5f991fffb9e5a9321181c7191fa7a882d0c0b4b380c57af67e"
V1_RUNNER_SHA256 = "1ebfbfd5709132d49f5d34276176df26a5ca53cfa492700a69c7ba64422d0b22"
V1_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_implementation_freeze_20260806.json"
)
V1_FREEZE_SHA256 = "fbc5991e61ae427e9a752c2525a702a54d930eef2cd55c434c78d4ae33c841cf"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_implementation_freeze_v2_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign068_features_v2.py"
)
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign068_feature_library_v2"
)


class Campaign068FeatureV2Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign068_feature_library"
        / OUTPUT_RUN_ID
    )


def load_repair_protocol() -> dict[str, Any]:
    for path, expected, label in (
        (REPAIR_PROTOCOL_PATH, REPAIR_PROTOCOL_SHA256, "v2 repair protocol"),
        (V1_FAILURE_PATH, V1_FAILURE_SHA256, "v1 failure record"),
        (Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 feature runner"),
        (V1_FREEZE_PATH, V1_FREEZE_SHA256, "v1 implementation freeze"),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign068FeatureV2Error(f"Campaign068 {label} changed")
    spec = json.loads(REPAIR_PROTOCOL_PATH.read_text(encoding="utf-8"))
    output = spec.get("v2_output") or {}
    repair = spec.get("sole_repair") or {}
    unchanged = spec.get("unchanged_semantics") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 2
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign068_feature_snapshot_repair_protocol"
        and spec.get("status")
        == "frozen_before_v2_source_rows_candidate_values_or_snapshot_files"
        and (spec.get("recorded_v1_failure") or {}).get("sha256")
        == V1_FAILURE_SHA256
        and (spec.get("recorded_v1_failure") or {}).get(
            "v1_snapshot_files_reusable_for_v2"
        )
        is False
        and output.get("root") == str(output_root(DEFAULT_DATA_ROOT))
        and output.get("fresh_source_read_and_fresh_partition_build_required")
        is True
        and repair.get("old_incorrect_eligible_value_range") == [0.0, 1.0]
        and repair.get("new_required_eligible_value_range") == [-1.0, 1.0]
        and repair.get("all_33015_partitions_must_pass") is True
        and unchanged.get("factor") == v1.FACTOR_NAME
        and unchanged.get("formula") == v1.FACTOR_FORMULA
        and unchanged.get("expected_rows") == v1.EXPECTED_ROWS
        and unchanged.get("expected_partitions") == v1.EXPECTED_PARTITIONS
        and boundary.get("v2_source_candidate_or_snapshot_values_read_before_this_freeze")
        is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign068FeatureV2Error("Campaign068 v2 repair protocol changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign068FeatureV2Error("Campaign068 v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign068_feature_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_v2_source_rows_candidate_values_or_snapshot_files"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("v2_output_existed_before_freeze") is False
        and record.get("v2_source_candidate_or_snapshot_values_read_before_freeze")
        is False
        and record.get("comparison_daily_price_or_forward_return_values_read_before_freeze")
        is False
    ):
        raise Campaign068FeatureV2Error(
            "Campaign068 v2 implementation freeze changed"
        )
    return record


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != v1.OUTPUT_COLUMNS:
        raise Campaign068FeatureV2Error("v2 partition columns changed")
    values = pd.to_numeric(frame[v1.FACTOR_NAME], errors="coerce")
    eligible = frame[f"{v1.FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign068FeatureV2Error("v2 signed value semantics changed")
    return len(frame), int(eligible.sum())


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign068FeatureV2Error("Campaign068 v2 data root changed")
    root = output_root(data_root)
    if root.exists():
        raise Campaign068FeatureV2Error("Campaign068 v2 output already exists")
    original_output_root = v1._runtime["output_root"]
    try:
        v1._runtime["output_root"] = output_root
        manifest = v1.build_snapshot(data_root=data_root, workers=workers)
    finally:
        v1._runtime["output_root"] = original_output_root
    if manifest != root / "snapshot_manifest.json":
        raise Campaign068FeatureV2Error("Campaign068 v2 publication root changed")
    return manifest


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    load_repair_protocol()
    _load_implementation_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    expected_manifest = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected_manifest:
        raise Campaign068FeatureV2Error("Campaign068 v2 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    v1._runtime["_validate_manifest"](manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise Campaign068FeatureV2Error("v2 partition escaped output root") from exc
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign068FeatureV2Error(f"v2 partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or v1._runtime["_frame_sha256"](frame) != item["output_frame_sha256"]
        ):
            raise Campaign068FeatureV2Error(f"v2 partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    if not (
        v1._runtime["_json_digest"](digest_rows) == manifest["dataset_sha256"]
        and sum(value[0] for value in totals) == v1.EXPECTED_ROWS
        and len(totals) == v1.EXPECTED_PARTITIONS
        and sum(value[1] for value in totals)
        == (manifest.get("factor_eligible_rows") or {}).get(v1.FACTOR_NAME)
    ):
        raise Campaign068FeatureV2Error("Campaign068 v2 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
        "dataset_sha256": manifest["dataset_sha256"],
        "eligible_value_range": [-1.0, 1.0],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_repair_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build",
        "snapshot_manifest": str(path),
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v1_failed_snapshot_accepted": False,
        "candidate_or_comparison_values_read_by_status": False,
        "daily_price_fields_read_by_status": [],
        "historical_forward_return_fields_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {
            "snapshot_manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
