#!/usr/bin/env python3
"""Build Campaign101's frozen 129-factor lower-quartile consensus snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import gc
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pa_dataset
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign100_features as c100

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_no_return_preregistration.json"
)
DEFAULT_SOURCE_CATALOG = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_101_source_catalog.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_feature_implementation_freeze_v3_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign101_features.py"
)

PROTOCOL_SHA256 = "2d1919a7dd53e340158e6e59d48af65132625dd36725a417cef6119241f925c3"
SOURCE_CATALOG_SHA256 = (
    "e47ce3727bb4fcc68832d1d5f686000734b80d72752c7661d747d5a5ef2b8323"
)
CACHE_MANIFEST_SHA256 = (
    "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
)
CACHE_DATASET_SHA256 = (
    "4a56dac48c14b667b6ee431519266f27bb8ff7cc25c51d8dce3bbc7aebe0376f"
)
NUMERIC_POLICY_SHA256 = (
    "517193a12ad592015a4af7579041abf79c508dbbdaf3e2a7d5f1d752f391458f"
)
NUMERIC_COUNT = 129
NUMERIC_ORDER_SHA256 = (
    "a029c53fb237cc1d34aec0a9f7b67856ffa1a67ffe0fc9620fb230680353263b"
)
COMPLETE_DEFINITION_COUNT = 132
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "2d0c342fe9644092e562832fe928473c230cbf982c1fb32f9d5c41c0a3594a42"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_SESSIONS = 1_632
EXPECTED_PARTITIONS = 7
EXPECTED_YEARS = tuple(range(2019, 2026))
MINIMUM_FINITE_COMPONENTS = 97
MAXIMUM_MISSING_COMPONENTS = 32
ORDER_STATISTIC_INDEX = 32
FACTOR_NAME = "full_numeric_library_directional_lower_quartile_consensus_129f"
ELIGIBLE_NAME = f"{FACTOR_NAME}_eligible"
FINITE_COUNT_NAME = f"{FACTOR_NAME}_finite_component_count"
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, ELIGIBLE_NAME, FINITE_COUNT_NAME)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign101_feature_library_v1"
)


class Campaign101FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign101 invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected:
        raise Campaign101FeatureError(f"{label} changed: {resolved}")


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return c100._order_digest(items)


def reconstruct_numeric_sources() -> list[dict[str, str]]:
    items = [dict(item) for item in c100.reconstruct_comparisons()]
    items.append({"name": c100.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COUNT
        or _order_digest(items) != NUMERIC_ORDER_SHA256
        or items[-1] != {"name": c100.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign101FeatureError("Campaign101 numeric source order changed")
    return items


def load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    _require(DEFAULT_PROTOCOL, PROTOCOL_SHA256, "Campaign101 protocol")
    _require(
        DEFAULT_SOURCE_CATALOG, SOURCE_CATALOG_SHA256, "Campaign101 source catalog"
    )
    reports = [
        bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
        for path in (DEFAULT_PROTOCOL, DEFAULT_SOURCE_CATALOG)
    ]
    if not all(item.get("all_bindings_passed") is True for item in reports):
        raise Campaign101FeatureError("Campaign101 frozen input binding failed")
    protocol = json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    catalog = json.loads(DEFAULT_SOURCE_CATALOG.read_text(encoding="utf-8"))
    candidate = protocol.get("candidate") or {}
    first = catalog.get("first_98_numeric_sources") or {}
    post = list(catalog.get("post_cache_numeric_sources") or [])
    expected = reconstruct_numeric_sources()
    observed = [
        *cache_v4._library_layout()["definitions"],
        *[
            {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
            for item in post
        ],
    ]
    if not (
        protocol.get("status")
        == "frozen_before_campaign101_source_factor_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("source_factor_count") == NUMERIC_COUNT
        and candidate.get("source_factor_order_sha256") == NUMERIC_ORDER_SHA256
        and candidate.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and candidate.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and candidate.get("minimum_finite_components") == MINIMUM_FINITE_COMPONENTS
        and candidate.get("maximum_missing_components") == MAXIMUM_MISSING_COMPONENTS
        and (candidate.get("aggregation") or {}).get("zero_indexed_partition_index")
        == ORDER_STATISTIC_INDEX
        and (catalog.get("numeric_policy") or {}).get("sha256") == NUMERIC_POLICY_SHA256
        and first.get("logical_numeric_count") == 98
        and (first.get("cache_manifest") or {}).get("sha256") == CACHE_MANIFEST_SHA256
        and (first.get("cache_manifest") or {}).get("dataset_sha256")
        == CACHE_DATASET_SHA256
        and len(post) == 31
        and [int(item["ordinal"]) for item in post] == list(range(99, 130))
        and observed == expected
        and _order_digest(observed) == NUMERIC_ORDER_SHA256
    ):
        raise Campaign101FeatureError("Campaign101 frozen protocol semantics changed")
    return protocol, catalog


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign101FeatureError(
            "Campaign101 feature implementation freeze is absent"
        )
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign101_feature_implementation_freeze"
        and record.get("status")
        == "frozen_after_failed_build_source_values_before_repaired_candidate_snapshot_rerun"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("source_catalog") or {}).get("sha256") == SOURCE_CATALOG_SHA256
        and (record.get("feature_builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("synthetic_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("source_factor_values_read_before_freeze") is True
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign101FeatureError(
            "Campaign101 feature implementation freeze changed"
        )
    return record


def _directional_percentile(
    values: np.ndarray,
    session_codes: np.ndarray,
    direction: str,
) -> np.ndarray:
    """Rank finite values independently in each session, preserving missing states."""

    array = np.asarray(values, dtype=np.float64)
    sessions = np.asarray(session_codes, dtype=np.int64)
    if (
        array.ndim != 1
        or sessions.shape != array.shape
        or direction
        not in {
            "higher",
            "lower",
        }
    ):
        raise Campaign101FeatureError("directional percentile inputs changed")
    ranked = (
        pd.Series(array)
        .groupby(pd.Series(sessions), sort=False, observed=True)
        .rank(
            method="average",
            pct=True,
            ascending=direction == "higher",
        )
    )
    result = ranked.to_numpy(dtype=np.float64)
    finite = np.isfinite(result)
    if np.any((result[finite] <= 0.0) | (result[finite] > 1.0)):
        raise Campaign101FeatureError("directional percentile escaped (0,1]")
    return result


def _lower_quartile_consensus(
    component_scores: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the sole frozen missingness threshold and 33rd order statistic."""

    scores = np.asarray(component_scores, dtype=np.float64)
    if scores.ndim != 2 or scores.shape[1] != NUMERIC_COUNT:
        raise Campaign101FeatureError("Campaign101 component matrix shape changed")
    finite = np.isfinite(scores)
    if np.any((scores[finite] <= 0.0) | (scores[finite] > 1.0)):
        raise Campaign101FeatureError("Campaign101 component scores escaped (0,1]")
    finite_count = finite.sum(axis=1).astype(np.uint8)
    eligible = finite_count >= MINIMUM_FINITE_COMPONENTS
    imputed = np.where(finite, scores, 0.0)
    values = np.partition(imputed, ORDER_STATISTIC_INDEX, axis=1)[
        :, ORDER_STATISTIC_INDEX
    ].astype(np.float64, copy=False)
    values[~eligible] = np.nan
    if np.any(values[eligible] <= 0.0) or np.any(values[eligible] > 1.0):
        raise Campaign101FeatureError(
            "eligible Campaign101 score is not observed finite rank"
        )
    return values, eligible, finite_count


