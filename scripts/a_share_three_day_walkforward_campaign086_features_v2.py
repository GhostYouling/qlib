#!/usr/bin/env python3
"""Run Campaign086's additive empty-identity repair without changing v1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_walkforward_campaign085_features as c85
from scripts import a_share_three_day_walkforward_campaign086_features as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_feature_implementation_freeze_v2_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_empty_identity_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "c90796e994bc81325e0c06c66cc68c1245e7f52376b362d9b2d2154295cca277"
)
V1_FREEZE = v1.DEFAULT_IMPLEMENTATION_FREEZE
V1_FREEZE_SHA256 = (
    "9ea63a23935619537137376e464297bbc302bed26feff0ae719ad00656c47ebd"
)
V1_RUNNER_SHA256 = (
    "ed59f42461a89cc58738c922e87ac821b548dabd8ac1ce0f99eca68cef3b9f8a"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign086_features_v2.py"
)


class Campaign086FeatureV2Error(RuntimeError):
    """Fail-closed Campaign086 v2 repair error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign086FeatureV2Error(f"Campaign086 v2 {label} changed: {path}")


def empty_attached_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            v1.FACTOR_NAME: pd.Series(dtype="float64"),
        }
    ).loc[:, (*v1.IDENTITY_COLUMNS, v1.FACTOR_NAME)]


def attach_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != v1.IDENTITY_COLUMNS:
        raise Campaign086FeatureV2Error(
            f"Campaign086 v2 identity projection changed for {symbol}"
        )
    if identity.empty:
        return empty_attached_frame()
    return v1.attach_values(identity, values, symbol=symbol)


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(V1_FREEZE, V1_FREEZE_SHA256, "v1 implementation freeze")
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 feature runner")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign086FeatureV2Error("Campaign086 v2 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign086_feature_implementation_freeze_v2"
        and record.get("status")
        == "empty_identity_repair_frozen_before_campaign086_feature_build_retry"
        and (record.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_FREEZE_SHA256
        and (record.get("v2_feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_snapshot_published_before_v2_freeze") is False
        and record.get("comparison_values_read_before_v2_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v2_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v2_freeze") is False
    ):
        raise Campaign086FeatureV2Error("Campaign086 v2 freeze changed")
    return record


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "v1_implementation_freeze_sha256": manifest["runtime_repair"][
            "v1_implementation_freeze_sha256"
        ],
        "v2_implementation_freeze_sha256": manifest["implementation_freeze"][
            "sha256"
        ],
        "repair_protocol_sha256": manifest["runtime_repair"][
            "repair_protocol_sha256"
        ],
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
    freeze_sha = _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
    manifest["kind"] = "a_share_three_day_walkforward_campaign086_feature_snapshot_v2"
    manifest["implementation_freeze"] = {
        "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
        "sha256": freeze_sha,
    }
    manifest["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    manifest["runtime_repair"] = {
        "scope": "accepted empty joint-clean identity partitions only",
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v1_implementation_freeze_sha256": V1_FREEZE_SHA256,
        "v1_feature_runner_sha256": V1_RUNNER_SHA256,
        "formula_or_gate_changed": False,
    }
    manifest["implementation_freeze_status"] = (
        "empty_identity_repair_frozen_before_campaign086_feature_build_retry"
    )
    manifest["dataset_sha256"] = v1._json_digest(_dataset_material(manifest))
    c85._atomic_json(manifest, manifest_path)
    return manifest_path


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign086FeatureV2Error("Campaign086 v2 build requires --confirm-build")
    _load_implementation_freeze()
    if v1.output_root(data_root.expanduser().resolve()).exists():
        raise Campaign086FeatureV2Error("Campaign086 output already exists")
    original = v1.attach_values
    v1.attach_values = attach_values
    try:
        manifest_path = v1.build_snapshot(
            data_root=data_root,
            workers=workers,
            confirm_build=True,
        )
    finally:
        v1.attach_values = original
    return _activate_v2_manifest(manifest_path)


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign086FeatureV2Error("Campaign086 v2 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign086_feature_snapshot_v2"
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
        and manifest.get("rows") == v1.EXPECTED_ROWS
        and manifest.get("partitions") == v1.EXPECTED_PARTITIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256")
        == v1._json_digest(_dataset_material(manifest))
    ):
        raise Campaign086FeatureV2Error("Campaign086 v2 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign086FeatureV2Error("Campaign086 v2 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(v1.OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign086FeatureV2Error("Campaign086 v2 partition frame changed")
        values = frame[v1.FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{v1.FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign086FeatureV2Error("Campaign086 v2 values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == v1.EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(v1.FACTOR_NAME)
        and len(np.unique(keys)) == v1.EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign086FeatureV2Error("Campaign086 v2 aggregate identity changed")
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
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_v2_retry",
        "manifest_path": str(path),
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
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
