#!/usr/bin/env python3
"""Publish and verify Campaign087's additive protocol-metadata repair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign087_features as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_publication_implementation_freeze_v5_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_v5_protocol_metadata_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "6c731c496b71136a003537e4d2b5abe38faa8badeaf3e408e749d1cb2369cf86"
)
ORIGINAL_MANIFEST_PATH = v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
ORIGINAL_MANIFEST_SHA256 = (
    "6abe71a2402dc7b34124c1cc2abee8c54730ce978e6057b7b02beb4a4bcce5bd"
)
REPAIRED_MANIFEST_PATH = (
    v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest_v5.json"
)
REPAIRED_KIND = (
    "a_share_three_day_walkforward_campaign087_feature_snapshot_v5_protocol_metadata_repair"
)
REQUIRED_PROTOCOL_SHA256 = v1.PROTOCOL_SHA256
INCORRECT_PROTOCOL_SHA256 = (
    "033cd34013770b5b19ccb8579100c7ab920946de22b3936bc34a0898f4d2acb3"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_features_v5.py"
)
EXPECTED_ELIGIBLE_ROWS = 1_328_449
EXPECTED_PARTITION_SHA256 = {
    2019: "0460241d06d59639815af256e6f3bea6204c96b718fbd78ebe8fbd91148bea24",
    2020: "adb6f1412a3be12d5db09f7a354dbd2840c1316285259813687ba2d745184cea",
    2021: "989ba95fea774f507b4640d915eb2a717be59932b499570659e7134b4acf4bd6",
    2022: "69284884355eb72241f747bd85de61f9e0118f58c89b04e9c7f207cda660a463",
    2023: "ac0a9a82cbc03510eb1e93d2a237bc90966f44d92b14e9b1bf5b78a2a8254a64",
    2024: "aa33a0e4535091617d94cee96afe1d475e2c8628c6dd271e99f822c85cec2590",
    2025: "8514072f05250a42bdaebaabe30383d9fc0df28b75a147993f9d4a975a08e5ed",
}


class Campaign087FeatureV5Error(RuntimeError):
    """Fail-closed Campaign087 v5 publication error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign087FeatureV5Error(f"Campaign087 v5 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(ORIGINAL_MANIFEST_PATH, ORIGINAL_MANIFEST_SHA256, "original manifest")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087FeatureV5Error("Campaign087 v5 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_publication_implementation_freeze_v5"
        and record.get("status")
        == "additive_protocol_metadata_publication_frozen_before_v5_manifest_or_coverage"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("original_manifest") or {}).get("sha256")
        == ORIGINAL_MANIFEST_SHA256
        and (record.get("v5_publisher_verifier") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v5_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("repaired_manifest_published_before_freeze") is False
        and record.get("coverage_or_capacity_metrics_computed_before_freeze")
        is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign087FeatureV5Error("Campaign087 v5 freeze changed")
    return record


def _repaired_manifest(original: dict[str, Any]) -> dict[str, Any]:
    if not (
        original.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_snapshot"
        and (original.get("protocol") or {}).get("path")
        == str(v1.DEFAULT_PROTOCOL.resolve())
        and (original.get("protocol") or {}).get("sha256")
        == INCORRECT_PROTOCOL_SHA256
        and original.get("dataset_sha256")
        == "acc712042d582fbcbb87d23e7e7e47e71c6cbeb9b8a33678c75bb0ea58070777"
    ):
        raise Campaign087FeatureV5Error("Campaign087 original manifest failure changed")
    repaired = copy.deepcopy(original)
    repaired["kind"] = REPAIRED_KIND
    repaired["protocol"]["sha256"] = REQUIRED_PROTOCOL_SHA256
    repaired["publication_metadata_repair"] = {
        "scope": "additive protocol sha256 correction only; partitions reused unchanged",
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "original_manifest_path": str(ORIGINAL_MANIFEST_PATH.resolve()),
        "original_manifest_sha256": ORIGINAL_MANIFEST_SHA256,
        "incorrect_protocol_sha256": INCORRECT_PROTOCOL_SHA256,
        "corrected_protocol_sha256": REQUIRED_PROTOCOL_SHA256,
        "partition_bytes_rewritten": False,
        "candidate_values_recomputed": False,
        "formula_or_gate_changed": False,
    }
    repaired["dataset_sha256"] = v1._json_digest(v1._dataset_material(repaired))
    return repaired


def publish_repaired_manifest(*, confirm_publish: bool = False) -> Path:
    if not confirm_publish:
        raise Campaign087FeatureV5Error("Campaign087 v5 publish requires --confirm-publish")
    _load_implementation_freeze()
    if REPAIRED_MANIFEST_PATH.exists():
        raise Campaign087FeatureV5Error("Campaign087 v5 repaired manifest already exists")
    original = json.loads(ORIGINAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    repaired = _repaired_manifest(original)
    v1.c85._atomic_json(repaired, REPAIRED_MANIFEST_PATH)
    if _sha256(ORIGINAL_MANIFEST_PATH) != ORIGINAL_MANIFEST_SHA256:
        raise Campaign087FeatureV5Error("Campaign087 original manifest was rewritten")
    return REPAIRED_MANIFEST_PATH


def verify_snapshot_files(
    manifest_path: Path = REPAIRED_MANIFEST_PATH,
) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    if path != REPAIRED_MANIFEST_PATH.resolve() or not path.is_file():
        raise Campaign087FeatureV5Error("Campaign087 v5 repaired manifest path changed")
    original = json.loads(ORIGINAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    repaired = json.loads(path.read_text(encoding="utf-8"))
    expected = _repaired_manifest(original)
    if repaired != expected:
        raise Campaign087FeatureV5Error("Campaign087 v5 metadata delta changed")
    if not (
        repaired.get("kind") == REPAIRED_KIND
        and (repaired.get("protocol") or {}).get("sha256")
        == REQUIRED_PROTOCOL_SHA256
        and repaired.get("dataset_sha256")
        == v1._json_digest(v1._dataset_material(repaired))
        and repaired.get("rows") == v1.EXPECTED_ROWS
        and repaired.get("partitions") == v1.EXPECTED_PARTITIONS
        and repaired.get("calendar_sessions") == v1.EXPECTED_SESSIONS
        and (repaired.get("factor_eligible_rows") or {}).get(v1.FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and repaired.get("comparison_values_read") is False
        and repaired.get("historical_daily_price_fields_read") == []
        and repaired.get("historical_forward_returns_read") is False
        and repaired.get("provider_request_issued") is False
    ):
        raise Campaign087FeatureV5Error("Campaign087 v5 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    observed_years: list[int] = []
    for record in repaired.get("files") or []:
        year = int(record["year"])
        observed_years.append(year)
        partition = path.parent / str(record["path"])
        if not (
            _sha256(partition) == record.get("sha256")
            and record.get("sha256") == EXPECTED_PARTITION_SHA256.get(year)
        ):
            raise Campaign087FeatureV5Error("Campaign087 v5 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(v1.OUTPUT_COLUMNS))
        if v1.c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign087FeatureV5Error("Campaign087 v5 partition frame changed")
        values = frame[v1.FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{v1.FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and v1.cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign087FeatureV5Error("Campaign087 v5 candidate values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        observed_years == list(range(2019, 2026))
        and rows == v1.EXPECTED_ROWS
        and eligible_count == EXPECTED_ELIGIBLE_ROWS
        and len(np.unique(keys)) == v1.EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (repaired.get("eligible_universe") or {}).get("keys_sha256")
        and _sha256(ORIGINAL_MANIFEST_PATH) == ORIGINAL_MANIFEST_SHA256
    ):
        raise Campaign087FeatureV5Error("Campaign087 v5 aggregate identity changed")
    return {
        "status": "verified",
        "manifest_path": str(path),
        "manifest_sha256": _sha256(path),
        "dataset_sha256": repaired["dataset_sha256"],
        "partitions": len(observed_years),
        "rows": rows,
        "eligible_rows": eligible_count,
        "original_manifest_unchanged": True,
        "partition_bytes_rewritten": False,
        "candidate_values_recomputed": False,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status() -> dict[str, Any]:
    return {
        "status": "repaired_manifest_present"
        if REPAIRED_MANIFEST_PATH.is_file()
        else "repaired_manifest_absent_prepublish",
        "original_manifest_sha256_matches": ORIGINAL_MANIFEST_PATH.is_file()
        and _sha256(ORIGINAL_MANIFEST_PATH) == ORIGINAL_MANIFEST_SHA256,
        "repaired_manifest_path": str(REPAIRED_MANIFEST_PATH),
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    publish = sub.add_parser("publish")
    publish.add_argument("--confirm-publish", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, default=REPAIRED_MANIFEST_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(), sort_keys=True))
        return 0
    if args.command == "publish":
        print(publish_repaired_manifest(confirm_publish=args.confirm_publish))
        return 0
    print(json.dumps(verify_snapshot_files(args.manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
