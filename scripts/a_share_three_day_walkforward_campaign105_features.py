#!/usr/bin/env python3
"""Build Campaign105's activity-clock occupancy snapshot without returns.

The builder reads only ``datetime,symbol,provider,volume,amount`` from the
immutable Tushare minute source and stock-day identity from the joint-clean
snapshot.  It never reads a price, comparator value, forward return, or
Candidate49 outcome.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign074_features as source
from scripts import a_share_three_day_walkforward_campaign102_design as c102
from scripts import a_share_three_day_walkforward_campaign103_features as c103


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_no_return_implementation_freeze_v2_20260808.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign105_features.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign105_no_return_audit.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign105_no_return_audit.py"
)

PROTOCOL_SHA256 = "73d7c65b2e531ec613d4baed38bab0b4b507294c2a889db318fc9eec9bb5f126"
MECHANISM_AUDIT_SHA256 = (
    "8e1069159f2f807a1f783aba2ad173e0a167b5c67441d76e5604116c88415d45"
)
NUMERIC_POLICY_SHA256 = (
    "3259f771039a2c3eb64c33b548fd9b198e6cd36f154cb8ab33a06ca91d495dfa"
)
NUMERIC_COMPARATOR_COUNT = 131
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "ab56a1791ae9a74b75d0a32cfb2346aa4bb6bfe266589be65825f8f51422f646"
)
COMPLETE_DEFINITION_COUNT = 134
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "db734b25fed4046ff80a276448daf20918d410125ebae941373c5617816cf8dc"
)

RAW_MANIFEST_RELATIVE = source.RAW_MANIFEST_RELATIVE
CLEAN_MANIFEST_RELATIVE = source.CLEAN_MANIFEST_RELATIVE
RAW_MANIFEST_SHA256 = source.RAW_MANIFEST_SHA256
CLEAN_MANIFEST_SHA256 = source.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = source.CLEAN_DATASET_SHA256
EXPECTED_PARTITIONS = source.EXPECTED_PARTITIONS
EXPECTED_ROWS = source.EXPECTED_ROWS
SOURCE_BAR_COUNT = source.SOURCE_BAR_COUNT
SELECTED_BAR_COUNT = source.SELECTED_BAR_COUNT
CONTINUOUS_MINUTE_CODES = source.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = source.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = source.SOURCE_MINUTE_CODE_SET

FACTOR_NAME = "intraday_active_trading_bar_share_240m"
FACTOR_FORMULA = (
    "count of exact 09:31-11:30 and 13:01-15:00 bars where volume and amount "
    "are both strictly positive, divided by 240; joint zero is valid inactive "
    "and one-sided zero makes the stock-day missing"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign105_feature_library_v1"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")
IDENTITY_COLUMNS = source.IDENTITY_COLUMNS
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)


class Campaign105FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign105 feature invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _json_digest([[item["name"], item["score_direction"]] for item in items])


def _require(path: Path, expected: str, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected:
        raise Campaign105FeatureError(f"Campaign105 {label} changed: {resolved}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    """Rebuild the exact v62 numeric order without reading comparator values."""

    items = [dict(item) for item in c102.reconstruct_numeric_sources()]
    items.append({"name": c103.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
        or items[-1] != {"name": c103.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign105FeatureError("Campaign105 numeric comparison order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the pre-value protocol without reading source or factor rows."""

    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign105FeatureError("Campaign105 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v62") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    activity = candidate.get("activity_semantics") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign105_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign105_minute_source_candidate_comparator_daily_price_or_return_values"
        and policy.get("sha256") == NUMERIC_POLICY_SHA256
        and policy.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and policy.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (inputs.get("mechanism_support_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and grid.get("accepted_rows_required") == SOURCE_BAR_COUNT
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and activity.get("finite_nonnegative_volume_and_amount_required") is True
        and activity.get("joint_zero") == "valid inactive bar"
        and activity.get("one_sided_zero") == "whole stock-day missing"
        and activity.get("joint_positive") == "active bar"
        and activity.get("minimum_active_bar_count") == 0
        and activity.get("positive_total_activity_required") is False
        and activity.get("activity_magnitude_used") is False
        and snapshot.get("data_root") == str(DEFAULT_DATA_ROOT)
        and snapshot.get("joint_clean_manifest_sha256") == CLEAN_MANIFEST_SHA256
        and snapshot.get("joint_clean_dataset_sha256") == CLEAN_DATASET_SHA256
        and snapshot.get("expected_partitions") == EXPECTED_PARTITIONS
        and snapshot.get("expected_rows") == EXPECTED_ROWS
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and boundary.get("campaign105_source_rows_read_before_freeze") is False
        and boundary.get("campaign105_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign105_comparison_values_read_before_freeze") is False
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign105FeatureError("Campaign105 protocol semantics changed")
    return spec


def extract_active_trading_bar_share(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate exact 241-row grids and compute the frozen 240-bar occupancy."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign105FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "active_trading_bar_share": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_activity_sessions": 0,
        "invalid_numeric_sessions": 0,
        "one_sided_zero_sessions": 0,
        "active_bars": 0,
        "joint_zero_bars": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["volume"] = pd.to_numeric(work["volume"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign105FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign105FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "volume", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign105FeatureError(f"continuous minute grid changed for {symbol}")
    volume = (
        selected["volume"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    amount = (
        selected["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    numeric_valid = (
        np.isfinite(volume).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (volume >= 0.0).all(axis=1)
        & (amount >= 0.0).all(axis=1)
    )
    one_sided = (volume == 0.0) ^ (amount == 0.0)
    zero_equivalent = ~one_sided.any(axis=1)
    valid = numeric_valid & zero_equivalent
    active = (volume > 0.0) & (amount > 0.0)
    joint_zero = (volume == 0.0) & (amount == 0.0)
    scores = np.full(len(dates), np.nan, dtype=np.float64)
    active_counts = active.sum(axis=1, dtype=np.int16)
    scores[valid] = active_counts[valid].astype(np.float64) / SELECTED_BAR_COUNT
    range_valid = np.isfinite(scores) & (scores >= 0.0) & (scores <= 1.0)
    scores[~range_valid] = np.nan
    return pd.DataFrame({"trade_date": dates, "active_trading_bar_share": scores}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_activity_sessions": int(range_valid.sum()),
        "invalid_numeric_sessions": int((~numeric_valid).sum()),
        "one_sided_zero_sessions": int((numeric_valid & ~zero_equivalent).sum()),
        "active_bars": int(active[valid].sum()),
        "joint_zero_bars": int(joint_zero[valid].sum()),
    }


def attach_activity_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign105FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["active_trading_bar_share"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
        or values.empty
        or values.duplicated(["trade_date"]).any()
    ):
        raise Campaign105FeatureError(f"stock-day identity changed for {symbol}")
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    source_dates = set(values["trade_date"].tolist())
    if any(date not in source_dates for date in out["trade_date"]):
        raise Campaign105FeatureError(
            f"accepted session absent from source for {symbol}"
        )
    return out


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "active_trading_bar_share")
    if not set(required).issubset(frame.columns):
        raise Campaign105FeatureError("Campaign105 input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work["active_trading_bar_share"], errors="coerce")
    eligible = np.isfinite(values) & values.ge(0.0) & values.le(1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "tushare"
    return work


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign105FeatureError("Campaign105 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    scaled = values[eligible] * SELECTED_BAR_COUNT
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-12)
        or values[~eligible].notna().any()
    ):
        raise Campaign105FeatureError("Campaign105 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign105_feature_library"
        / OUTPUT_RUN_ID
    )


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign105FeatureError("Campaign105 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    tests = record.get("synthetic_tests") or []
    expected_tests = {
        str(FEATURE_TEST_PATH.relative_to(REPO_ROOT)): _sha256(FEATURE_TEST_PATH),
        str(AUDIT_TEST_PATH.relative_to(REPO_ROOT)): _sha256(AUDIT_TEST_PATH),
    }
    observed_tests = {str(item.get("path")): str(item.get("sha256")) for item in tests}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign105_no_return_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign105_minute_source_candidate_coverage_or_comparator_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("ordered_audit_runner") or {}).get("sha256")
        == _sha256(AUDIT_RUNNER_PATH)
        and observed_tests == expected_tests
        and record.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (record.get("research_boundary") or {}).get(
            "candidate_source_rows_read_before_freeze"
        )
        is False
        and (record.get("research_boundary") or {}).get(
            "candidate_or_comparator_values_read_before_freeze"
        )
        is False
        and (record.get("research_boundary") or {}).get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and (record.get("research_boundary") or {}).get(
            "provider_request_issued_before_freeze"
        )
        is False
    ):
        raise Campaign105FeatureError("Campaign105 implementation freeze changed")
    return record


def _require_inputs(
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    load_protocol()
    freeze = _validate_implementation_freeze()
    raw_path = data_root / RAW_MANIFEST_RELATIVE
    clean_path = data_root / CLEAN_MANIFEST_RELATIVE
    _require(raw_path, RAW_MANIFEST_SHA256, "raw minute manifest")
    _require(clean_path, CLEAN_MANIFEST_SHA256, "joint-clean manifest")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    if not (
        len(raw.get("files") or []) == EXPECTED_PARTITIONS
        and len(clean.get("files") or []) == EXPECTED_PARTITIONS
        and clean.get("dataset_sha256") == CLEAN_DATASET_SHA256
        and clean.get("rows") == EXPECTED_ROWS
        and clean.get("partitions") == EXPECTED_PARTITIONS
    ):
        raise Campaign105FeatureError("Campaign105 source aggregate changed")
    return raw, clean, freeze


def _raw_file_map(raw: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for item in raw.get("files") or []:
        key = (str(item["symbol"]).upper(), int(item["year"]))
        if key in result:
            raise Campaign105FeatureError(f"duplicate raw partition: {key}")
        result[key] = item
    if len(result) != EXPECTED_PARTITIONS:
        raise Campaign105FeatureError("raw partition count changed")
    return result


def _load_attached(
    index: int, clean_item: dict[str, Any], raw_item: dict[str, Any]
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    clean_path = Path(str(clean_item["path"])).expanduser().resolve()
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if (
        not clean_path.is_file()
        or pq.ParquetFile(clean_path).metadata.num_rows != int(clean_item["rows"])
        or not raw_path.is_file()
        or pq.ParquetFile(raw_path).metadata.num_rows != int(raw_item["rows"])
    ):
        raise Campaign105FeatureError(f"source partition changed for {symbol}")
    identity = pd.read_parquet(clean_path, columns=list(IDENTITY_COLUMNS))
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_active_trading_bar_share(raw, symbol=symbol)
    out = attach_activity_values(identity, values, symbol=symbol)
    out["_partition_index"] = index
    return index, out, quality


def build_snapshot(
    *, data_root: Path, workers: int = 4, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign105FeatureError("Campaign105 build requires --confirm-build")
    if workers < 1 or workers > 16:
        raise Campaign105FeatureError("--workers must be between 1 and 16")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign105FeatureError("Campaign105 data root changed")
    raw, clean, freeze = _require_inputs(data_root)
    raw_by_key = _raw_file_map(raw)
    files = list(clean.get("files") or [])
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    final_root = output_root(data_root)
    if final_root.exists():
        raise Campaign105FeatureError("Campaign105 snapshot already exists; verify it")
    final_root.parent.mkdir(parents=True, exist_ok=True)
    partial_root = Path(
        tempfile.mkdtemp(prefix=f".{OUTPUT_RUN_ID}.", dir=final_root.parent)
    )
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {
        "eligible": 0,
        "missing": 0,
        "source_rows": 0,
        "source_sessions": 0,
        "invalid_numeric_sessions": 0,
        "one_sided_zero_sessions": 0,
        "active_bars": 0,
        "joint_zero_bars": 0,
    }
    try:
        for year in sorted(by_year):
            jobs = []
            for index, item in by_year[year]:
                key = (str(item["symbol"]).upper(), int(item["year"]))
                raw_item = raw_by_key.get(key)
                if raw_item is None:
                    raise Campaign105FeatureError(f"raw partition missing: {key}")
                jobs.append((index, item, raw_item))
            pieces: list[pd.DataFrame] = []
            quality_by_index: dict[int, dict[str, int]] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_load_attached, *job) for job in jobs]
                for future in concurrent.futures.as_completed(futures):
                    index, attached, quality = future.result()
                    pieces.append(attached)
                    quality_by_index[index] = quality
                    for key in totals:
                        if key not in {"eligible", "missing"}:
                            totals[key] += quality[key]
            if not pieces:
                raise Campaign105FeatureError(f"Campaign105 year {year} is empty")
            year_frame = finalize_feature_frame(pd.concat(pieces, ignore_index=True))
            grouped = {
                int(index): group
                for index, group in year_frame.groupby("_partition_index", sort=False)
            }
            for index, item in by_year[year]:
                group = grouped.get(index)
                out = (
                    empty_output_frame()
                    if group is None
                    else group.loc[:, OUTPUT_COLUMNS]
                    .sort_values("trade_date", kind="stable")
                    .reset_index(drop=True)
                )
                validate_value_semantics(out)
                relative = (
                    Path("partitions")
                    / str(item["symbol"]).lower()
                    / f"{int(item['year'])}.parquet"
                )
                partial_path = partial_root / relative
                source._atomic_parquet(out, partial_path)
                eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
                missing = int(len(out) - eligible)
                totals["eligible"] += eligible
                totals["missing"] += missing
                raw_item = raw_by_key[(str(item["symbol"]).upper(), int(item["year"]))]
                records[index] = {
                    "schema_version": 1,
                    "kind": "a_share_three_day_walkforward_campaign105_feature_partition",
                    "status": "complete_pending_aggregate_publication",
                    "path": str((final_root / relative).resolve()),
                    "relative_path": str(relative),
                    "symbol": str(item["symbol"]),
                    "code": str(item["code"]),
                    "year": int(item["year"]),
                    "rows": int(len(out)),
                    "output_byte_sha256": _sha256(partial_path),
                    "output_frame_sha256": source._frame_sha256(out),
                    "joint_clean_path": str(item["path"]),
                    "joint_clean_byte_sha256": str(item["output_byte_sha256"]),
                    "raw_source_path": str(raw_item["path"]),
                    "raw_source_manifest_byte_sha256": str(raw_item["byte_sha256"]),
                    "raw_source_rows": int(raw_item["rows"]),
                    "source_fields_read": list(RAW_COLUMNS),
                    "factor_eligible_rows": {FACTOR_NAME: eligible},
                    "quality": {
                        "base_rows": int(len(out)),
                        f"{FACTOR_NAME}__eligible_rows": eligible,
                        f"{FACTOR_NAME}__missing_rows": missing,
                        **quality_by_index[index],
                    },
                    "protocol_sha256": PROTOCOL_SHA256,
                    "implementation_freeze_sha256": _sha256(
                        DEFAULT_IMPLEMENTATION_FREEZE
                    ),
                    "daily_price_fields_read": [],
                    "forward_return_fields_read": False,
                    "comparison_factor_values_read": False,
                    "provider_request_issued": False,
                }
            print(
                f"Campaign105 built year={year} partitions={len(by_year[year])} "
                f"eligible_rows={totals['eligible']}",
                flush=True,
            )
        completed = [record for record in records if record is not None]
        if (
            len(completed) != EXPECTED_PARTITIONS
            or sum(int(record["rows"]) for record in completed) != EXPECTED_ROWS
            or totals["eligible"] + totals["missing"] != EXPECTED_ROWS
        ):
            raise Campaign105FeatureError("Campaign105 publication totals changed")
        digest_rows = [
            [
                record["relative_path"],
                record["output_byte_sha256"],
                record["output_frame_sha256"],
                record["rows"],
            ]
            for record in completed
        ]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign105_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "output_run_id": OUTPUT_RUN_ID,
            "dataset_sha256": _json_digest(digest_rows),
            "partitions": EXPECTED_PARTITIONS,
            "rows": EXPECTED_ROWS,
            "files": completed,
            "factor_names": [FACTOR_NAME],
            "factor_directions": {FACTOR_NAME: "higher"},
            "factor_ranges": {FACTOR_NAME: [0.0, 1.0]},
            "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
            "factor_eligible_rows": {FACTOR_NAME: totals["eligible"]},
            "quality": {
                "base_rows": EXPECTED_ROWS,
                f"{FACTOR_NAME}__eligible_rows": totals["eligible"],
                f"{FACTOR_NAME}__missing_rows": totals["missing"],
                "raw_source_rows_read": totals["source_rows"],
                "raw_source_sessions": totals["source_sessions"],
                "invalid_numeric_sessions": totals["invalid_numeric_sessions"],
                "one_sided_zero_sessions": totals["one_sided_zero_sessions"],
                "active_bars": totals["active_bars"],
                "joint_zero_bars": totals["joint_zero_bars"],
            },
            "source_fields_read": list(RAW_COLUMNS),
            "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
            "source_rows_required_per_session": SOURCE_BAR_COUNT,
            "source_selected_bar_count": SELECTED_BAR_COUNT,
            "source_minute_grid": (
                "09:30 plus 09:31-11:30 and 13:01-15:00; formula excludes 09:30"
            ),
            "activity_rule": FACTOR_FORMULA,
            "minimum_active_bar_count": 0,
            "positive_total_activity_required": False,
            "activity_magnitude_used": False,
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_clean_manifest_sha256": CLEAN_MANIFEST_SHA256,
            "joint_clean_dataset_sha256": CLEAN_DATASET_SHA256,
            "protocol_sha256": PROTOCOL_SHA256,
            "mechanism_support_audit_sha256": MECHANISM_AUDIT_SHA256,
            "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
            "implementation_freeze_status": freeze.get("status"),
            "partition_checkpoint_reuse_performed": False,
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "comparison_factor_values_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "prospective_candidate_activation_created": False,
            "provider_request_issued": False,
        }
        manifest_path = partial_root / "snapshot_manifest.json"
        source._atomic_json(manifest, manifest_path)
        os.replace(partial_root, final_root)
        return final_root / "snapshot_manifest.json"
    except BaseException:
        shutil.rmtree(partial_root, ignore_errors=True)
        raise


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign105_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("partitions") == len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("factor_formulas") == {FACTOR_NAME: FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read") == list(IDENTITY_COLUMNS)
        and manifest.get("source_rows_required_per_session") == SOURCE_BAR_COUNT
        and manifest.get("source_selected_bar_count") == SELECTED_BAR_COUNT
        and manifest.get("minimum_active_bar_count") == 0
        and manifest.get("positive_total_activity_required") is False
        and manifest.get("activity_magnitude_used") is False
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_clean_manifest_sha256") == CLEAN_MANIFEST_SHA256
        and manifest.get("joint_clean_dataset_sha256") == CLEAN_DATASET_SHA256
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_support_audit_sha256") == MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and quality.get(f"{FACTOR_NAME}__missing_rows") == EXPECTED_ROWS - eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign105FeatureError("Campaign105 manifest semantics changed")


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign105FeatureError("Campaign105 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign105FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if (
            len(frame) != item["rows"]
            or source._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign105FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verified = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    expected_eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if (
        _json_digest(digest_rows) != manifest["dataset_sha256"]
        or len(verified) != EXPECTED_PARTITIONS
        or sum(rows for rows, _eligible in verified) != EXPECTED_ROWS
        or sum(eligible for _rows, eligible in verified) != expected_eligible
    ):
        raise Campaign105FeatureError("Campaign105 aggregate identity changed")
    return {
        "status": "verified",
        "manifest_sha256": _sha256(manifest_path),
        "partitions": len(verified),
        "rows": sum(rows for rows, _eligible in verified),
        "eligible_rows": sum(eligible for _rows, eligible in verified),
        "dataset_sha256": manifest["dataset_sha256"],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_prebuild",
        "snapshot_manifest": str(path),
        "source_fields_read_by_status": [],
        "candidate_or_comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {
            "snapshot_manifest": str(
                build_snapshot(
                    data_root=args.data_root,
                    workers=args.workers,
                    confirm_build=args.confirm_build,
                )
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
