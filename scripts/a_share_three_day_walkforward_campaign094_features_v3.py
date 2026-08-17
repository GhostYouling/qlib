#!/usr/bin/env python3
"""Activate and verify Campaign094's metadata-only v3 snapshot repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign094_features as v1
from scripts import a_share_three_day_walkforward_campaign094_features_v2 as v2

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
PREACTIVATION_MANIFEST = v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
PREACTIVATION_MANIFEST_SHA256 = (
    "c9756aece82523c2fbb4fdbf941aa8e699f2d6024066fa06f96203701b347c06"
)
PREACTIVATION_DATASET_SHA256 = (
    "7f3396394b691d22c0359b67e5e43b95f387c0510a7bf062a66eab66a4a509ad"
)
V2_RUNNER_SHA256 = "2925f324198625608794479a8b081658ab4e837f1e3ee44c7292643dd7fbfe38"
V2_FREEZE = v2.DEFAULT_IMPLEMENTATION_FREEZE
V2_FREEZE_SHA256 = "0e24abb954edee47c1653af038d7c2158bb0fd9a0771343a621d530110c87ded"
V2_FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_v2_postpublication_activation_failure_20260807.json"
)
V2_FAILURE_SHA256 = "6420faf861cc4cf515519e3942aa12ed7b84e34e59c149ad086babc80bfde785"
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_v3_metadata_activation_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "75074f18e4c361c3a74b5824239d3935df2656408097e841873bd477b4351885"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_094_feature_implementation_freeze_v3_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign094_features_v3.py"
)


class Campaign094FeatureV3Error(RuntimeError):
    """Fail-closed Campaign094 metadata-activation error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign094FeatureV3Error(f"Campaign094 v3 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v2.__file__).resolve(), V2_RUNNER_SHA256, "v2 runner")
    _require(V2_FREEZE, V2_FREEZE_SHA256, "v2 freeze")
    _require(V2_FAILURE, V2_FAILURE_SHA256, "v2 failure")
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign094FeatureV3Error("Campaign094 v3 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign094_feature_implementation_freeze_v3"
        and record.get("status")
        == "metadata_activation_repair_frozen_before_campaign094_manifest_mutation"
        and (record.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (record.get("v2_implementation_freeze") or {}).get("sha256")
        == V2_FREEZE_SHA256
        and (record.get("v2_activation_failure") or {}).get("sha256")
        == V2_FAILURE_SHA256
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v3_feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v3_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("preactivation_manifest_sha256") == PREACTIVATION_MANIFEST_SHA256
        and record.get("partition_files_may_be_rewritten") is False
        and record.get("comparison_values_read_before_v3_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v3_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v3_freeze") is False
        and record.get("candidate49_ledgers_changed_before_v3_freeze") is False
    ):
        raise Campaign094FeatureV3Error("Campaign094 v3 freeze changed")
    return record


def _normalized_quality(quality: dict[str, Any]) -> dict[str, int]:
    result = {str(key): int(value) for key, value in quality.items()}
    if not (
        "zero_destination_range_pairs" in result
        and "zero_range_bars" not in result
        and "endpoint_canonicalized_sessions" not in result
    ):
        raise Campaign094FeatureV3Error("Campaign094 preactivation quality changed")
    result["zero_range_bars"] = result.pop("zero_destination_range_pairs")
    return result


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    repair = manifest["runtime_repair"]
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "v1_implementation_freeze_sha256": repair["v1_implementation_freeze_sha256"],
        "v2_implementation_freeze_sha256": repair["v2_implementation_freeze_sha256"],
        "v3_implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "v3_repair_protocol_sha256": repair["v3_repair_protocol_sha256"],
        "preactivation_manifest_sha256": repair["preactivation_manifest_sha256"],
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


def _transform_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign094_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and manifest.get("dataset_sha256") == PREACTIVATION_DATASET_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == v2.V1_FREEZE_SHA256
        and (manifest.get("feature_runner") or {}).get("sha256") == v2.V1_RUNNER_SHA256
    ):
        raise Campaign094FeatureV3Error("Campaign094 preactivation manifest changed")
    result = dict(manifest)
    result["quality"] = _normalized_quality(dict(manifest.get("quality") or {}))
    result["kind"] = "a_share_three_day_walkforward_campaign094_feature_snapshot_v3"
    result["implementation_freeze"] = {
        "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
        "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
    }
    result["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    result["runtime_repair"] = {
        "scope": "metadata-only quality-field activation",
        "v1_implementation_freeze_sha256": v2.V1_FREEZE_SHA256,
        "v1_feature_runner_sha256": v2.V1_RUNNER_SHA256,
        "v2_implementation_freeze_sha256": V2_FREEZE_SHA256,
        "v2_feature_runner_sha256": V2_RUNNER_SHA256,
        "v2_activation_failure_sha256": V2_FAILURE_SHA256,
        "v3_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "preactivation_manifest_sha256": PREACTIVATION_MANIFEST_SHA256,
        "preactivation_dataset_sha256": PREACTIVATION_DATASET_SHA256,
        "quality_field_renamed_from": "zero_destination_range_pairs",
        "quality_field_renamed_to": "zero_range_bars",
        "partition_files_or_factor_values_changed": False,
    }
    result["implementation_freeze_status"] = (
        "metadata_activation_repair_frozen_before_campaign094_manifest_mutation"
    )
    result["dataset_sha256"] = v2._G["_json_digest"](_dataset_material(result))
    return result


def activate_manifest(*, confirm_activate: bool = False) -> Path:
    if not confirm_activate:
        raise Campaign094FeatureV3Error(
            "Campaign094 v3 activation requires --confirm-activate"
        )
    _load_implementation_freeze()
    _require(
        PREACTIVATION_MANIFEST,
        PREACTIVATION_MANIFEST_SHA256,
        "preactivation manifest",
    )
    v1.verify_snapshot_files(PREACTIVATION_MANIFEST)
    manifest = json.loads(PREACTIVATION_MANIFEST.read_text(encoding="utf-8"))
    activated = _transform_manifest(manifest)
    v2.STORAGE._atomic_json(activated, PREACTIVATION_MANIFEST)
    return PREACTIVATION_MANIFEST


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    if path != PREACTIVATION_MANIFEST.resolve() or not path.is_file():
        raise Campaign094FeatureV3Error("Campaign094 v3 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    quality = manifest.get("quality") or {}
    repair = manifest.get("runtime_repair") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign094_feature_snapshot_v3"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and repair.get("v3_repair_protocol_sha256") == REPAIR_PROTOCOL_SHA256
        and repair.get("preactivation_manifest_sha256") == PREACTIVATION_MANIFEST_SHA256
        and repair.get("partition_files_or_factor_values_changed") is False
        and manifest.get("factor_names") == [v1.FACTOR_NAME]
        and manifest.get("factor_directions") == {v1.FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {v1.FACTOR_NAME: [0.0, 0.25]}
        and (manifest.get("source") or {}).get("raw_fields_read")
        == list(v1.RAW_COLUMNS)
        and manifest.get("rows") == v2.EXPECTED_ROWS
        and manifest.get("partitions") == v2.EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == v2.EXPECTED_SESSIONS
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
        == v2._G["_json_digest"](_dataset_material(manifest))
    ):
        raise Campaign094FeatureV3Error("Campaign094 v3 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign094FeatureV3Error("Campaign094 v3 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(v2.OUTPUT_COLUMNS))
        if v2.STORAGE._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign094FeatureV3Error("Campaign094 v3 partition frame changed")
        values = frame[v1.FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{v1.FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] > 0.0) & (values[finite] <= 0.25)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and v2.CACHE.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign094FeatureV3Error("Campaign094 v3 partition values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == v2.EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(v1.FACTOR_NAME)
        and len(np.unique(keys)) == v2.EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign094FeatureV3Error("Campaign094 v3 aggregate identity changed")
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


def status() -> dict[str, Any]:
    if not PREACTIVATION_MANIFEST.is_file():
        state = "snapshot_absent"
    elif _sha256(PREACTIVATION_MANIFEST) == PREACTIVATION_MANIFEST_SHA256:
        state = "verified_v1_snapshot_awaiting_v3_activation"
    else:
        manifest = json.loads(PREACTIVATION_MANIFEST.read_text(encoding="utf-8"))
        state = (
            "v3_snapshot_present"
            if manifest.get("kind")
            == "a_share_three_day_walkforward_campaign094_feature_snapshot_v3"
            else "unexpected_manifest_state"
        )
    return {
        "status": state,
        "manifest_path": str(PREACTIVATION_MANIFEST),
        "partition_or_factor_values_mutated_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    activate = commands.add_parser("activate")
    activate.add_argument("--confirm-activate", action="store_true")
    commands.add_parser("status")
    verify = commands.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(), sort_keys=True))
        return 0
    if args.command == "activate":
        print(activate_manifest(confirm_activate=args.confirm_activate))
        return 0
    manifest = args.manifest or PREACTIVATION_MANIFEST
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
