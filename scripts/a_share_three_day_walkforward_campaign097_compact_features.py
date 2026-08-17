#!/usr/bin/env python3
"""Publish Campaign097's admitted factor on the frozen compact stock-day grid."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pa_dataset
import pyarrow.parquet as pq

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit as audit_v1,
)
from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v4 as audit_v4,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = audit_v1.FACTOR_NAME
DEFAULT_DATA_ROOT = audit_v1.DEFAULT_DATA_ROOT
SOURCE_MANIFEST = audit_v1.SNAPSHOT_MANIFEST_PATH
SOURCE_MANIFEST_SHA256 = audit_v1.SNAPSHOT_MANIFEST_SHA256
SOURCE_DATASET_SHA256 = audit_v1.SNAPSHOT_DATASET_SHA256
ELIGIBILITY_MANIFEST = audit_v1.ELIGIBILITY_MANIFEST_PATH
ELIGIBILITY_MANIFEST_SHA256 = audit_v1.ELIGIBILITY_MANIFEST_SHA256
AUTHORITATIVE_NO_RETURN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_097/no_return/20260807T063355Z_campaign097_no_return_audit.json"
)
AUTHORITATIVE_NO_RETURN_AUDIT_SHA256 = (
    "e95544ba9928c416a00aeaea66c187a4620d3955a48c1418fb697379704bd35b"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_compact_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_compact_features.py"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign097_compact_feature_library_v1"
)
EXPECTED_SOURCE_ROWS = 7_724_498
EXPECTED_ROWS = 1_331_759
EXPECTED_ELIGIBLE_ROWS = 1_328_449
EXPECTED_PARTITIONS = 7
EXPECTED_SESSIONS = 1_632


class Campaign097CompactFeatureError(RuntimeError):
    """Fail-closed Campaign097 compact publication error."""


def _sha256(path: Path) -> str:
    return audit_v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097CompactFeatureError(f"Campaign097 {label} changed: {path}")


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign097_compact_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097CompactFeatureError("compact implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_compact_feature_implementation_freeze"
        and record.get("status")
        == "frozen_after_no_return_admission_before_compact_publication_or_development_return_read"
        and (record.get("compact_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("authoritative_no_return_audit") or {}).get("sha256")
        == AUTHORITATIVE_NO_RETURN_AUDIT_SHA256
        and record.get("expected_rows") == EXPECTED_ROWS
        and record.get("expected_eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign097CompactFeatureError("compact implementation freeze changed")
    return record


def _frame_sha256(keys: np.ndarray, values: np.ndarray) -> str:
    compact = np.asarray(keys, dtype="<i8")
    scores = np.asarray(values, dtype="<f8").copy()
    scores[np.isnan(scores)] = np.nan
    digest = hashlib.sha256()
    digest.update(compact.tobytes())
    digest.update(scores.tobytes())
    return digest.hexdigest()


def _load_all_candidate_arrays() -> tuple[np.ndarray, np.ndarray]:
    dataset = pa_dataset.dataset(
        str(SOURCE_MANIFEST.parent / "partitions"), format="parquet"
    )
    table = dataset.to_table(
        columns=["trade_date", "symbol", FACTOR_NAME], use_threads=True
    )
    if table.num_rows != EXPECTED_SOURCE_ROWS:
        raise Campaign097CompactFeatureError("source candidate row count changed")
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    keys = audit_v1.compact_stock_day_keys(frame["trade_date"], frame["symbol"])
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce").to_numpy(
        dtype=np.float64
    )
    if not (
        len(keys) == EXPECTED_SOURCE_ROWS
        and values.shape == keys.shape
        and len(np.unique(keys)) == len(keys)
    ):
        raise Campaign097CompactFeatureError("source candidate identities changed")
    return keys, values


def _write_partition(path: Path, keys: np.ndarray, values: np.ndarray) -> None:
    table = pa.Table.from_arrays(
        [
            pa.array(np.asarray(keys, dtype=np.int64), type=pa.int64()),
            pa.array(np.asarray(values, dtype=np.float64), type=pa.float64()),
        ],
        names=["stock_day_key", FACTOR_NAME],
    )
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=False,
        write_statistics=True,
        row_group_size=65_536,
        data_page_version="2.0",
    )


def build_snapshot(*, data_root: Path) -> Path:
    _load_implementation_freeze()
    _require(SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "source manifest")
    _require(
        ELIGIBILITY_MANIFEST,
        ELIGIBILITY_MANIFEST_SHA256,
        "eligibility manifest",
    )
    _require(
        AUTHORITATIVE_NO_RETURN_AUDIT,
        AUTHORITATIVE_NO_RETURN_AUDIT_SHA256,
        "authoritative no-return audit",
    )
    audit = json.loads(AUTHORITATIVE_NO_RETURN_AUDIT.read_text(encoding="utf-8"))
    if not (
        audit.get("admissible_factor_names") == [FACTOR_NAME]
        and audit.get("historical_forward_return_fields_read") is False
        and (audit.get("uniqueness") or {})
        .get(FACTOR_NAME, {})
        .get("comparison_factor_count")
        == 125
    ):
        raise Campaign097CompactFeatureError("no-return admission changed")
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists() or partial_root.exists():
        raise Campaign097CompactFeatureError("compact output already exists")
    partial_root.mkdir(parents=True)
    partition_root = partial_root / "partitions"
    partition_root.mkdir()

    source_keys, source_values = _load_all_candidate_arrays()
    eligibility = json.loads(ELIGIBILITY_MANIFEST.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    eligible_total = 0
    for record in eligibility.get("files") or []:
        year = int(record["year"])
        key_frame = pd.read_parquet(
            ELIGIBILITY_MANIFEST.parent / str(record["path"]),
            columns=["stock_day_key"],
        )
        denominator_keys = key_frame["stock_day_key"].to_numpy(dtype=np.int64)
        day_numbers = source_keys // 4_000_000
        start = np.datetime64(f"{year}-01-01", "D").astype(np.int64)
        stop = np.datetime64(f"{year + 1}-01-01", "D").astype(np.int64)
        selected = (day_numbers >= start) & (day_numbers < stop)
        keys, values, _ = audit_v4.align_candidate_year(
            eligible_keys=denominator_keys,
            candidate_keys=source_keys[selected],
            candidate_values=source_values[selected],
            year=year,
        )
        path = partition_root / f"{year}.parquet"
        _write_partition(path, keys, values)
        eligible_rows = int(np.isfinite(values).sum())
        eligible_total += eligible_rows
        records.append(
            {
                "year": year,
                "path": f"partitions/{year}.parquet",
                "rows": len(keys),
                "eligible_rows": eligible_rows,
                "sha256": _sha256(path),
                "frame_sha256": _frame_sha256(keys, values),
            }
        )
    dataset_payload = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign097_compact_feature_snapshot",
        "status": "immutable_compact_factor_ready_for_exact_single_development_trial",
        "factor_name": FACTOR_NAME,
        "factor_direction": "higher",
        "source_manifest_path": str(SOURCE_MANIFEST.resolve()),
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_dataset_sha256": SOURCE_DATASET_SHA256,
        "eligibility_manifest_path": str(ELIGIBILITY_MANIFEST.resolve()),
        "eligibility_manifest_sha256": ELIGIBILITY_MANIFEST_SHA256,
        "authoritative_no_return_audit_path": str(
            AUTHORITATIVE_NO_RETURN_AUDIT.resolve()
        ),
        "authoritative_no_return_audit_sha256": AUTHORITATIVE_NO_RETURN_AUDIT_SHA256,
        "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
        "files": records,
        "partitions": len(records),
        "rows": sum(int(item["rows"]) for item in records),
        "factor_eligible_rows": {FACTOR_NAME: eligible_total},
        "calendar_sessions": EXPECTED_SESSIONS,
        "candidate_source_columns_read": ["trade_date", "symbol", FACTOR_NAME],
        "eligibility_source_columns_read": ["stock_day_key"],
        "comparison_values_read_by_publication": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    if not (
        manifest["partitions"] == EXPECTED_PARTITIONS
        and manifest["rows"] == EXPECTED_ROWS
        and eligible_total == EXPECTED_ELIGIBLE_ROWS
    ):
        raise Campaign097CompactFeatureError("compact snapshot aggregates changed")
    manifest_path = partial_root / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    partial_root.replace(final_root)
    return final_root / "snapshot_manifest.json"


def verify_snapshot(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = eligible = 0
    observed: list[dict[str, Any]] = []
    for record in manifest.get("files") or []:
        path = manifest_path.parent / str(record["path"])
        _require(path, str(record["sha256"]), "compact partition")
        frame = pd.read_parquet(path, columns=["stock_day_key", FACTOR_NAME])
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        if _frame_sha256(keys, values) != str(record["frame_sha256"]):
            raise Campaign097CompactFeatureError("compact frame changed")
        rows += len(frame)
        eligible += int(np.isfinite(values).sum())
        observed.append(dict(record))
    dataset_sha256 = hashlib.sha256(
        json.dumps(
            observed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign097_compact_feature_snapshot"
        and len(observed) == EXPECTED_PARTITIONS
        and rows == manifest.get("rows") == EXPECTED_ROWS
        and eligible
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and dataset_sha256 == manifest.get("dataset_sha256")
    ):
        raise Campaign097CompactFeatureError("compact snapshot verification changed")
    return {
        "status": "verified",
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": dataset_sha256,
        "partitions": len(observed),
        "rows": rows,
        "eligible_rows": eligible,
        "historical_daily_price_or_forward_return_values_read": False,
    }


def status(*, data_root: Path) -> dict[str, Any]:
    root = output_root(data_root)
    return {
        "output_root": str(root),
        "published": (root / "snapshot_manifest.json").is_file(),
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "build", "verify"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.command == "status":
        payload: Any = status(data_root=args.data_root)
    elif args.command == "build":
        payload = {"manifest": str(build_snapshot(data_root=args.data_root))}
    else:
        if args.manifest is None:
            raise Campaign097CompactFeatureError("--manifest is required")
        payload = verify_snapshot(args.manifest)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
