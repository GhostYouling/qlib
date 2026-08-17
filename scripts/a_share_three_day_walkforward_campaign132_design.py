#!/usr/bin/env python3
"""Build Campaign132's frozen complete-140 directional-rank design matrix."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign102_design as c102
from scripts import a_share_three_day_walkforward_campaign128_features as c128


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "b4c3f6b3a69506c8a8f5ee71ffe05e487af0f71ae2b104adb3a79b2efc4ac0be"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_design_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign132_design.py"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign132_numeric140_design_v1"
)
OUTPUT_RELATIVE = (
    Path("derived/a_share/rich/tushare/minute_walkforward_campaign132_design_matrix")
    / OUTPUT_RUN_ID
)
BASE_FEATURE_COUNT = 130
FEATURE_COUNT = 140
FEATURE_ORDER_SHA256 = (
    "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
)
MINIMUM_FINITE_COMPONENTS = 105
FINITE_COUNT_NAME = "finite_component_count"
ELIGIBLE_NAME = "model_support_eligible"
EXPECTED_YEARS = tuple(range(2019, 2026))


class Campaign132DesignError(RuntimeError):
    """Fail closed when the frozen Campaign132 design contract changes."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def frame_digest(frame: pd.DataFrame) -> str:
    work = frame.copy()
    digest = hashlib.sha256()
    for column in work.columns:
        digest.update(column.encode("utf-8"))
        values = work[column]
        if pd.api.types.is_float_dtype(values.dtype):
            digest.update(values.to_numpy(dtype="<f4", copy=False).tobytes())
        elif pd.api.types.is_bool_dtype(values.dtype):
            digest.update(values.to_numpy(dtype=np.uint8, copy=False).tobytes())
        elif pd.api.types.is_integer_dtype(values.dtype):
            digest.update(values.to_numpy(dtype="<i8", copy=False).tobytes())
        else:
            raise Campaign132DesignError(f"unsupported digest dtype: {column}")
    return digest.hexdigest()


def output_root(data_root: Path = DEFAULT_DATA_ROOT) -> Path:
    return data_root.expanduser().resolve() / OUTPUT_RELATIVE


def current_feature_order() -> list[dict[str, str]]:
    items = [dict(item) for item in c128.reconstruct_comparisons()]
    items.append({"name": c128.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FEATURE_COUNT
        or json_digest([[item["name"], item["score_direction"]] for item in items])
        != FEATURE_ORDER_SHA256
    ):
        raise Campaign132DesignError("current numeric feature order changed")
    return items


def feature_names() -> list[str]:
    return [item["name"] for item in current_feature_order()]


def _resolve_record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record["path"]))
    return (
        raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()
    )


def _expected_record_sha(record: dict[str, Any]) -> str:
    expected = str(record.get("sha256") or record.get("output_byte_sha256") or "")
    if len(expected) != 64:
        raise Campaign132DesignError("source partition hash is absent")
    return expected