def _compact_stock_day_keys(trade_dates: pd.Series, symbols: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2), errors="coerce")
    if dates.isna().any() or exchange.isna().any() or codes.isna().any():
        raise Campaign101FeatureError("source stock-day identity cannot be compacted")
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security_number = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security_number


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record["path"]))
    return (
        raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()
    )


def _verify_record(path: Path, expected: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign101FeatureError(f"source partition changed: {path}")


def _verify_source_files(
    manifest_path: Path,
    manifest: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    records = list(manifest.get("files") or [])
    if len(records) not in {7, 33_015}:
        raise Campaign101FeatureError(
            f"unexpected source partition count: {manifest_path}"
        )
    jobs: list[tuple[Path, str]] = []
    for record in records:
        expected = str(record.get("sha256") or record.get("output_byte_sha256") or "")
        if len(expected) != 64:
            raise Campaign101FeatureError(
                f"source partition receipt absent: {manifest_path}"
            )
        jobs.append((_record_path(manifest_path, record), expected))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_verify_record, path, digest) for path, digest in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": str(manifest.get("dataset_sha256") or ""),
        "partition_files_rehashed": len(records),
        "partition_files_verified": True,
    }


def _load_cache_year(
    cache_manifest_path: Path,
    cache_manifest: dict[str, Any],
    year: int,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, Any]]:
    records = [item for item in cache_manifest["files"] if int(item["year"]) == year]
    if len(records) != 1:
        raise Campaign101FeatureError(f"compact-cache year {year} changed")
    record = records[0]
    path = _record_path(cache_manifest_path, record)
    _verify_record(path, str(record["sha256"]))
    layout = cache_v4._library_layout()
    table = pq.read_table(path, columns=["stock_day_key", *layout["physical_names"]])
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    keys = frame.pop("stock_day_key").to_numpy(dtype=np.int64)
    if not (
        len(keys) == int(record["rows"])
        and len(np.unique(keys)) == len(keys)
        and (len(keys) < 2 or np.all(keys[1:] > keys[:-1]))
    ):
        raise Campaign101FeatureError(f"compact-cache keys changed for {year}")
    physical = {
        name: pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype=np.float64)
        for name in layout["physical_names"]
    }
    logical = {name: physical[name] for name in layout["fixed_names"]}
    logical.update(
        cache_v4.reconstruct_dynamic_quality_values(
            candidate_keys=keys,
            raw_auxiliary_values={
                name: physical[name] for name in cache_v4.AUXILIARY_COLUMNS
            },
        )
    )
    if set(logical) != set(layout["logical_names"]):
        raise Campaign101FeatureError("compact-cache logical reconstruction changed")
    del frame, table, physical
    gc.collect()
    return (
        keys,
        logical,
        {
            "year": year,
            "path": str(path),
            "sha256": str(record["sha256"]),
            "rows": len(keys),
        },
    )


