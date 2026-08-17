#!/usr/bin/env python3
"""Build and audit Campaign102's frozen 130-factor directional-rank matrix.

This module is deliberately price/return blind.  It reconstructs the exact
v58 numeric library from immutable source snapshots, preserves component
missingness, and publishes only identities, directional ranks, finite counts,
and the frozen support flag.
"""

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
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign101_features as c101

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_no_return_preregistration.json"
)
DEFAULT_SOURCE_CATALOG = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_102_source_catalog.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_design_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign102_design.py"
)

PROTOCOL_SHA256 = "5def1f153c4cca94f2d646598f09b810108688488b8aab0b2be345366364b8f9"
SOURCE_CATALOG_SHA256 = "fd7e5f4486fc4cef5a954e279c865ac8718a214c8dd3bd10450b509f8fdfbd5c"
C101_BUILDER_SHA256 = "61bbb490c862f53548eedffa01265a3b814c29ef9bb489142aed07896d3168f4"
C101_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign101_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign101_feature_library_v1/snapshot_manifest.json"
)
C101_MANIFEST_SHA256 = "7a2db929fff69f46edbc93d57cdca9cc4427c47dd542291b4f58d879dd91a3b6"
C101_DATASET_SHA256 = "ed024ab2736b9766e1adb122b155189029f30a5d14e11d4d67a403ff9befef24"
NUMERIC_COUNT = 130
NUMERIC_ORDER_SHA256 = "c80d9b929536dd509d6c1a904f790831050e68200393de381f92ad9293ef69e7"
EXPECTED_ROWS = 1_331_759
EXPECTED_SESSIONS = 1_632
EXPECTED_PARTITIONS = 7
EXPECTED_YEARS = tuple(range(2019, 2026))
MINIMUM_FINITE_COMPONENTS = 98
FINITE_COUNT_NAME = "finite_component_count"
ELIGIBLE_NAME = "model_support_eligible"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign102_design_matrix_v1"
)


class Campaign102DesignError(RuntimeError):
    """Fail closed when a frozen Campaign102 design invariant changes."""


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
        raise Campaign102DesignError(f"{label} changed: {resolved}")