def _verify_path(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256(path) != expected:
        raise Campaign132DesignError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    _verify_path(DEFAULT_PROTOCOL, PROTOCOL_SHA256, "Campaign132 protocol")
    spec = json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    library = spec.get("complete_feature_library") or {}
    support = library.get("design_support") or {}
    appended = list(library.get("appended_numeric_features_in_order") or [])
    names = feature_names()
    if not (
        spec.get("kind") == "a_share_three_day_walkforward_campaign132_preregistration"
        and spec.get("status")
        == "frozen_complete_numeric140_model_campaign_before_component_values_or_historical_returns"
        and library.get("numeric_feature_count") == FEATURE_COUNT
        and library.get("numeric_feature_order_sha256") == FEATURE_ORDER_SHA256
        and len(appended) == FEATURE_COUNT - BASE_FEATURE_COUNT
        and [item.get("name") for item in appended] == names[BASE_FEATURE_COUNT:]
        and all(item.get("direction") == "higher" for item in appended)
        and support.get("minimum_finite_components") == MINIMUM_FINITE_COMPONENTS
        and support.get("model_input_missing_fill") == 0.5
        and support.get("missing_indicator_or_missing_split_allowed") is False
        and support.get("years") == list(EXPECTED_YEARS)
        and support.get("output_run_id") == OUTPUT_RUN_ID
        and (spec.get("research_boundary") or {}).get(
            "component_factor_values_read_before_preregistration"
        )
        is False
        and (spec.get("research_boundary") or {}).get(
            "historical_daily_price_or_forward_return_values_read_before_preregistration"
        )
        is False
    ):
        raise Campaign132DesignError("Campaign132 protocol semantics changed")
    base = library.get("base_numeric130_design") or {}
    base_path = Path(str(base.get("path", ""))).expanduser().resolve()
    _verify_path(base_path, str(base.get("sha256")), "base numeric130 manifest")
    base_manifest = json.loads(base_path.read_text(encoding="utf-8"))
    if not (
        base.get("feature_count") == BASE_FEATURE_COUNT
        and base.get("feature_order_sha256") == c102.NUMERIC_ORDER_SHA256
        and base_manifest.get("dataset_sha256") == base.get("dataset_sha256")
        and base_manifest.get("component_count") == BASE_FEATURE_COUNT
    ):
        raise Campaign132DesignError("base numeric130 manifest semantics changed")
    for item in appended:
        path = Path(str(item["manifest_path"])).expanduser().resolve()
        _verify_path(path, str(item["manifest_sha256"]), f"{item['name']} manifest")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("dataset_sha256") != item.get("dataset_sha256"):
            raise Campaign132DesignError(f"{item['name']} dataset digest changed")
    return spec


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign132DesignError(
            "Campaign132 design implementation freeze is absent"
        )
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign132_design_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign132_component_factor_values_or_historical_returns"
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("builder_path")
        == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and frozen.get("builder_sha256") == sha256(Path(__file__).resolve())
        and frozen.get("test_path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and frozen.get("test_sha256") == sha256(TEST_PATH)
        and frozen.get("feature_count") == FEATURE_COUNT
        and frozen.get("feature_order_sha256") == FEATURE_ORDER_SHA256
        and frozen.get("minimum_finite_components") == MINIMUM_FINITE_COMPONENTS
        and boundary.get("component_factor_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign132DesignError("Campaign132 design implementation freeze changed")
    return record


def compact_stock_day_keys(trade_dates: pd.Series, symbols: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2), errors="coerce")
    if dates.isna().any() or exchange.isna().any() or codes.isna().any():
        raise Campaign132DesignError("source stock-day identity cannot be compacted")
    days = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return days * 4_000_000 + security


def align_values(
    *, source_keys: np.ndarray, source_values: np.ndarray, target_keys: np.ndarray
) -> np.ndarray:
    source_keys = np.asarray(source_keys, dtype=np.int64)
    source_values = np.asarray(source_values, dtype=np.float64)
    target_keys = np.asarray(target_keys, dtype=np.int64)
    if len(source_keys) != len(source_values) or len(np.unique(source_keys)) != len(
        source_keys
    ):
        raise Campaign132DesignError("source stock-day keys are not unique")
    order = np.argsort(source_keys, kind="mergesort")
    keys = source_keys[order]
    values = source_values[order]
    positions = np.searchsorted(keys, target_keys)
    in_range = positions < len(keys)
    matched = np.zeros(len(target_keys), dtype=bool)
    matched[in_range] = keys[positions[in_range]] == target_keys[in_range]
    aligned = np.full(len(target_keys), np.nan, dtype=np.float64)
    aligned[matched] = values[positions[matched]]
    return aligned


def favorable_percentile_ranks(keys: np.ndarray, raw_values: np.ndarray) -> np.ndarray:
    compact = np.asarray(keys, dtype=np.int64)
    values = np.asarray(raw_values, dtype=np.float64)
    if len(compact) != len(values):
        raise Campaign132DesignError("rank input length changed")
    days = compact // 4_000_000
    ranked = (
        pd.Series(values)
        .groupby(pd.Series(days), sort=False)
        .rank(method="average", pct=True, ascending=True)
        .to_numpy(dtype=np.float64)
    )
    finite = np.isfinite(ranked)
    if np.any((ranked[finite] <= 0.0) | (ranked[finite] > 1.0)):
        raise Campaign132DesignError("directional percentile escaped (0,1]")
    return ranked.astype(np.float32)


def extend_matrix(
    base_matrix: np.ndarray, appended_ranks: Iterable[np.ndarray]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base = np.asarray(base_matrix, dtype=np.float32)
    extra = [np.asarray(values, dtype=np.float32) for values in appended_ranks]
    if base.ndim != 2 or base.shape[1] != BASE_FEATURE_COUNT:
        raise Campaign132DesignError("base design shape changed")
    if len(extra) != FEATURE_COUNT - BASE_FEATURE_COUNT or any(
        values.shape != (len(base),) for values in extra
    ):
        raise Campaign132DesignError("appended design shape changed")
    matrix = np.column_stack([base, *extra]).astype(np.float32, copy=False)
    finite_count = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
    eligible = finite_count >= MINIMUM_FINITE_COMPONENTS
    return matrix, finite_count, eligible


def _load_base_year(
    base_manifest_path: Path, base_manifest: dict[str, Any], year: int
) -> pd.DataFrame:
    records = [item for item in base_manifest["files"] if int(item["year"]) == year]
    if len(records) != 1:
        raise Campaign132DesignError(f"base partition count changed for {year}")
    record = records[0]
    path = _resolve_record_path(base_manifest_path, record)
    _verify_path(path, str(record["sha256"]), f"base partition {year}")
    columns = ["stock_day_key", *c102.component_columns()]
    frame = pd.read_parquet(path, columns=columns)
    if frame["stock_day_key"].duplicated().any():
        raise Campaign132DesignError(f"base keys duplicate for {year}")
    return frame


def _read_source_record(
    manifest_path: Path, record: dict[str, Any], factor: str
) -> tuple[np.ndarray, np.ndarray, str]:
    path = _resolve_record_path(manifest_path, record)
    expected = _expected_record_sha(record)
    _verify_path(path, expected, f"{factor} source partition")
    schema = pq.read_schema(path)
    if "stock_day_key" in schema.names:
        frame = pd.read_parquet(path, columns=["stock_day_key", factor])
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
    elif {"trade_date", "symbol", factor}.issubset(schema.names):
        frame = pd.read_parquet(path, columns=["trade_date", "symbol", factor])
        keys = compact_stock_day_keys(frame["trade_date"], frame["symbol"])
    else:
        raise Campaign132DesignError(f"{factor} source schema changed")
    values = pd.to_numeric(frame[factor], errors="coerce").to_numpy(dtype=np.float64)
    return keys, values, expected


def _load_source_year(
    item: dict[str, Any], year: int, *, workers: int
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    factor = str(item["name"])
    manifest_path = Path(str(item["manifest_path"])).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = [record for record in manifest["files"] if int(record["year"]) == year]
    if not records:
        raise Campaign132DesignError(f"{factor} has no records for {year}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        loaded = list(
            pool.map(
                lambda record: _read_source_record(manifest_path, record, factor),
                records,
            )
        )
    keys = np.concatenate([result[0] for result in loaded])
    values = np.concatenate([result[1] for result in loaded])
    if len(np.unique(keys)) != len(keys):
        raise Campaign132DesignError(f"{factor} source keys duplicate for {year}")
    return (
        keys,
        values,
        {
            "factor": factor,
            "manifest_path": str(manifest_path),
            "manifest_sha256": str(item["manifest_sha256"]),
            "dataset_sha256": str(item["dataset_sha256"]),
            "source_partition_count": len(records),
            "source_rows": len(keys),
            "finite_source_values": int(np.isfinite(values).sum()),
        },
    )


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".parquet", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(table, temporary, compression="zstd")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, suffix=".json", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_plan(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    spec = load_protocol()
    validate_implementation_freeze()
    final_root = output_root(data_root)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_design_plan",
        "status": "ready_to_build_numeric140_design_without_prices_or_returns",
        "ready": not final_root.exists(),
        "protocol_sha256": PROTOCOL_SHA256,
        "feature_count": FEATURE_COUNT,
        "feature_order_sha256": FEATURE_ORDER_SHA256,
        "minimum_finite_components": MINIMUM_FINITE_COMPONENTS,
        "source_manifest_count": 11,
        "output_root": str(final_root),
        "component_factor_values_read_by_plan": False,
        "historical_daily_price_or_forward_return_values_read_by_plan": False,
        "provider_request_issued": False,
        "trial_count": len(spec["trial_catalog"]),
    }


def build_design(*, data_root: Path = DEFAULT_DATA_ROOT, workers: int = 8) -> Path:
    plan = build_plan(data_root)
    if plan["ready"] is not True:
        raise Campaign132DesignError("Campaign132 design output already exists")
    spec = load_protocol()
    library = spec["complete_feature_library"]
    base_manifest_path = Path(library["base_numeric130_design"]["path"]).resolve()
    base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    appended = list(library["appended_numeric_features_in_order"])
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{final_root.name}.partial"
    if partial_root.exists():
        raise Campaign132DesignError(f"partial output already exists: {partial_root}")
    partial_root.mkdir(parents=True)
    files: list[dict[str, Any]] = []
    try:
        names = feature_names()
        for year in EXPECTED_YEARS:
            print(
                f"Campaign132 design year {year}: loading base numeric130", flush=True
            )
            base = _load_base_year(base_manifest_path, base_manifest, year)
            keys = base.pop("stock_day_key").to_numpy(dtype=np.int64)
            base_matrix = base[list(c102.component_columns())].to_numpy(
                dtype=np.float32, copy=True
            )
            ranks: list[np.ndarray] = []
            receipts: list[dict[str, Any]] = []
            for item in appended:
                print(
                    f"Campaign132 design year {year}: loading {item['name']}",
                    flush=True,
                )
                source_keys, source_values, receipt = _load_source_year(
                    item, year, workers=workers
                )
                aligned = align_values(
                    source_keys=source_keys,
                    source_values=source_values,
                    target_keys=keys,
                )
                rank = favorable_percentile_ranks(keys, aligned)
                receipt["aligned_rows"] = len(rank)
                receipt["aligned_finite_values"] = int(np.isfinite(rank).sum())
                ranks.append(rank)
                receipts.append(receipt)
            matrix, finite_count, eligible = extend_matrix(base_matrix, ranks)
            output = pd.DataFrame(matrix, columns=names)
            output.insert(0, "stock_day_key", keys)
            output[FINITE_COUNT_NAME] = finite_count
            output[ELIGIBLE_NAME] = eligible
            relative = Path("partitions") / f"{year}.parquet"
            path = partial_root / relative
            _atomic_parquet(output, path)
            files.append(
                {
                    "year": year,
                    "path": str(relative),
                    "rows": len(output),
                    "eligible_rows": int(eligible.sum()),
                    "minimum_finite_components_observed": int(finite_count.min()),
                    "maximum_finite_components_observed": int(finite_count.max()),
                    "sha256": sha256(path),
                    "frame_sha256": frame_digest(output),
                    "source_receipts": receipts,
                }
            )
        digest_rows = [
            [
                item["year"],
                item["rows"],
                item["eligible_rows"],
                item["sha256"],
                item["frame_sha256"],
            ]
            for item in files
        ]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign132_numeric140_design_snapshot",
            "status": "immutable_design_ready_for_structural_audit_before_training_returns",
            "created_at": datetime.now(UTC).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol": {
                "path": str(DEFAULT_PROTOCOL),
                "sha256": PROTOCOL_SHA256,
            },
            "base_feature_count": BASE_FEATURE_COUNT,
            "feature_count": FEATURE_COUNT,
            "feature_names": names,
            "feature_order_sha256": FEATURE_ORDER_SHA256,
            "appended_feature_names": [item["name"] for item in appended],
            "minimum_finite_components": MINIMUM_FINITE_COMPONENTS,
            "neutral_model_fill": 0.5,
            "rows": int(sum(item["rows"] for item in files)),
            "eligible_rows": int(sum(item["eligible_rows"] for item in files)),
            "partitions": len(files),
            "files": files,
            "dataset_sha256": json_digest(digest_rows),
            "component_values_read": True,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "model_fitting_performed": False,
            "stress_2024_2025_return_fields_read": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "current_use_or_investment_advice": False,
        }
        _atomic_json(manifest, partial_root / "snapshot_manifest.json")
        os.replace(partial_root, final_root)
        return final_root / "snapshot_manifest.json"
    except BaseException:
        if partial_root.exists():
            failure = partial_root / "build_failure.json"
            _atomic_json(
                {
                    "kind": "a_share_three_day_walkforward_campaign132_design_build_failure",
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "partial_preserved": True,
                },
                failure,
            )
        raise


def verify_snapshot(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    target = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if target != expected or not target.is_file():
        raise Campaign132DesignError("Campaign132 snapshot path changed")
    manifest = json.loads(target.read_text(encoding="utf-8"))
    names = feature_names()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign132_numeric140_design_snapshot"
        and manifest.get("status")
        == "immutable_design_ready_for_structural_audit_before_training_returns"
        and manifest.get("feature_count") == FEATURE_COUNT
        and manifest.get("feature_names") == names
        and manifest.get("feature_order_sha256") == FEATURE_ORDER_SHA256
        and manifest.get("minimum_finite_components") == MINIMUM_FINITE_COMPONENTS
        and manifest.get("partitions") == len(manifest.get("files") or []) == 7
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_return_fields_read") is False
        and manifest.get("model_fitting_performed") is False
    ):
        raise Campaign132DesignError("Campaign132 snapshot metadata changed")

    def verify(record: dict[str, Any]) -> list[Any]:
        path = _resolve_record_path(target, record)
        _verify_path(path, str(record["sha256"]), "Campaign132 output partition")
        frame = pd.read_parquet(path)
        if (
            list(frame.columns)
            != ["stock_day_key", *names, FINITE_COUNT_NAME, ELIGIBLE_NAME]
            or len(frame) != int(record["rows"])
            or frame_digest(frame) != record["frame_sha256"]
        ):
            raise Campaign132DesignError("Campaign132 output frame changed")
        matrix = frame[names].to_numpy(dtype=np.float32, copy=False)
        finite_count = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
        eligible = finite_count >= MINIMUM_FINITE_COMPONENTS
        if not (
            np.array_equal(finite_count, frame[FINITE_COUNT_NAME].to_numpy(np.uint8))
            and np.array_equal(eligible, frame[ELIGIBLE_NAME].to_numpy(bool))
            and int(eligible.sum()) == int(record["eligible_rows"])
        ):
            raise Campaign132DesignError("Campaign132 output support changed")
        return [
            int(record["year"]),
            len(frame),
            int(eligible.sum()),
            str(record["sha256"]),
            str(record["frame_sha256"]),
        ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        digest_rows = list(pool.map(verify, manifest["files"]))
    if json_digest(digest_rows) != manifest.get("dataset_sha256"):
        raise Campaign132DesignError("Campaign132 dataset digest changed")
    return {
        "status": "verified",
        "manifest_path": str(target),
        "manifest_sha256": sha256(target),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": manifest["rows"],
        "eligible_rows": manifest["eligible_rows"],
        "feature_count": manifest["feature_count"],
        "component_values_read": True,
        "historical_daily_price_or_forward_return_values_read": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    build = sub.add_parser("build")
    build.add_argument("--confirm-build", action="store_true")
    build.add_argument("--workers", type=int, default=8)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "plan":
            payload = build_plan()
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if payload["ready"] else 2
        if args.command == "build":
            if not args.confirm_build:
                raise Campaign132DesignError("build requires --confirm-build")
            path = build_design(workers=args.workers)
            print(json.dumps({"status": "built", "manifest": str(path)}, indent=2))
            return 0
        payload = verify_snapshot(args.manifest, workers=args.workers)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Campaign132DesignError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