def _load_post_source_year(
    *,
    source: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: Path,
    year: int,
    base_keys: np.ndarray,
) -> np.ndarray:
    factor = str(source["name"])
    records = [
        item for item in manifest.get("files") or [] if int(item["year"]) == year
    ]
    if not records:
        raise Campaign101FeatureError(f"{factor} has no {year} source partitions")
    paths = [str(_record_path(manifest_path, item)) for item in records]
    if len(manifest.get("files") or []) == EXPECTED_PARTITIONS:
        dataset = pa_dataset.dataset(paths, format="parquet")
        table = dataset.to_table(columns=["stock_day_key", factor], use_threads=True)
        keys = table["stock_day_key"].to_numpy(zero_copy_only=False).astype(np.int64)
        values = table[factor].to_numpy(zero_copy_only=False).astype(np.float64)
        del table, dataset
    else:
        dataset = pa_dataset.dataset(paths, format="parquet")
        scanner = dataset.scanner(
            columns=["trade_date", "symbol", factor],
            batch_size=262_144,
            use_threads=True,
        )
        key_parts: list[np.ndarray] = []
        value_parts: list[np.ndarray] = []
        total_rows = 0
        for batch in scanner.to_batches():
            frame = batch.to_pandas(split_blocks=True, self_destruct=True)
            total_rows += len(frame)
            keys_batch = _compact_stock_day_keys(frame["trade_date"], frame["symbol"])
            positions = np.searchsorted(base_keys, keys_batch, side="left")
            bounded = positions < len(base_keys)
            matched = np.zeros(len(keys_batch), dtype=bool)
            matched[bounded] = base_keys[positions[bounded]] == keys_batch[bounded]
            if matched.any():
                key_parts.append(keys_batch[matched])
                value_parts.append(
                    pd.to_numeric(frame.loc[matched, factor], errors="coerce").to_numpy(
                        dtype=np.float64
                    )
                )
            del frame, keys_batch, positions, bounded, matched, batch
        expected_rows = sum(int(item["rows"]) for item in records)
        if total_rows != expected_rows:
            raise Campaign101FeatureError(f"{factor} {year} source row count changed")
        keys = np.concatenate(key_parts) if key_parts else np.empty(0, dtype=np.int64)
        values = (
            np.concatenate(value_parts)
            if value_parts
            else np.empty(0, dtype=np.float64)
        )
        del scanner, dataset, key_parts, value_parts
    if values.shape != keys.shape:
        raise Campaign101FeatureError(f"{factor} {year} identity/value shape changed")
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign101FeatureError(f"{factor} {year} identities changed")
    positions = np.searchsorted(base_keys, keys, side="left")
    bounded = positions < len(base_keys)
    if not (bounded.all() and np.array_equal(base_keys[positions], keys)):
        raise Campaign101FeatureError(f"{factor} {year} escaped the frozen base")
    aligned = np.full(len(base_keys), np.nan, dtype=np.float64)
    aligned[positions] = values
    return aligned