def reconstruct_numeric_sources() -> list[dict[str, str]]:
    items = [dict(item) for item in c101.reconstruct_numeric_sources()]
    items.append({"name": c101.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COUNT
        or c101._order_digest(items) != NUMERIC_ORDER_SHA256
        or items[-1]
        != {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign102DesignError("Campaign102 numeric source order changed")
    return items


def component_columns() -> tuple[str, ...]:
    return tuple(item["name"] for item in reconstruct_numeric_sources())


def _load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _require(DEFAULT_PROTOCOL, PROTOCOL_SHA256, "Campaign102 protocol")
    _require(DEFAULT_SOURCE_CATALOG, SOURCE_CATALOG_SHA256, "Campaign102 catalog")
    _require(Path(c101.__file__), C101_BUILDER_SHA256, "Campaign101 builder")
    _require(C101_MANIFEST_PATH, C101_MANIFEST_SHA256, "Campaign101 manifest")
    protocol = json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    catalog = json.loads(DEFAULT_SOURCE_CATALOG.read_text(encoding="utf-8"))
    c101_manifest = json.loads(C101_MANIFEST_PATH.read_text(encoding="utf-8"))
    design = protocol.get("design_matrix") or {}
    numeric = catalog.get("numeric_policy") or {}
    final = catalog.get("final_numeric_source") or {}
    final_manifest = final.get("manifest") or {}
    if not (
        protocol.get("status")
        == "frozen_before_campaign102_design_matrix_model_fit_validation_or_lockbox_return_values"
        and design.get("source_factor_count") == NUMERIC_COUNT
        and design.get("source_factor_order_sha256") == NUMERIC_ORDER_SHA256
        and design.get("minimum_originally_finite_components")
        == MINIMUM_FINITE_COMPONENTS
        and numeric.get("numeric_source_factor_count") == NUMERIC_COUNT
        and numeric.get("numeric_source_factor_order_sha256")
        == NUMERIC_ORDER_SHA256
        and final.get("name") == c101.FACTOR_NAME
        and final.get("score_direction") == "higher"
        and final_manifest.get("sha256") == C101_MANIFEST_SHA256
        and final_manifest.get("dataset_sha256") == C101_DATASET_SHA256
        and c101_manifest.get("dataset_sha256") == C101_DATASET_SHA256
        and c101_manifest.get("rows") == EXPECTED_ROWS
        and c101_manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and len(c101_manifest.get("files") or []) == EXPECTED_PARTITIONS
    ):
        raise Campaign102DesignError("Campaign102 frozen input semantics changed")
    return protocol, catalog, c101_manifest


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign102DesignError("Campaign102 design implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign102_design_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign102_design_matrix_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("source_catalog") or {}).get("sha256")
        == SOURCE_CATALOG_SHA256
        and (record.get("design_builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("synthetic_tests") or {}).get("sha256")
        == _sha256(TEST_PATH)
        and record.get("campaign102_design_matrix_values_read_before_freeze") is False
        and record.get("historical_daily_price_or_return_values_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign102DesignError("Campaign102 implementation freeze changed")
    return record


def support_state(component_scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scores = np.asarray(component_scores)
    if scores.ndim != 2 or scores.shape[1] != NUMERIC_COUNT:
        raise Campaign102DesignError("Campaign102 component matrix shape changed")
    finite = np.isfinite(scores)
    if np.any((scores[finite] <= 0.0) | (scores[finite] > 1.0)):
        raise Campaign102DesignError("directional component escaped (0,1]")
    finite_count = finite.sum(axis=1).astype(np.uint8)
    eligible = finite_count >= MINIMUM_FINITE_COMPONENTS
    return finite_count, eligible


def model_matrix(component_scores: np.ndarray, eligible: np.ndarray) -> np.ndarray:
    scores = np.asarray(component_scores, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    if scores.ndim != 2 or support.shape != (len(scores),):
        raise Campaign102DesignError("Campaign102 model-matrix inputs changed")
    result = np.where(np.isfinite(scores), scores, 0.0)
    result[~support, :] = np.nan
    return result


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record["path"]))
    return raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()


def _verify_record(path: Path, expected: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign102DesignError(f"source partition changed: {path}")


def _verify_jobs(jobs: Iterable[tuple[Path, str]], workers: int) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_verify_record, path, digest) for path, digest in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def _source_manifests(
    old_catalog: dict[str, Any], workers: int
) -> list[tuple[dict[str, Any], Path, dict[str, Any]]]:
    result: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
    for source in old_catalog["post_cache_numeric_sources"]:
        manifest_path = Path(str(source["path"])).resolve()
        _require(manifest_path, str(source["sha256"]), f"{source['name']} manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("dataset_sha256") != source["dataset_sha256"]:
            raise Campaign102DesignError(f"{source['name']} dataset changed")
        jobs = []
        for record in manifest.get("files") or []:
            digest = str(record.get("sha256") or record.get("output_byte_sha256") or "")
            if len(digest) != 64:
                raise Campaign102DesignError(f"{source['name']} receipt is absent")
            jobs.append((_record_path(manifest_path, record), digest))
        _verify_jobs(jobs, workers)
        result.append((source, manifest_path, manifest))
    if len(result) != 31:
        raise Campaign102DesignError("Campaign102 post-cache source count changed")
    return result


def _load_campaign101_year(
    manifest: dict[str, Any], year: int, base_keys: np.ndarray
) -> np.ndarray:
    records = [item for item in manifest["files"] if int(item["year"]) == year]
    if len(records) != 1:
        raise Campaign102DesignError(f"Campaign101 year {year} changed")
    record = records[0]
    path = _record_path(C101_MANIFEST_PATH, record)
    _verify_record(path, str(record["sha256"]))
    frame = pd.read_parquet(path, columns=["stock_day_key", c101.FACTOR_NAME])
    keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
    values = pd.to_numeric(frame[c101.FACTOR_NAME], errors="coerce").to_numpy(
        dtype=np.float64
    )
    if not np.array_equal(keys, base_keys):
        raise Campaign102DesignError(f"Campaign101/base identity changed for {year}")
    return values


def _canonical_matrix_sha256(
    keys: np.ndarray,
    matrix: np.ndarray,
    finite_count: np.ndarray,
    eligible: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(keys, dtype="<i8").tobytes())
    canonical = np.asarray(matrix, dtype="<f4").copy(order="C")
    canonical[~np.isfinite(canonical)] = np.float32(np.nan)
    digest.update(canonical.tobytes(order="C"))
    digest.update(np.asarray(finite_count, dtype=np.uint8).tobytes())
    digest.update(np.asarray(eligible, dtype=np.uint8).tobytes())
    return digest.hexdigest()


def _write_partition(
    path: Path,
    keys: np.ndarray,
    matrix: np.ndarray,
    finite_count: np.ndarray,
    eligible: np.ndarray,
) -> None:
    columns: dict[str, Any] = {"stock_day_key": pa.array(keys, type=pa.int64())}
    for index, name in enumerate(component_columns()):
        columns[name] = pa.array(matrix[:, index], type=pa.float32(), from_pandas=True)
    columns[FINITE_COUNT_NAME] = pa.array(finite_count, type=pa.uint8())
    columns[ELIGIBLE_NAME] = pa.array(eligible, type=pa.bool_())
    pq.write_table(
        pa.Table.from_pydict(columns),
        path,
        compression="zstd",
        compression_level=6,
        use_dictionary=False,
        write_statistics=True,
        row_group_size=65_536,
        data_page_version="2.0",
    )


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign102_design_matrix"
        / OUTPUT_RUN_ID
    )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    if workers < 1 or workers > 16:
        raise Campaign102DesignError("--workers must be between 1 and 16")
    freeze = _load_implementation_freeze()
    _, _, c101_manifest = _load_frozen_inputs()
    _, old_catalog = c101.load_frozen_inputs()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign102DesignError("Campaign102 data root changed")
    final_root = output_root(data_root)
    if final_root.exists():
        raise Campaign102DesignError("Campaign102 design output already exists")
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise Campaign102DesignError("data root has less than 10 GiB free")

    cache_binding = old_catalog["first_98_numeric_sources"]["cache_manifest"]
    cache_manifest_path = Path(str(cache_binding["path"])).resolve()
    _require(cache_manifest_path, c101.CACHE_MANIFEST_SHA256, "compact cache")
    cache_manifest = json.loads(cache_manifest_path.read_text(encoding="utf-8"))
    if cache_manifest.get("dataset_sha256") != c101.CACHE_DATASET_SHA256:
        raise Campaign102DesignError("compact cache dataset changed")
    sources = _source_manifests(old_catalog, workers)
    first_definitions = [dict(item) for item in cache_v4._library_layout()["definitions"]]
    if len(first_definitions) != 98:
        raise Campaign102DesignError("first-98 layout changed")

    final_root.parent.mkdir(parents=True, exist_ok=True)
    partial_root = Path(tempfile.mkdtemp(prefix=f".{OUTPUT_RUN_ID}.", dir=final_root.parent))
    partition_root = partial_root / "partitions"
    partition_root.mkdir()
    records: list[dict[str, Any]] = []
    total_rows = total_eligible = 0
    sessions_seen: set[int] = set()
    try:
        for year in EXPECTED_YEARS:
            print(f"building Campaign102 design year={year}", flush=True)
            keys, logical, cache_receipt = c101._load_cache_year(
                cache_manifest_path, cache_manifest, year
            )
            sessions = keys // 4_000_000
            matrix = np.empty((len(keys), NUMERIC_COUNT), dtype=np.float32)
            for index, definition in enumerate(first_definitions):
                matrix[:, index] = c101._directional_percentile(
                    logical[str(definition["name"])],
                    sessions,
                    str(definition["score_direction"]),
                ).astype(np.float32)
            del logical
            for source, manifest_path, manifest in sources:
                index = int(source["ordinal"]) - 1
                raw = c101._load_post_source_year(
                    source=source,
                    manifest=manifest,
                    manifest_path=manifest_path,
                    year=year,
                    base_keys=keys,
                )
                matrix[:, index] = c101._directional_percentile(
                    raw, sessions, str(source["score_direction"])
                ).astype(np.float32)
                del raw
            c101_values = _load_campaign101_year(c101_manifest, year, keys)
            matrix[:, 129] = c101._directional_percentile(
                c101_values, sessions, "higher"
            ).astype(np.float32)
            del c101_values
            finite_count, eligible = support_state(matrix)
            path = partition_root / f"{year}.parquet"
            _write_partition(path, keys, matrix, finite_count, eligible)
            eligible_rows = int(eligible.sum())
            records.append(
                {
                    "year": year,
                    "path": f"partitions/{year}.parquet",
                    "rows": len(keys),
                    "eligible_rows": eligible_rows,
                    "sha256": _sha256(path),
                    "matrix_sha256": _canonical_matrix_sha256(
                        keys, matrix, finite_count, eligible
                    ),
                    "minimum_finite_components_observed": int(finite_count.min()),
                    "maximum_finite_components_observed": int(finite_count.max()),
                    "cache_source": cache_receipt,
                }
            )
            total_rows += len(keys)
            total_eligible += eligible_rows
            sessions_seen.update(sessions.tolist())
            del keys, sessions, matrix, finite_count, eligible
            gc.collect()
        if not (
            total_rows == EXPECTED_ROWS
            and len(records) == EXPECTED_PARTITIONS
            and len(sessions_seen) == EXPECTED_SESSIONS
        ):
            raise Campaign102DesignError("Campaign102 aggregate design base changed")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign102_design_matrix_snapshot",
            "status": "immutable_design_ready_for_no_return_structural_audit",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol": {"path": str(DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
            "source_catalog": {
                "path": str(DEFAULT_SOURCE_CATALOG),
                "sha256": SOURCE_CATALOG_SHA256,
            },
            "implementation_freeze": {
                "path": str(DEFAULT_IMPLEMENTATION_FREEZE),
                "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
                "design_builder_sha256": freeze["design_builder"]["sha256"],
                "synthetic_tests_sha256": freeze["synthetic_tests"]["sha256"],
            },
            "component_count": NUMERIC_COUNT,
            "component_order_sha256": NUMERIC_ORDER_SHA256,
            "components": reconstruct_numeric_sources(),
            "component_storage_dtype": "float32",
            "component_missingness_preserved": True,
            "model_missing_score_not_materialized": 0.0,
            "minimum_finite_components": MINIMUM_FINITE_COMPONENTS,
            "files": records,
            "partitions": len(records),
            "rows": total_rows,
            "eligible_rows": total_eligible,
            "calendar_sessions": len(sessions_seen),
            "dataset_sha256": _json_sha256(records),
            "campaign102_design_matrix_values_read": True,
            "model_fitting_performed": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued": False,
            "candidate49_historical_backfill_performed": False,
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


def _read_partition(
    manifest_path: Path, record: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    path = _record_path(manifest_path, record)
    _verify_record(path, str(record["sha256"]))
    names = list(component_columns())
    frame = pd.read_parquet(
        path, columns=["stock_day_key", *names, FINITE_COUNT_NAME, ELIGIBLE_NAME]
    )
    keys = frame.pop("stock_day_key").to_numpy(dtype=np.int64)
    finite_count = frame.pop(FINITE_COUNT_NAME).to_numpy(dtype=np.uint8)
    eligible = frame.pop(ELIGIBLE_NAME).to_numpy(dtype=bool)
    matrix = frame[names].to_numpy(dtype=np.float32, copy=True)
    return keys, matrix, finite_count, eligible


def verify_snapshot(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = list(manifest.get("files") or [])
    rows = eligible_rows = 0
    sessions: set[int] = set()
    for record in records:
        keys, matrix, finite_count, eligible = _read_partition(manifest_path, record)
        observed_count, observed_eligible = support_state(matrix)
        if not (
            np.array_equal(finite_count, observed_count)
            and np.array_equal(eligible, observed_eligible)
            and _canonical_matrix_sha256(keys, matrix, finite_count, eligible)
            == record["matrix_sha256"]
        ):
            raise Campaign102DesignError(
                f"Campaign102 partition semantics changed: {record['year']}"
            )
        rows += len(keys)
        eligible_rows += int(eligible.sum())
        sessions.update((keys // 4_000_000).tolist())
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign102_design_matrix_snapshot"
        and manifest.get("component_count") == NUMERIC_COUNT
        and manifest.get("component_order_sha256") == NUMERIC_ORDER_SHA256
        and manifest.get("components") == reconstruct_numeric_sources()
        and len(records) == manifest.get("partitions") == EXPECTED_PARTITIONS
        and rows == manifest.get("rows") == EXPECTED_ROWS
        and eligible_rows == manifest.get("eligible_rows")
        and len(sessions) == manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("dataset_sha256") == _json_sha256(records)
        and manifest.get("model_fitting_performed") is False
        and manifest.get("historical_forward_return_fields_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign102DesignError("Campaign102 snapshot verification changed")
    return {
        "status": "verified",
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(records),
        "rows": rows,
        "eligible_rows": eligible_rows,
        "calendar_sessions": len(sessions),
        "model_fitting_performed": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def structural_audit(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    verification = verify_snapshot(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_rows: list[dict[str, Any]] = []
    for record in manifest["files"]:
        path = _record_path(manifest_path, record)
        frame = pd.read_parquet(path, columns=["stock_day_key", ELIGIBLE_NAME])
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        sessions = keys // 4_000_000
        eligible = frame[ELIGIBLE_NAME].to_numpy(dtype=bool)
        local = pd.DataFrame({"session": sessions, "eligible": eligible})
        grouped = local.groupby("session", sort=True, observed=True)["eligible"].agg(
            ["size", "sum"]
        )
        for row in grouped.itertuples():
            daily_rows.append(
                {
                    "session": int(row.Index),
                    "quality_listing_names": int(row.size),
                    "eligible_names": int(row.sum),
                }
            )
    daily = pd.DataFrame(daily_rows).sort_values("session", kind="stable")
    if daily["session"].duplicated().any() or len(daily) != EXPECTED_SESSIONS:
        raise Campaign102DesignError("Campaign102 daily coverage identity changed")
    ratios = daily["eligible_names"] / daily["quality_listing_names"]
    indices = np.arange(0, max(len(daily) - 3, 0), 3)
    potential_mask = daily.iloc[indices]["eligible_names"].ge(50)
    potential = int(potential_mask.sum())
    cohort_sessions = daily.iloc[indices].loc[potential_mask, "session"].to_numpy(
        dtype=np.int64
    )
    cohort_years = sorted(
        pd.to_datetime(cohort_sessions, unit="D", origin="unix").year.unique().tolist()
    )
    median_coverage = float(ratios.median())
    p05_coverage = float(ratios.quantile(0.05))
    p05_names = float(daily["eligible_names"].quantile(0.05))
    passed = bool(
        median_coverage >= 0.95
        and p05_coverage >= 0.9
        and p05_names >= 50
        and potential >= 200
        and len(cohort_years) >= 5
    )
    daily_digest = hashlib.sha256(
        daily.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign102_design_structural_audit",
        "status": (
            "passed_ready_for_sequential_training_fit"
            if passed
            else "failed_terminal_before_model_fit_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": str(DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
        "snapshot": {
            "path": str(manifest_path),
            "sha256": _sha256(manifest_path),
            "dataset_sha256": manifest["dataset_sha256"],
        },
        "verification": verification,
        "coverage": {
            "quality_listing_rows": EXPECTED_ROWS,
            "eligible_rows": int(manifest["eligible_rows"]),
            "calendar_sessions": len(daily),
            "median_coverage": median_coverage,
            "p05_coverage": p05_coverage,
            "eligible_names_min": int(daily["eligible_names"].min()),
            "eligible_names_p05": p05_names,
            "eligible_names_median": float(daily["eligible_names"].median()),
            "potential_non_overlapping_three_session_cohorts": potential,
            "observed_cohort_years": [int(value) for value in cohort_years],
            "daily_coverage_frame_sha256": daily_digest,
            "gate_passed_before_model_fit_or_returns": passed,
        },
        "campaign102_design_matrix_values_read": True,
        "model_fitting_performed": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "provider_request_issued": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def status(*, data_root: Path) -> dict[str, Any]:
    root = output_root(data_root)
    return {
        "output_root": str(root),
        "published": (root / "snapshot_manifest.json").is_file(),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "campaign102_design_matrix_values_read_by_status": False,
        "model_fitting_performed_by_status": False,
        "historical_daily_price_or_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "build", "verify", "audit"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "status":
        payload: Any = status(data_root=args.data_root)
    elif args.command == "build":
        payload = {"manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    elif args.command == "verify":
        if args.manifest is None:
            raise Campaign102DesignError("--manifest is required")
        payload = verify_snapshot(args.manifest)
    else:
        if args.manifest is None or args.output is None:
            raise Campaign102DesignError("audit requires --manifest and --output")
        payload = structural_audit(args.manifest)
        _atomic_json(args.output.expanduser().resolve(), payload)
        payload = {"audit": str(args.output.expanduser().resolve()), "status": payload["status"]}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
