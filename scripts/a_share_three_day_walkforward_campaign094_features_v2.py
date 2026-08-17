#!/usr/bin/env python3
"""Retry Campaign094 with the frozen additive quality-key adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign094_features as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
V1_RUNNER_SHA256 = "d0e51bac3c27cf2d020a7f3df458273f7440554fd6d9e6b1927975492774e1f8"
V1_FREEZE = v1.DEFAULT_IMPLEMENTATION_FREEZE
V1_FREEZE_SHA256 = "d4b5bb63e412c091a4c32c45fcfcc4f431446d6f101e674a062425e6f534c743"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_build_quality_schema_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "2cb67be4ea48ccc1df029113a21329b1a0c0f93656bb6356fcf299649589fd79"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_build_quality_schema_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "98cce1cd8a1c9df986557381bbee3423d5d8c8ec10aa52e135311151afbdaab0"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_implementation_freeze_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign094_features_v2.py"
)

_G = v1.build_snapshot.__globals__
EXPECTED_ROWS = int(_G["EXPECTED_ROWS"])
EXPECTED_PARTITIONS = int(_G["EXPECTED_PARTITIONS"])
EXPECTED_SESSIONS = int(_G["EXPECTED_SESSIONS"])
OUTPUT_COLUMNS = tuple(_G["OUTPUT_COLUMNS"])
CACHE = _G["cache_v1"]
STORAGE = _G["c85"]


class Campaign094FeatureV2Error(RuntimeError):
    """Fail-closed Campaign094 v2 repair error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign094FeatureV2Error(f"Campaign094 v2 {label} changed: {path}")


def _quality_compatible_extract(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    values, quality = v1.extract_range_local_peak_clock_dispersion(raw, symbol=symbol)
    if "zero_range_bars" not in quality or "zero_destination_range_pairs" in quality:
        raise Campaign094FeatureV2Error("Campaign094 v2 quality schema changed")
    adapted = dict(quality)
    adapted["zero_destination_range_pairs"] = int(quality["zero_range_bars"])
    adapted["endpoint_canonicalized_sessions"] = 0
    return values, adapted


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 runner")
    _require(V1_FREEZE, V1_FREEZE_SHA256, "v1 freeze")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record")
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign094FeatureV2Error("Campaign094 v2 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign094_feature_implementation_freeze_v2"
        and record.get("status")
        == "quality_schema_repair_frozen_before_campaign094_snapshot_retry"
        and (record.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_FREEZE_SHA256
        and (record.get("failure_record") or {}).get("sha256") == FAILURE_RECORD_SHA256
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("comparison_values_read_before_v2_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v2_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v2_freeze") is False
        and record.get("candidate49_ledgers_changed_before_v2_freeze") is False
    ):
        raise Campaign094FeatureV2Error("Campaign094 v2 freeze changed")
    return record


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "v1_implementation_freeze_sha256": manifest["runtime_repair"][
            "v1_implementation_freeze_sha256"
        ],
        "v2_implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "repair_protocol_sha256": manifest["runtime_repair"]["repair_protocol_sha256"],
        "raw_manifest_sha256": manifest["source"]["raw_manifest_sha256"],
        "joint_clean_manifest_sha256": manifest["source"][
            "joint_clean_manifest_sha256"
        ],
        "eligible_keys_sha256": manifest["eligible_universe"]["keys_sha256"],
        "factor_name": v1.FACTOR_NAME,
        "factor_formula": v1.FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][v1.FACTOR_NAME],
        "files": manifest["files"],
    }