def _frame_sha256(
    keys: np.ndarray,
    values: np.ndarray,
    eligible: np.ndarray,
    finite_count: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(keys, dtype="<i8").tobytes())
    digest.update(bytes.fromhex(cache_v1.canonical_column_sha256(values)))
    digest.update(np.asarray(eligible, dtype=np.uint8).tobytes())
    digest.update(np.asarray(finite_count, dtype=np.uint8).tobytes())
    return digest.hexdigest()


def _write_partition(
    path: Path,
    keys: np.ndarray,
    values: np.ndarray,
    eligible: np.ndarray,
    finite_count: np.ndarray,
) -> None:
    table = pa.Table.from_arrays(
        [
            pa.array(keys, type=pa.int64()),
            pa.array(values, type=pa.float64(), from_pandas=True),
            pa.array(eligible, type=pa.bool_()),
            pa.array(finite_count, type=pa.uint8()),
        ],
        names=list(OUTPUT_COLUMNS),
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


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign101_feature_library"
        / OUTPUT_RUN_ID
    )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    if workers < 1 or workers > 16:
        raise Campaign101FeatureError("--workers must be between 1 and 16")
    freeze = _load_implementation_freeze()
    protocol, catalog = load_frozen_inputs()
    data_root = data_root.expanduser().resolve()
    final_root = output_root(data_root)
    if final_root.exists():
        raise Campaign101FeatureError("Campaign101 output already exists")
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise Campaign101FeatureError("data root has less than 5 GiB free")

    cache_binding = catalog["first_98_numeric_sources"]["cache_manifest"]
    cache_manifest_path = Path(str(cache_binding["path"])).resolve()
    _require(cache_manifest_path, CACHE_MANIFEST_SHA256, "compact-cache manifest")
    cache_manifest = json.loads(cache_manifest_path.read_text(encoding="utf-8"))
    if cache_manifest.get("dataset_sha256") != CACHE_DATASET_SHA256:
        raise Campaign101FeatureError("compact-cache dataset changed")
    sources: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
    source_verifications: list[dict[str, Any]] = []
    for source in catalog["post_cache_numeric_sources"]:
        manifest_path = Path(str(source["path"])).resolve()
        _require(manifest_path, str(source["sha256"]), f"{source['name']} manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("dataset_sha256") != source["dataset_sha256"]:
            raise Campaign101FeatureError(f"{source['name']} dataset changed")
        print(
            f"verifying source bytes {source['ordinal']:03d}/129 {source['name']}",
            flush=True,
        )
        receipt = _verify_source_files(manifest_path, manifest, workers)
        receipt["name"] = str(source["name"])
        receipt["ordinal"] = int(source["ordinal"])
        source_verifications.append(receipt)
        sources.append((source, manifest_path, manifest))

    final_root.parent.mkdir(parents=True, exist_ok=True)
    partial_root = Path(
        tempfile.mkdtemp(prefix=f".{OUTPUT_RUN_ID}.", dir=final_root.parent)
    )
    partition_root = partial_root / "partitions"
    partition_root.mkdir()
    layout = cache_v4._library_layout()
    first_definitions = [dict(item) for item in layout["definitions"]]
    records: list[dict[str, Any]] = []
    total_rows = 0
    total_eligible = 0
    try:
        for year in EXPECTED_YEARS:
            print(f"building Campaign101 year={year}", flush=True)
            keys, logical, cache_receipt = _load_cache_year(
                cache_manifest_path, cache_manifest, year
            )
            sessions = keys // 4_000_000
            matrix = np.empty((len(keys), NUMERIC_COUNT), dtype=np.float64)
            for index, definition in enumerate(first_definitions):
                matrix[:, index] = _directional_percentile(
                    logical[str(definition["name"])],
                    sessions,
                    str(definition["score_direction"]),
                )
            del logical
            for source, manifest_path, manifest in sources:
                index = int(source["ordinal"]) - 1
                raw = _load_post_source_year(
                    source=source,
                    manifest=manifest,
                    manifest_path=manifest_path,
                    year=year,
                    base_keys=keys,
                )
                matrix[:, index] = _directional_percentile(
                    raw, sessions, str(source["score_direction"])
                )
                del raw
            values, eligible, finite_count = _lower_quartile_consensus(matrix)
            path = partition_root / f"{year}.parquet"
            _write_partition(path, keys, values, eligible, finite_count)
            eligible_rows = int(eligible.sum())
            records.append(
                {
                    "year": year,
                    "path": f"partitions/{year}.parquet",
                    "rows": len(keys),
                    "eligible_rows": eligible_rows,
                    "sha256": _sha256(path),
                    "frame_sha256": _frame_sha256(keys, values, eligible, finite_count),
                    "minimum_finite_components_observed": int(finite_count.min()),
                    "maximum_finite_components_observed": int(finite_count.max()),
                    "cache_source": cache_receipt,
                }
            )
            total_rows += len(keys)
            total_eligible += eligible_rows
            del keys, sessions, matrix, values, eligible, finite_count
            gc.collect()
        if total_rows != EXPECTED_ROWS or len(records) != EXPECTED_PARTITIONS:
            raise Campaign101FeatureError("Campaign101 aggregate base changed")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign101_feature_snapshot",
            "status": "immutable_candidate_ready_for_ordered_no_return_gates",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "factor_name": FACTOR_NAME,
            "factor_direction": "higher",
            "formula": protocol["candidate"],
            "protocol": {"path": str(DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
            "source_catalog": {
                "path": str(DEFAULT_SOURCE_CATALOG),
                "sha256": SOURCE_CATALOG_SHA256,
            },
            "implementation_freeze": {
                "path": str(DEFAULT_IMPLEMENTATION_FREEZE),
                "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
                "feature_builder_sha256": freeze["feature_builder"]["sha256"],
                "synthetic_tests_sha256": freeze["synthetic_tests"]["sha256"],
            },
            "numeric_source_factor_count": NUMERIC_COUNT,
            "numeric_source_factor_order_sha256": NUMERIC_ORDER_SHA256,
            "numeric_source_factors": reconstruct_numeric_sources(),
            "cache_manifest": {
                "path": str(cache_manifest_path),
                "sha256": CACHE_MANIFEST_SHA256,
                "dataset_sha256": CACHE_DATASET_SHA256,
            },
            "post_cache_source_verifications": source_verifications,
            "post_cache_source_verifications_sha256": _json_sha256(
                source_verifications
            ),
            "files": records,
            "partitions": len(records),
            "rows": total_rows,
            "calendar_sessions": EXPECTED_SESSIONS,
            "factor_eligible_rows": {FACTOR_NAME: total_eligible},
            "dataset_sha256": _json_sha256(records),
            "source_factor_values_read": True,
            "comparison_values_read_by_candidate_builder": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "provider_request_issued": False,
            "candidate49_history_signal_or_execution_backfilled": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        manifest_path = partial_root / "snapshot_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(partial_root, final_root)
        return final_root / "snapshot_manifest.json"
    except BaseException:
        shutil.rmtree(partial_root, ignore_errors=True)
        raise


def verify_snapshot(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = list(manifest.get("files") or [])
    rows = eligible_rows = 0
    sessions: set[int] = set()
    for record in records:
        path = _record_path(manifest_path, record)
        _verify_record(path, str(record["sha256"]))
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        eligible = frame[ELIGIBLE_NAME].to_numpy(dtype=bool)
        finite_count = frame[FINITE_COUNT_NAME].to_numpy(dtype=np.uint8)
        if not (
            np.array_equal(np.isfinite(values), eligible)
            and np.array_equal(eligible, finite_count >= MINIMUM_FINITE_COMPONENTS)
            and _frame_sha256(keys, values, eligible, finite_count)
            == record["frame_sha256"]
        ):
            raise Campaign101FeatureError(
                f"Campaign101 partition semantics changed: {path}"
            )
        rows += len(keys)
        eligible_rows += int(eligible.sum())
        sessions.update((keys // 4_000_000).tolist())
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign101_feature_snapshot"
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("numeric_source_factor_count") == NUMERIC_COUNT
        and manifest.get("numeric_source_factor_order_sha256") == NUMERIC_ORDER_SHA256
        and len(records) == EXPECTED_PARTITIONS
        and rows == manifest.get("rows") == EXPECTED_ROWS
        and len(sessions) == manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and eligible_rows
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and manifest.get("dataset_sha256") == _json_sha256(records)
        and manifest.get("historical_forward_return_fields_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign101FeatureError("Campaign101 snapshot verification changed")
    return {
        "status": "verified",
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(records),
        "rows": rows,
        "eligible_rows": eligible_rows,
        "calendar_sessions": len(sessions),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(*, data_root: Path) -> dict[str, Any]:
    root = output_root(data_root)
    return {
        "output_root": str(root),
        "published": (root / "snapshot_manifest.json").is_file(),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "source_factor_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "build", "verify"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.command == "status":
        payload: Any = status(data_root=args.data_root)
    elif args.command == "build":
        payload = {
            "manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    else:
        if args.manifest is None:
            raise Campaign101FeatureError("--manifest is required")
        payload = verify_snapshot(args.manifest)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