def _activate_v2_manifest(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    quality = dict(manifest.get("quality") or {})
    if not (
        "zero_destination_range_pairs" in quality
        and "endpoint_canonicalized_sessions" in quality
        and "zero_range_bars" not in quality
    ):
        raise Campaign094FeatureV2Error("Campaign094 v1 manifest quality changed")
    quality["zero_range_bars"] = int(quality.pop("zero_destination_range_pairs"))
    if int(quality.pop("endpoint_canonicalized_sessions")) != 0:
        raise Campaign094FeatureV2Error(
            "Campaign094 inherited endpoint counter changed"
        )
    manifest["quality"] = quality
    manifest["kind"] = "a_share_three_day_walkforward_campaign094_feature_snapshot_v2"
    manifest["implementation_freeze"] = {
        "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
        "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
    }
    manifest["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    manifest["runtime_repair"] = {
        "scope": "quality-counter name compatibility only",
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v1_implementation_freeze_sha256": V1_FREEZE_SHA256,
        "v1_feature_runner_sha256": V1_RUNNER_SHA256,
        "input_quality_field": "zero_range_bars",
        "temporary_inherited_alias": "zero_destination_range_pairs",
        "published_quality_field": "zero_range_bars",
        "formula_direction_source_projection_eligibility_or_factor_values_changed": False,
    }
    manifest["implementation_freeze_status"] = (
        "quality_schema_repair_frozen_before_campaign094_snapshot_retry"
    )
    manifest["dataset_sha256"] = _G["_json_digest"](_dataset_material(manifest))
    STORAGE._atomic_json(manifest, manifest_path)
    return manifest_path


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign094FeatureV2Error("Campaign094 v2 build requires --confirm-build")
    _load_implementation_freeze()
    root = v1.output_root(data_root.expanduser().resolve())
    if root.exists():
        raise Campaign094FeatureV2Error("Campaign094 output already exists")
    original = _G.get("extract_directional_amount_timing_spread")
    if original is not v1.extract_range_local_peak_clock_dispersion:
        raise Campaign094FeatureV2Error("Campaign094 v1 extractor binding changed")
    _G["extract_directional_amount_timing_spread"] = _quality_compatible_extract
    try:
        manifest_path = v1.build_snapshot(
            data_root=data_root,
            workers=workers,
            confirm_build=True,
        )
    finally:
        _G["extract_directional_amount_timing_spread"] = original
    return _activate_v2_manifest(manifest_path)


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign094FeatureV2Error("Campaign094 v2 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign094_feature_snapshot_v2"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (manifest.get("runtime_repair") or {}).get("repair_protocol_sha256")
        == REPAIR_PROTOCOL_SHA256
        and manifest.get("factor_names") == [v1.FACTOR_NAME]
        and manifest.get("factor_directions") == {v1.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {v1.FACTOR_NAME: [0.0, 0.25]}
        and (manifest.get("source") or {}).get("raw_fields_read")
        == list(v1.RAW_COLUMNS)
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and "zero_range_bars" in quality
        and "zero_destination_range_pairs" not in quality
        and "endpoint_canonicalized_sessions" not in quality
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("dataset_sha256")
        == _G["_json_digest"](_dataset_material(manifest))
    ):
        raise Campaign094FeatureV2Error("Campaign094 v2 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign094FeatureV2Error("Campaign094 v2 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if STORAGE._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign094FeatureV2Error("Campaign094 v2 partition frame changed")
        values = frame[v1.FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{v1.FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] > 0.0) & (values[finite] <= 0.25)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and CACHE.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign094FeatureV2Error("Campaign094 v2 partition values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(v1.FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign094FeatureV2Error("Campaign094 v2 aggregate identity changed")
    return {
        "status": "verified",
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": rows,
        "eligible_rows": eligible_count,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    v1.load_protocol()
    path = v1.output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": (
            "snapshot_present" if path.is_file() else "snapshot_absent_pre_v2_retry"
        ),
        "manifest_path": str(path),
        "source_or_candidate_values_read_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = commands.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = commands.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.data_root), sort_keys=True))
        return 0
    if args.command == "build":
        print(
            build_snapshot(
                data_root=args.data_root,
                workers=args.workers,
                confirm_build=args.confirm_build,
            )
        )
        return 0
    manifest = args.manifest or (
        v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
