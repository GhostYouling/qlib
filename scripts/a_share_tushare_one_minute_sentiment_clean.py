#!/usr/bin/env python3
"""Build a non-destructive Tushare one-minute sentiment-feature layer.

The command is deliberately separate from ``a_share_rich_data.py`` because the
original full-source protocol is terminally failed and immutable.  This cleaner
implements the separately frozen, no-return sentiment cleaning protocol only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_one_minute_sentiment_cleaning_protocol.json"
)
PROTOCOL_SHA256 = "f70c7da688ecb6d2e88cd86f4ec086a42b620e0c12025ee9263fe603abe3a2fe"
SOURCE_AUDIT_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_one_minute_full_source_coverage_audit.json"
)
SOURCE_AUDIT_SHA256 = "5626c0f6523eeadd7739266f29a133b4e66852b1af0aebf84ef00ad88dadbfec"
SOURCE_MANIFEST_SHA256 = (
    "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
)
SOURCE_RUN_ID = "tushare_stk_mins_1m_2019_2025_ea0cbb8f"
OUTPUT_VERSION = "sentiment_clean_v1"
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_{OUTPUT_VERSION}"
FIELDWISE_PROTOCOL_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_one_minute_fieldwise_cleaning_protocol.json"
)
FIELDWISE_PROTOCOL_SHA256 = (
    "51e4fbf399411f62d35cbdb81d78651b4ceab17934264db0146cef61554d2fd6"
)
JOINT_RESULT_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_one_minute_sentiment_cleaning_result.json"
)
JOINT_RESULT_SHA256 = (
    "2bd511045a1c9bc8a2b8d3bc566d4c0219c5764e8f1ae02c559125c99c6a4275"
)
JOINT_MANIFEST_SHA256 = (
    "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
)
FIELDWISE_OUTPUT_VERSION = "fieldwise_clean_v2"
FIELDWISE_OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_{FIELDWISE_OUTPUT_VERSION}"
REQUIRED_DAILY_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
REQUIRED_COLUMNS = frozenset(
    {
        "datetime",
        "symbol",
        "provider",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    }
)
FEATURE_COLUMNS = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "intraday_realized_volatility",
)
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    "opening_row_role",
    "source_minute_bars",
    "canonical_bars",
    "close_relative_error",
    "amount_ratio_to_local_daily",
    "volume_ratio_to_local_daily",
    *FEATURE_COLUMNS,
    "sentiment_feature_eligible",
)
FIELDWISE_ELIGIBILITY_COLUMNS = tuple(
    f"{feature}_eligible" for feature in FEATURE_COLUMNS
)
FIELDWISE_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    "opening_row_role",
    "source_minute_bars",
    "canonical_bars",
    "close_relative_error",
    "amount_ratio_to_local_daily",
    "volume_ratio_to_local_daily",
    *FEATURE_COLUMNS,
    *FIELDWISE_ELIGIBILITY_COLUMNS,
)


class CleaningError(RuntimeError):
    """Raised when a frozen cleaning or integrity contract is violated."""


def file_digest(path: Path) -> str:
    """Return a canonical-text or byte-exact SHA-256 digest."""

    path = Path(path)
    digest = hashlib.sha256()
    if path.suffix.lower() in {
        ".csv",
        ".json",
        ".md",
        ".rst",
        ".tsv",
        ".txt",
        ".yaml",
        ".yml",
    }:
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        return digest.hexdigest()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_digest(frame: pd.DataFrame) -> str:
    """Return the repository's stable stored-frame digest."""

    content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        suffix=".json",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".parquet", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def expected_canonical_times() -> tuple[dt.time, ...]:
    anchor = pd.Timestamp("2000-01-03")
    values = [
        *pd.date_range(
            anchor + pd.Timedelta(hours=9, minutes=31), periods=120, freq="1min"
        ),
        *pd.date_range(
            anchor + pd.Timedelta(hours=13, minutes=1), periods=120, freq="1min"
        ),
    ]
    return tuple(value.time() for value in values)


def expected_source_times() -> tuple[dt.time, ...]:
    return (dt.time(9, 30), *expected_canonical_times())


def minute_code(value: dt.time) -> int:
    return value.hour * 60 + value.minute


SOURCE_MINUTE_CODES = np.asarray(
    [minute_code(value) for value in expected_source_times()], dtype=np.int16
)
SOURCE_MINUTE_CODE_SET = frozenset(int(value) for value in SOURCE_MINUTE_CODES)
CANONICAL_MINUTE_CODES = SOURCE_MINUTE_CODES[1:]
LATE_START_INDEX = int(np.flatnonzero(CANONICAL_MINUTE_CODES == 14 * 60 + 30)[0])


def empty_output_frame() -> pd.DataFrame:
    """Return a typed empty daily sentiment frame."""

    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            "opening_row_role": pd.Series(dtype="object"),
            "source_minute_bars": pd.Series(dtype="int16"),
            "canonical_bars": pd.Series(dtype="int16"),
            "close_relative_error": pd.Series(dtype="float64"),
            "amount_ratio_to_local_daily": pd.Series(dtype="float64"),
            "volume_ratio_to_local_daily": pd.Series(dtype="float64"),
            "late_return_30m": pd.Series(dtype="float64"),
            "late_amount_share_30m": pd.Series(dtype="float64"),
            "late_vwap_to_day_vwap_30m": pd.Series(dtype="float64"),
            "intraday_realized_volatility": pd.Series(dtype="float64"),
            "sentiment_feature_eligible": pd.Series(dtype="bool"),
        }
    )


def _validate_identity(frame: pd.DataFrame, symbol: str) -> None:
    if missing := sorted(REQUIRED_COLUMNS - set(frame.columns)):
        raise CleaningError("source partition is missing columns: " + ", ".join(missing))
    if frame.empty:
        return
    if frame[["symbol", "provider"]].isna().any().any():
        raise CleaningError(f"source identity contains null values for {symbol}")
    symbols = set(frame["symbol"].astype(str).str.upper())
    providers = set(frame["provider"].astype(str).str.lower())
    if symbols != {symbol.upper()}:
        raise CleaningError(f"source identity mismatch for {symbol}: {sorted(symbols)}")
    if providers != {"tushare"}:
        raise CleaningError(f"source provider mismatch for {symbol}: {sorted(providers)}")


def prepare_daily_reconciliation(daily: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Validate and index only the three allowed local daily fields."""

    required = {"date", "raw_close", "raw_volume", "amount", "price_basis"}
    if missing := sorted(required - set(daily.columns)):
        raise CleaningError("local daily history is missing columns: " + ", ".join(missing))
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        raise CleaningError(
            f"local daily price basis is rejected for {symbol}: {sorted(bases)}"
        )
    work = daily[["date", "raw_close", "raw_volume", "amount"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    for column in ("raw_close", "raw_volume", "amount"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work = (
        work.dropna(subset=["date"])
        .sort_values("date", kind="stable")
        .drop_duplicates("date", keep="last")
        .set_index("date")
    )
    return work


def clean_partition_frame(
    frame: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean one symbol-year in memory without reading returns or other factors."""

    _validate_identity(frame, symbol)
    if frame.empty:
        quality = {
            "observed_sessions": 0,
            "exact_source_grid_sessions": 0,
            "incomplete_or_off_grid_sessions": 0,
            "invalid_numeric_sessions": 0,
            "nonpositive_activity_sessions": 0,
            "missing_local_daily_sessions": 0,
            "close_reconciliation_failed_sessions": 0,
            "amount_reconciliation_failed_sessions": 0,
            "volume_reconciliation_failed_sessions": 0,
            "nonfinite_feature_sessions": 0,
            "eligible_sessions": 0,
            "eligible_reference_placeholder_sessions": 0,
            "eligible_active_auction_sessions": 0,
        }
        return empty_output_frame(), quality

    work = frame[list(REQUIRED_COLUMNS)].copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    if work["datetime"].isna().any():
        raise CleaningError(f"source partition contains invalid timestamps for {symbol}")
    work = work.sort_values("datetime", kind="stable").reset_index(drop=True)
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    ).astype(np.int16)
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    numeric = work[numeric_columns].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    prices_positive = (numeric[["open", "high", "low", "close"]] > 0.0).all(
        axis=1
    )
    activity_nonnegative = (numeric[["volume", "amount"]] >= 0.0).all(axis=1)
    envelope_valid = (
        numeric["high"] >= numeric[["open", "close"]].max(axis=1)
    ) & (numeric["low"] <= numeric[["open", "close"]].min(axis=1))
    work[numeric_columns] = numeric
    work["row_numeric_valid"] = (
        finite & prices_positive & activity_nonnegative & envelope_valid
    )
    work["row_on_source_grid"] = (
        work["minute_code"].isin(SOURCE_MINUTE_CODE_SET)
        & work["datetime"].dt.second.eq(0)
        & work["datetime"].dt.microsecond.eq(0)
    )

    grouped = work.groupby("trade_date", sort=True, observed=True)
    stats = grouped.agg(
        row_count=("datetime", "size"),
        unique_times=("minute_code", "nunique"),
        on_grid_rows=("row_on_source_grid", "sum"),
        valid_numeric_rows=("row_numeric_valid", "sum"),
    )
    exact_mask = (
        (stats["row_count"] == 241)
        & (stats["unique_times"] == 241)
        & (stats["on_grid_rows"] == 241)
    )
    exact_dates = pd.DatetimeIndex(stats.index[exact_mask])
    quality: dict[str, Any] = {
        "observed_sessions": int(len(stats)),
        "exact_source_grid_sessions": int(exact_mask.sum()),
        "incomplete_or_off_grid_sessions": int((~exact_mask).sum()),
        "invalid_numeric_sessions": 0,
        "nonpositive_activity_sessions": 0,
        "missing_local_daily_sessions": 0,
        "close_reconciliation_failed_sessions": 0,
        "amount_reconciliation_failed_sessions": 0,
        "volume_reconciliation_failed_sessions": 0,
        "nonfinite_feature_sessions": 0,
        "eligible_sessions": 0,
        "eligible_reference_placeholder_sessions": 0,
        "eligible_active_auction_sessions": 0,
    }
    if not len(exact_dates):
        return empty_output_frame(), quality

    exact = work[work["trade_date"].isin(exact_dates)].copy()
    exact = exact.sort_values(["trade_date", "datetime"], kind="stable")
    codes = exact["minute_code"].to_numpy().reshape(-1, 241)
    if not np.array_equal(codes, np.broadcast_to(SOURCE_MINUTE_CODES, codes.shape)):
        raise CleaningError("exact-grid vectorization invariant failed")
    dates = pd.DatetimeIndex(exact["trade_date"].to_numpy()[::241])
    values = {
        column: exact[column].to_numpy(dtype=float).reshape(-1, 241)
        for column in numeric_columns
    }
    numeric_valid = exact["row_numeric_valid"].to_numpy().reshape(-1, 241).all(axis=1)
    quality["invalid_numeric_sessions"] = int((~numeric_valid).sum())

    source_volume = values["volume"].sum(axis=1)
    source_amount = values["amount"].sum(axis=1)
    positive_activity = (source_volume > 0.0) & (source_amount > 0.0)
    quality["nonpositive_activity_sessions"] = int((~positive_activity).sum())
    opening_placeholder = (values["volume"][:, 0] == 0.0) & (
        values["amount"][:, 0] == 0.0
    )

    canonical_close = values["close"][:, 1:]
    canonical_volume = values["volume"][:, 1:].copy()
    canonical_amount = values["amount"][:, 1:].copy()
    active_opening = ~opening_placeholder
    canonical_volume[active_opening, 0] += values["volume"][active_opening, 0]
    canonical_amount[active_opening, 0] += values["amount"][active_opening, 0]
    if canonical_close.shape[1] != 240:
        raise CleaningError("canonical grid does not contain exactly 240 bars")

    daily_indexed = prepare_daily_reconciliation(daily, symbol)
    aligned = daily_indexed.reindex(dates)
    daily_close = aligned["raw_close"].to_numpy(dtype=float)
    daily_volume = aligned["raw_volume"].to_numpy(dtype=float)
    daily_amount = aligned["amount"].to_numpy(dtype=float)
    daily_present = (
        np.isfinite(daily_close)
        & np.isfinite(daily_volume)
        & np.isfinite(daily_amount)
        & (daily_close > 0.0)
        & (daily_volume > 0.0)
        & (daily_amount > 0.0)
    )
    quality["missing_local_daily_sessions"] = int((~daily_present).sum())

    with np.errstate(divide="ignore", invalid="ignore"):
        close_error = np.abs(canonical_close[:, -1] - daily_close) / np.abs(
            daily_close
        )
        amount_ratio = source_amount / daily_amount
        volume_ratio = source_volume / daily_volume
    close_pass = daily_present & np.isfinite(close_error) & (close_error <= 0.002)
    amount_pass = (
        daily_present
        & np.isfinite(amount_ratio)
        & (np.abs(amount_ratio - 1.0) <= 0.005)
    )
    volume_pass = (
        daily_present
        & np.isfinite(volume_ratio)
        & (np.abs(volume_ratio - 100.0) <= 0.005)
    )
    quality["close_reconciliation_failed_sessions"] = int(
        (daily_present & ~close_pass).sum()
    )
    quality["amount_reconciliation_failed_sessions"] = int(
        (daily_present & ~amount_pass).sum()
    )
    quality["volume_reconciliation_failed_sessions"] = int(
        (daily_present & ~volume_pass).sum()
    )

    base_eligible = (
        numeric_valid
        & positive_activity
        & daily_present
        & close_pass
        & amount_pass
        & volume_pass
    )
    late_close = canonical_close[:, LATE_START_INDEX]
    late_amount = canonical_amount[:, LATE_START_INDEX + 1 :].sum(axis=1)
    late_volume = canonical_volume[:, LATE_START_INDEX + 1 :].sum(axis=1)
    day_amount = canonical_amount.sum(axis=1)
    day_volume = canonical_volume.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        late_return = canonical_close[:, -1] / late_close - 1.0
        late_amount_share = late_amount / day_amount
        late_vwap_to_day_vwap = (
            (late_amount / late_volume) / (day_amount / day_volume) - 1.0
        )
        realized_volatility = np.sqrt(
            np.square(np.diff(np.log(canonical_close), axis=1)).sum(axis=1)
        )
    feature_matrix = np.column_stack(
        [
            late_return,
            late_amount_share,
            late_vwap_to_day_vwap,
            realized_volatility,
        ]
    )
    feature_finite = np.isfinite(feature_matrix).all(axis=1)
    quality["nonfinite_feature_sessions"] = int(
        (base_eligible & ~feature_finite).sum()
    )
    eligible = base_eligible & feature_finite
    quality["eligible_sessions"] = int(eligible.sum())
    quality["eligible_reference_placeholder_sessions"] = int(
        (eligible & opening_placeholder).sum()
    )
    quality["eligible_active_auction_sessions"] = int(
        (eligible & ~opening_placeholder).sum()
    )

    if not eligible.any():
        return empty_output_frame(), quality
    result = pd.DataFrame(
        {
            "trade_date": dates[eligible],
            "symbol": symbol.upper(),
            "provider": "tushare",
            "opening_row_role": np.where(
                opening_placeholder[eligible], "reference_placeholder", "active_auction"
            ),
            "source_minute_bars": np.int16(241),
            "canonical_bars": np.int16(240),
            "close_relative_error": close_error[eligible],
            "amount_ratio_to_local_daily": amount_ratio[eligible],
            "volume_ratio_to_local_daily": volume_ratio[eligible],
            "late_return_30m": late_return[eligible],
            "late_amount_share_30m": late_amount_share[eligible],
            "late_vwap_to_day_vwap_30m": late_vwap_to_day_vwap[eligible],
            "intraday_realized_volatility": realized_volatility[eligible],
            "sentiment_feature_eligible": True,
        }
    )
    return result.loc[:, OUTPUT_COLUMNS], quality


@dataclass(frozen=True)
class OutputPaths:
    partial_data: Path
    partial_sidecar: Path
    final_data: Path
    final_sidecar: Path


def output_paths(
    partial_root: Path, final_root: Path, source_record: dict[str, Any]
) -> OutputPaths:
    source_path = Path(str(source_record["path"]))
    relative = Path(source_path.parent.name) / source_path.name
    metadata_relative = Path(source_path.parent.name) / f"{source_path.stem}.json"
    return OutputPaths(
        partial_data=partial_root / "partitions" / relative,
        partial_sidecar=partial_root / ".metadata" / "partitions" / metadata_relative,
        final_data=final_root / "partitions" / relative,
        final_sidecar=final_root / ".metadata" / "partitions" / metadata_relative,
    )


def load_completed_partition(
    source_record: dict[str, Any], paths: OutputPaths, daily_sha256: str
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    source_path = Path(str(source_record["path"]))
    valid = (
        record.get("kind") == "a_share_tushare_one_minute_sentiment_clean_partition"
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("source_manifest_sha256") == SOURCE_MANIFEST_SHA256
        and record.get("source_byte_sha256") == source_record.get("byte_sha256")
        and record.get("daily_byte_sha256") == daily_sha256
        and paths.partial_data.is_file()
        and file_digest(source_path) == source_record.get("byte_sha256")
        and file_digest(paths.partial_data) == record.get("output_byte_sha256")
    )
    if not valid:
        raise CleaningError(f"completed cleaning checkpoint changed: {paths.partial_sidecar}")
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or frame_digest(output) != record.get(
        "output_frame_sha256"
    ):
        raise CleaningError(f"completed cleaning frame changed: {paths.partial_data}")
    dates = Counter(
        pd.to_datetime(output["trade_date"]).dt.strftime("%Y-%m-%d").tolist()
    )
    return record, dates


def clean_source_partition(
    source_record: dict[str, Any],
    *,
    partial_root: Path,
    final_root: Path,
    daily: pd.DataFrame,
    daily_sha256: str,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = output_paths(partial_root, final_root, source_record)
    completed = load_completed_partition(source_record, paths, daily_sha256)
    if completed is not None:
        record, dates = completed
        return record, dates, True

    source_path = Path(str(source_record["path"]))
    observed_source_hash = file_digest(source_path)
    if observed_source_hash != source_record.get("byte_sha256"):
        raise CleaningError(f"source partition byte hash changed: {source_path}")
    frame = pd.read_parquet(source_path)
    if len(frame) != int(source_record.get("rows", -1)):
        raise CleaningError(f"source partition row count changed: {source_path}")
    output, quality = clean_partition_frame(
        frame, daily, symbol=str(source_record["symbol"])
    )
    atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_one_minute_sentiment_clean_partition",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_run_id": SOURCE_RUN_ID,
        "output_run_id": OUTPUT_RUN_ID,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "symbol": str(source_record["symbol"]),
        "code": str(source_record["code"]),
        "year": int(source_record["year"]),
        "source_path": str(source_path),
        "source_rows": int(source_record["rows"]),
        "source_byte_sha256": str(source_record["byte_sha256"]),
        "source_frame_sha256": str(source_record["frame_sha256"]),
        "daily_byte_sha256": daily_sha256,
        "path": str(paths.final_data),
        "sidecar_path": str(paths.final_sidecar),
        "rows": int(len(output)),
        "output_byte_sha256": file_digest(paths.partial_data),
        "output_frame_sha256": frame_digest(output),
        "quality": quality,
        "opening_price_or_extrema_used_by_retained_features": False,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    atomic_write_json(record, paths.partial_sidecar)
    dates = Counter(
        pd.to_datetime(output["trade_date"]).dt.strftime("%Y-%m-%d").tolist()
    )
    return record, dates, False


def clean_symbol_partitions(
    source_records: list[dict[str, Any]],
    *,
    partial_root: Path,
    final_root: Path,
    daily_root: Path,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    symbol = str(source_records[0]["symbol"]).lower()
    daily_path = daily_root / f"{symbol}.parquet"
    if not daily_path.is_file():
        raise CleaningError(f"local daily history is missing: {daily_path}")
    daily_sha256 = file_digest(daily_path)
    daily = pd.read_parquet(daily_path)
    records: list[dict[str, Any]] = []
    dates: Counter[str] = Counter()
    resumed = 0
    for source_record in sorted(source_records, key=lambda item: int(item["year"])):
        record, partition_dates, was_resumed = clean_source_partition(
            source_record,
            partial_root=partial_root,
            final_root=final_root,
            daily=daily,
            daily_sha256=daily_sha256,
        )
        records.append(record)
        dates.update(partition_dates)
        resumed += int(was_resumed)
    return records, dates, resumed


def aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for record in records:
        for key, value in (record.get("quality") or {}).items():
            result[str(key)] += int(value)
    return dict(sorted(result.items()))


def coverage_report(
    source_manifest: dict[str, Any], eligible_by_date: Counter[str], protocol: dict[str, Any]
) -> dict[str, Any]:
    daily_source = (source_manifest.get("coverage") or {}).get("daily") or []
    if not daily_source:
        raise CleaningError("source manifest has no fingerprint-bound daily coverage")
    rows: list[dict[str, Any]] = []
    ratios: list[float] = []
    counts: list[int] = []
    dates: list[str] = []
    for source_row in daily_source:
        trade_date = str(source_row["trade_date"])
        active = int(source_row["active_pit_names"])
        eligible = int(eligible_by_date.get(trade_date, 0))
        if eligible > active:
            raise CleaningError(
                f"eligible session count exceeds PIT denominator on {trade_date}: "
                f"{eligible} > {active}"
            )
        ratio = eligible / active if active > 0 else math.nan
        dates.append(trade_date)
        counts.append(eligible)
        if math.isfinite(ratio):
            ratios.append(ratio)
        rows.append(
            {
                "trade_date": trade_date,
                "active_pit_names": active,
                "sentiment_eligible_names": eligible,
                "sentiment_eligible_coverage": ratio if math.isfinite(ratio) else None,
            }
        )
    if not ratios:
        raise CleaningError("cleaned sentiment coverage has no active sessions")
    gates = protocol["coverage_gates"]
    minimum_names = int(gates["minimum_eligible_names_per_cross_section"])
    indices = np.arange(0, max(len(dates) - 3, 0), 3, dtype=int)
    count_array = np.asarray(counts, dtype=np.int64)
    potential_cohorts = int((count_array[indices] >= minimum_names).sum())
    years = sorted(
        {
            int(dates[index][:4])
            for index in indices
            if count_array[index] >= minimum_names
        }
    )
    median = float(np.median(np.asarray(ratios, dtype=float)))
    p05 = float(np.quantile(np.asarray(ratios, dtype=float), 0.05))
    passed = (
        median >= float(gates["minimum_median_eligible_session_coverage"])
        and p05 >= float(gates["minimum_p05_eligible_session_coverage"])
        and potential_cohorts
        >= int(gates["minimum_non_overlapping_three_session_cohorts"])
        and len(years) >= int(gates["minimum_observed_calendar_years"])
    )
    return {
        "calendar_sessions": len(rows),
        "median_sentiment_eligible_coverage": median,
        "p05_sentiment_eligible_coverage": p05,
        "dates_with_at_least_fifty_eligible_names": int(
            (count_array >= minimum_names).sum()
        ),
        "potential_non_overlapping_three_session_cohorts": potential_cohorts,
        "observed_cohort_years": years,
        "gate_passed_before_any_forward_return_protocol": passed,
        "daily": rows,
    }


class ProcessLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> "ProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            raise CleaningError(f"another sentiment cleaning process holds {self.path}") from exc
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(f"pid={os.getpid()}\n")
        self.handle.flush()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def validate_source_chain(data_root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    if file_digest(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise CleaningError(f"sentiment cleaning protocol changed: {PROTOCOL_PATH}")
    if file_digest(SOURCE_AUDIT_PATH) != SOURCE_AUDIT_SHA256:
        raise CleaningError(f"terminal source audit changed: {SOURCE_AUDIT_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    source_manifest_path = (
        data_root
        / "raw"
        / "a_share"
        / "rich"
        / "tushare"
        / "minutes"
        / "1m"
        / "snapshots"
        / SOURCE_RUN_ID
        / "snapshot_manifest.json"
    )
    if not source_manifest_path.is_file():
        raise CleaningError(f"source snapshot manifest is missing: {source_manifest_path}")
    if file_digest(source_manifest_path) != SOURCE_MANIFEST_SHA256:
        raise CleaningError(f"source snapshot manifest changed: {source_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if (
        source_manifest.get("run_id") != SOURCE_RUN_ID
        or source_manifest.get("provider") != "tushare"
        or source_manifest.get("frequency") != "1m"
        or source_manifest.get("forward_return_fields_read") is not False
    ):
        raise CleaningError("source snapshot identity or research boundary is rejected")
    return protocol, source_manifest, source_manifest_path


def build(*, data_root: Path, workers: int) -> Path:
    data_root = data_root.expanduser().resolve()
    protocol, source_manifest, source_manifest_path = validate_source_chain(data_root)
    daily_root = REPO_ROOT / "data" / "raw" / "a_share" / "daily"
    output_parent = (
        data_root
        / "derived"
        / "a_share"
        / "rich"
        / "tushare"
        / "minute_sentiment_clean"
    )
    final_root = output_parent / OUTPUT_RUN_ID
    partial_root = output_parent / f".{OUTPUT_RUN_ID}.partial"
    lock_path = data_root / ".a_share_tushare_1m_sentiment_clean.lock"
    if final_root.exists():
        manifest_path = final_root / "snapshot_manifest.json"
        if not manifest_path.is_file():
            raise CleaningError(f"published output is missing its manifest: {final_root}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("protocol_sha256") != PROTOCOL_SHA256
            or manifest.get("source_manifest_sha256") != SOURCE_MANIFEST_SHA256
            or manifest.get("output_run_id") != OUTPUT_RUN_ID
        ):
            raise CleaningError(f"published output has an unexpected identity: {final_root}")
        return manifest_path

    usage = shutil.disk_usage(data_root)
    if usage.free < 5 * 1024**3:
        raise CleaningError("external data root has less than 5 GiB free")
    source_records = list(source_manifest.get("files") or [])
    if len(source_records) != 33015:
        raise CleaningError(
            f"expected 33,015 source partitions, observed {len(source_records):,}"
        )
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for record in source_records:
        by_symbol.setdefault(str(record["symbol"]), []).append(record)

    with ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_by_date: Counter[str] = Counter()
        resumed_partitions = 0
        completed_symbols = 0
        print(
            f"cleaning {len(source_records):,} partitions across {len(by_symbol):,} symbols "
            f"with {workers} workers",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    clean_symbol_partitions,
                    records,
                    partial_root=partial_root,
                    final_root=final_root,
                    daily_root=daily_root,
                ): symbol
                for symbol, records in sorted(by_symbol.items())
            }
            try:
                for future in as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed = future.result()
                    all_records.extend(records)
                    eligible_by_date.update(dates)
                    resumed_partitions += resumed
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(by_symbol):
                        print(
                            f"progress symbols={completed_symbols:,}/{len(by_symbol):,} "
                            f"partitions={len(all_records):,}/{len(source_records):,} "
                            f"eligible_sessions={sum(eligible_by_date.values()):,} "
                            f"resumed_partitions={resumed_partitions:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise

        if len(all_records) != len(source_records):
            raise CleaningError("not every source partition produced a cleaning checkpoint")
        if file_digest(source_manifest_path) != SOURCE_MANIFEST_SHA256:
            raise CleaningError("source manifest changed during cleaning")
        coverage = coverage_report(source_manifest, eligible_by_date, protocol)
        quality = aggregate_quality(all_records)
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        dataset_digest_payload = "\n".join(
            f"{record['symbol']}|{record['year']}|{record['output_byte_sha256']}"
            for record in all_records
        ).encode("utf-8")
        passed = bool(coverage["gate_passed_before_any_forward_return_protocol"])
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_one_minute_sentiment_clean_snapshot",
            "status": (
                "cleaned_sentiment_coverage_passed_pending_separate_no_return_research_protocol"
                if passed
                else "cleaned_sentiment_coverage_failed_stop_before_returns"
            ),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(PROTOCOL_PATH),
            "protocol_sha256": PROTOCOL_SHA256,
            "source_manifest_path": str(source_manifest_path),
            "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "source_audit_path": str(SOURCE_AUDIT_PATH),
            "source_audit_sha256": SOURCE_AUDIT_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_digest_payload).hexdigest(),
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("eligible_sessions", 0)),
            "quality": quality,
            "coverage": coverage,
            "feature_columns": list(FEATURE_COLUMNS),
            "opening_price_or_extrema_used_by_retained_features": False,
            "daily_price_fields_read_only_for_source_reconciliation": [
                "raw_close",
                "raw_volume",
                "amount",
                "price_basis",
            ],
            "source_rows_mutated": False,
            "forward_return_fields_read": False,
            "existing_factor_returns_reused": False,
            "aggregation_scoring_selection_sizing_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed_partitions,
        }
        manifest_path = partial_root / "snapshot_manifest.json"
        atomic_write_json(manifest, manifest_path)
        output_parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_root / "snapshot_manifest.json"


def empty_fieldwise_overlay_frame() -> pd.DataFrame:
    """Return a typed empty factor-specific exception overlay."""

    data: dict[str, pd.Series] = {
        "trade_date": pd.Series(dtype="datetime64[ns]"),
        "symbol": pd.Series(dtype="object"),
        "provider": pd.Series(dtype="object"),
        "opening_row_role": pd.Series(dtype="object"),
        "source_minute_bars": pd.Series(dtype="int16"),
        "canonical_bars": pd.Series(dtype="int16"),
        "close_relative_error": pd.Series(dtype="float64"),
        "amount_ratio_to_local_daily": pd.Series(dtype="float64"),
        "volume_ratio_to_local_daily": pd.Series(dtype="float64"),
    }
    data.update({feature: pd.Series(dtype="float64") for feature in FEATURE_COLUMNS})
    data.update(
        {column: pd.Series(dtype="bool") for column in FIELDWISE_ELIGIBILITY_COLUMNS}
    )
    return pd.DataFrame(data).loc[:, FIELDWISE_OUTPUT_COLUMNS]


def fieldwise_overlay_frame(
    frame: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    symbol: str,
    base_dates: Iterable[pd.Timestamp] = (),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recover factor-specific rows omitted by the conservative joint snapshot."""

    required = {"datetime", "symbol", "provider", "close", "volume", "amount"}
    if missing := sorted(required - set(frame.columns)):
        raise CleaningError(
            "fieldwise source partition is missing columns: " + ", ".join(missing)
        )
    if frame.empty:
        return empty_fieldwise_overlay_frame(), {
            "exact_source_grid_sessions": 0,
            "base_overlap_sessions": 0,
            "overlay_rows": 0,
            **{f"{feature}_recovered_sessions": 0 for feature in FEATURE_COLUMNS},
        }
    symbols = set(frame["symbol"].dropna().astype(str).str.upper())
    providers = set(frame["provider"].dropna().astype(str).str.lower())
    if symbols != {symbol.upper()} or providers != {"tushare"}:
        raise CleaningError(f"fieldwise source identity mismatch for {symbol}")

    work = frame[list(required)].copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    if work["datetime"].isna().any():
        raise CleaningError(f"fieldwise source timestamps are invalid for {symbol}")
    work = work.sort_values("datetime", kind="stable").reset_index(drop=True)
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    ).astype(np.int16)
    for column in ("close", "volume", "amount"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work["row_on_source_grid"] = (
        work["minute_code"].isin(SOURCE_MINUTE_CODE_SET)
        & work["datetime"].dt.second.eq(0)
        & work["datetime"].dt.microsecond.eq(0)
    )
    stats = work.groupby("trade_date", sort=True, observed=True).agg(
        row_count=("datetime", "size"),
        unique_times=("minute_code", "nunique"),
        on_grid_rows=("row_on_source_grid", "sum"),
    )
    exact_mask = (
        stats["row_count"].eq(241)
        & stats["unique_times"].eq(241)
        & stats["on_grid_rows"].eq(241)
    )
    exact_dates = pd.DatetimeIndex(stats.index[exact_mask])
    quality: dict[str, Any] = {
        "exact_source_grid_sessions": int(exact_mask.sum()),
        "base_overlap_sessions": 0,
        "overlay_rows": 0,
        **{f"{feature}_recovered_sessions": 0 for feature in FEATURE_COLUMNS},
    }
    if exact_dates.empty:
        return empty_fieldwise_overlay_frame(), quality

    exact = work[work["trade_date"].isin(exact_dates)].sort_values(
        ["trade_date", "datetime"], kind="stable"
    )
    codes = exact["minute_code"].to_numpy().reshape(-1, 241)
    if not np.array_equal(codes, np.broadcast_to(SOURCE_MINUTE_CODES, codes.shape)):
        raise CleaningError("fieldwise exact-grid vectorization invariant failed")
    dates = pd.DatetimeIndex(exact["trade_date"].to_numpy()[::241])
    close = exact["close"].to_numpy(dtype=float).reshape(-1, 241)
    volume = exact["volume"].to_numpy(dtype=float).reshape(-1, 241)
    amount = exact["amount"].to_numpy(dtype=float).reshape(-1, 241)
    canonical_close = close[:, 1:]
    close_path_valid = np.isfinite(canonical_close).all(axis=1) & (
        canonical_close > 0.0
    ).all(axis=1)
    volume_rows_valid = np.isfinite(volume).all(axis=1) & (volume >= 0.0).all(
        axis=1
    )
    amount_rows_valid = np.isfinite(amount).all(axis=1) & (amount >= 0.0).all(
        axis=1
    )
    source_volume = volume.sum(axis=1)
    source_amount = amount.sum(axis=1)
    positive_activity = (
        volume_rows_valid
        & amount_rows_valid
        & (source_volume > 0.0)
        & (source_amount > 0.0)
    )

    aligned = prepare_daily_reconciliation(daily, symbol).reindex(dates)
    daily_close = aligned["raw_close"].to_numpy(dtype=float)
    daily_volume = aligned["raw_volume"].to_numpy(dtype=float)
    daily_amount = aligned["amount"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        close_error = np.abs(canonical_close[:, -1] - daily_close) / np.abs(
            daily_close
        )
        amount_ratio = source_amount / daily_amount
        volume_ratio = source_volume / daily_volume
    close_pass = (
        np.isfinite(daily_close)
        & (daily_close > 0.0)
        & np.isfinite(close_error)
        & (close_error <= 0.002)
    )
    amount_pass = (
        np.isfinite(daily_amount)
        & (daily_amount > 0.0)
        & np.isfinite(amount_ratio)
        & (np.abs(amount_ratio - 1.0) <= 0.005)
    )
    volume_pass = (
        np.isfinite(daily_volume)
        & (daily_volume > 0.0)
        & np.isfinite(volume_ratio)
        & (np.abs(volume_ratio - 100.0) <= 0.005)
    )
    common = positive_activity & close_pass
    late_close = canonical_close[:, LATE_START_INDEX]
    late_amount = amount[:, 1:][:, LATE_START_INDEX + 1 :].sum(axis=1)
    late_volume = volume[:, 1:][:, LATE_START_INDEX + 1 :].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        late_return = canonical_close[:, -1] / late_close - 1.0
        late_amount_share = late_amount / source_amount
        late_vwap_to_day_vwap = (
            (late_amount / late_volume) / (source_amount / source_volume) - 1.0
        )
        realized_volatility = np.sqrt(
            np.square(np.diff(np.log(canonical_close), axis=1)).sum(axis=1)
        )

    eligibilities = {
        "late_return_30m": (
            common
            & np.isfinite(late_return)
            & np.isfinite(late_close)
            & (late_close > 0.0)
            & np.isfinite(canonical_close[:, -1])
            & (canonical_close[:, -1] > 0.0)
        ),
        "late_amount_share_30m": (
            common
            & amount_rows_valid
            & amount_pass
            & np.isfinite(late_amount_share)
            & (late_amount >= 0.0)
        ),
        "late_vwap_to_day_vwap_30m": (
            common
            & amount_rows_valid
            & volume_rows_valid
            & amount_pass
            & volume_pass
            & (late_amount > 0.0)
            & (late_volume > 0.0)
            & np.isfinite(late_vwap_to_day_vwap)
        ),
        "intraday_realized_volatility": (
            common & close_path_valid & np.isfinite(realized_volatility)
        ),
    }
    values = {
        "late_return_30m": late_return,
        "late_amount_share_30m": late_amount_share,
        "late_vwap_to_day_vwap_30m": late_vwap_to_day_vwap,
        "intraday_realized_volatility": realized_volatility,
    }
    base_date_index = pd.DatetimeIndex(pd.to_datetime(list(base_dates))).normalize()
    base_overlap = dates.isin(base_date_index)
    quality["base_overlap_sessions"] = int(base_overlap.sum())
    any_eligible = np.logical_or.reduce(list(eligibilities.values())) & ~base_overlap
    if not any_eligible.any():
        return empty_fieldwise_overlay_frame(), quality

    selected: dict[str, Any] = {
        "trade_date": dates[any_eligible],
        "symbol": symbol.upper(),
        "provider": "tushare",
        "opening_row_role": np.where(
            (volume[:, 0] == 0.0) & (amount[:, 0] == 0.0),
            "reference_placeholder",
            "active_auction",
        )[any_eligible],
        "source_minute_bars": np.int16(241),
        "canonical_bars": np.int16(240),
        "close_relative_error": close_error[any_eligible],
        "amount_ratio_to_local_daily": amount_ratio[any_eligible],
        "volume_ratio_to_local_daily": volume_ratio[any_eligible],
    }
    for feature in FEATURE_COLUMNS:
        eligible = eligibilities[feature]
        selected[feature] = np.where(eligible, values[feature], np.nan)[any_eligible]
        selected[f"{feature}_eligible"] = eligible[any_eligible]
        quality[f"{feature}_recovered_sessions"] = int(
            (eligible & ~base_overlap).sum()
        )
    output = pd.DataFrame(selected).loc[:, FIELDWISE_OUTPUT_COLUMNS]
    quality["overlay_rows"] = int(len(output))
    return output, quality


def select_fieldwise_exception_partitions(
    joint_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """Select exception partitions from frozen counts, never from returns."""

    selected: list[dict[str, Any]] = []
    for record in joint_manifest.get("files") or []:
        quality = record.get("quality") or {}
        exact = int(quality.get("exact_source_grid_sessions", 0))
        missing_daily = int(quality.get("missing_local_daily_sessions", 0))
        rows = int(record.get("rows", 0))
        amount_failures = int(
            quality.get("amount_reconciliation_failed_sessions", 0)
        )
        if amount_failures > 0 or rows < exact - missing_daily:
            selected.append(record)
    return selected


def fieldwise_factor_coverage(
    joint_manifest: dict[str, Any], overlay: pd.DataFrame, protocol: dict[str, Any]
) -> dict[str, Any]:
    """Calculate the frozen coverage gates independently for each factor."""

    daily = list((joint_manifest.get("coverage") or {}).get("daily") or [])
    if not daily:
        raise CleaningError("joint manifest has no daily PIT coverage denominator")
    gates = protocol["coverage_gates_applied_separately_to_each_factor"]
    minimum_names = int(gates["minimum_names_per_cross_section"])
    base_counts = {
        str(row["trade_date"]): int(row["sentiment_eligible_names"])
        for row in daily
    }
    overlay_dates = pd.to_datetime(overlay.get("trade_date", pd.Series(dtype=object)))
    result: dict[str, Any] = {}
    for feature in FEATURE_COLUMNS:
        increments: Counter[str] = Counter()
        if not overlay.empty:
            mask = overlay[f"{feature}_eligible"].fillna(False).astype(bool)
            increments.update(overlay_dates[mask].dt.strftime("%Y-%m-%d"))
        ratios: list[float] = []
        eligible_counts: list[int] = []
        dates: list[str] = []
        rows: list[dict[str, Any]] = []
        for source_row in daily:
            trade_date = str(source_row["trade_date"])
            active = int(source_row["active_pit_names"])
            eligible = base_counts[trade_date] + int(increments.get(trade_date, 0))
            if eligible > active:
                raise CleaningError(
                    f"{feature} eligible count exceeds PIT names on {trade_date}"
                )
            ratio = eligible / active if active else math.nan
            dates.append(trade_date)
            eligible_counts.append(eligible)
            if math.isfinite(ratio):
                ratios.append(ratio)
            rows.append(
                {
                    "trade_date": trade_date,
                    "active_pit_names": active,
                    "eligible_names": eligible,
                    "coverage": ratio if math.isfinite(ratio) else None,
                }
            )
        count_array = np.asarray(eligible_counts, dtype=np.int64)
        cohort_indices = np.arange(0, max(len(dates) - 3, 0), 3, dtype=int)
        potential_cohorts = int(
            (count_array[cohort_indices] >= minimum_names).sum()
        )
        years = sorted(
            {
                int(dates[index][:4])
                for index in cohort_indices
                if count_array[index] >= minimum_names
            }
        )
        ratio_array = np.asarray(ratios, dtype=float)
        median = float(np.median(ratio_array))
        p05 = float(np.quantile(ratio_array, 0.05))
        passed = (
            median >= float(gates["minimum_median_coverage"])
            and p05 >= float(gates["minimum_p05_coverage"])
            and potential_cohorts
            >= int(gates["minimum_non_overlapping_three_session_cohorts"])
            and len(years) >= int(gates["minimum_observed_calendar_years"])
        )
        result[feature] = {
            "eligible_symbol_sessions": int(count_array.sum()),
            "overlay_recovered_sessions": int(sum(increments.values())),
            "median_coverage": median,
            "p05_coverage": p05,
            "dates_with_at_least_minimum_names": int(
                (count_array >= minimum_names).sum()
            ),
            "potential_non_overlapping_three_session_cohorts": potential_cohorts,
            "observed_cohort_years": years,
            "gate_passed_before_forward_returns": passed,
            "daily": rows,
        }
    return result


def validate_fieldwise_source_chain(
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Validate every immutable input before reading an exception partition."""

    for path, expected, label in (
        (FIELDWISE_PROTOCOL_PATH, FIELDWISE_PROTOCOL_SHA256, "fieldwise protocol"),
        (PROTOCOL_PATH, PROTOCOL_SHA256, "joint cleaning protocol"),
        (JOINT_RESULT_PATH, JOINT_RESULT_SHA256, "joint cleaning result"),
        (SOURCE_AUDIT_PATH, SOURCE_AUDIT_SHA256, "terminal source audit"),
    ):
        if not path.is_file() or file_digest(path) != expected:
            raise CleaningError(f"{label} changed: {path}")
    protocol = json.loads(FIELDWISE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    joint_manifest_path = (
        data_root
        / "derived/a_share/rich/tushare/minute_sentiment_clean"
        / OUTPUT_RUN_ID
        / "snapshot_manifest.json"
    )
    if (
        not joint_manifest_path.is_file()
        or file_digest(joint_manifest_path) != JOINT_MANIFEST_SHA256
    ):
        raise CleaningError(f"joint cleaned snapshot changed: {joint_manifest_path}")
    joint_manifest = json.loads(joint_manifest_path.read_text(encoding="utf-8"))
    if (
        joint_manifest.get("status")
        != "cleaned_sentiment_coverage_passed_pending_separate_no_return_research_protocol"
        or joint_manifest.get("forward_return_fields_read") is not False
        or joint_manifest.get("rows") != 7_724_498
    ):
        raise CleaningError("joint cleaned snapshot identity is rejected")
    return protocol, joint_manifest, joint_manifest_path


def build_fieldwise_overlay(*, data_root: Path, workers: int) -> Path:
    """Build the immutable factor-specific exception overlay."""

    data_root = data_root.expanduser().resolve()
    protocol, joint_manifest, joint_manifest_path = validate_fieldwise_source_chain(
        data_root
    )
    output_parent = (
        data_root
        / "derived/a_share/rich/tushare/minute_fieldwise_clean"
    )
    final_root = output_parent / FIELDWISE_OUTPUT_RUN_ID
    partial_root = output_parent / f".{FIELDWISE_OUTPUT_RUN_ID}.partial"
    manifest_path = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not manifest_path.is_file():
            raise CleaningError(f"fieldwise output has no manifest: {final_root}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        overlay_path = final_root / "exceptions.parquet"
        if (
            manifest.get("protocol_sha256") != FIELDWISE_PROTOCOL_SHA256
            or manifest.get("joint_manifest_sha256") != JOINT_MANIFEST_SHA256
            or not overlay_path.is_file()
            or file_digest(overlay_path) != manifest.get("overlay_byte_sha256")
        ):
            raise CleaningError(f"published fieldwise output changed: {final_root}")
        return manifest_path

    exception_records = select_fieldwise_exception_partitions(joint_manifest)
    expected_partitions = int(
        protocol["exception_partition_selection"][
            "observed_partition_count_before_overlay_values"
        ]
    )
    if len(exception_records) != expected_partitions:
        raise CleaningError(
            f"expected {expected_partitions} fieldwise exception partitions, "
            f"observed {len(exception_records)}"
        )
    daily_root = REPO_ROOT / "data/raw/a_share/daily"

    def process(record: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
        source_path = Path(str(record["source_path"]))
        base_path = Path(str(record["path"]))
        if (
            file_digest(source_path) != record.get("source_byte_sha256")
            or file_digest(base_path) != record.get("output_byte_sha256")
        ):
            raise CleaningError(f"fieldwise exception input changed: {source_path}")
        symbol = str(record["symbol"])
        daily_path = daily_root / f"{symbol.lower()}.parquet"
        if file_digest(daily_path) != record.get("daily_byte_sha256"):
            raise CleaningError(f"fieldwise local daily input changed: {daily_path}")
        source = pd.read_parquet(
            source_path,
            columns=["datetime", "symbol", "provider", "close", "volume", "amount"],
        )
        daily = pd.read_parquet(
            daily_path,
            columns=["date", "raw_close", "raw_volume", "amount", "price_basis"],
        )
        base = pd.read_parquet(base_path, columns=["trade_date"])
        output, quality = fieldwise_overlay_frame(
            source,
            daily,
            symbol=symbol,
            base_dates=base["trade_date"],
        )
        quality.update({"symbol": symbol, "year": int(record["year"])})
        return output, quality

    lock_path = data_root / ".a_share_tushare_1m_fieldwise_clean.lock"
    with ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=False)
        frames: list[pd.DataFrame] = []
        partition_quality: list[dict[str, Any]] = []
        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(process, record) for record in exception_records]
                for completed, future in enumerate(as_completed(futures), start=1):
                    frame, quality = future.result()
                    frames.append(frame)
                    partition_quality.append(quality)
                    if completed % 25 == 0 or completed == len(futures):
                        print(
                            f"fieldwise progress={completed}/{len(futures)} "
                            f"overlay_rows={sum(len(item) for item in frames)}",
                            flush=True,
                        )
            overlay = (
                pd.concat(frames, ignore_index=True)
                if frames
                else empty_fieldwise_overlay_frame()
            )
            overlay = overlay.sort_values(
                ["trade_date", "symbol"], kind="stable"
            ).reset_index(drop=True)
            if overlay.duplicated(["trade_date", "symbol"]).any():
                raise CleaningError("fieldwise overlay contains duplicate symbol-session keys")
            coverage = fieldwise_factor_coverage(joint_manifest, overlay, protocol)
            all_passed = all(
                item["gate_passed_before_forward_returns"]
                for item in coverage.values()
            )
            overlay_path = partial_root / "exceptions.parquet"
            atomic_write_frame(overlay, overlay_path)
            partition_quality.sort(key=lambda item: (item["symbol"], item["year"]))
            manifest = {
                "schema_version": 1,
                "kind": "a_share_tushare_one_minute_fieldwise_clean_snapshot",
                "status": (
                    "fieldwise_factor_coverage_passed_pending_separate_exploratory_research_preregistration"
                    if all_passed
                    else "fieldwise_factor_coverage_failed_stop_before_returns"
                ),
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "output_run_id": FIELDWISE_OUTPUT_RUN_ID,
                "protocol_path": str(FIELDWISE_PROTOCOL_PATH),
                "protocol_sha256": FIELDWISE_PROTOCOL_SHA256,
                "joint_manifest_path": str(joint_manifest_path),
                "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
                "raw_source_manifest_sha256": SOURCE_MANIFEST_SHA256,
                "joint_base_rows": int(joint_manifest["rows"]),
                "exception_partitions_read": len(exception_records),
                "all_other_raw_partitions_read": False,
                "overlay_path": str(final_root / "exceptions.parquet"),
                "overlay_rows": int(len(overlay)),
                "overlay_byte_sha256": file_digest(overlay_path),
                "overlay_frame_sha256": frame_digest(overlay),
                "factor_columns": list(FEATURE_COLUMNS),
                "factor_eligibility_columns": list(FIELDWISE_ELIGIBILITY_COLUMNS),
                "factor_coverage": coverage,
                "all_factor_coverage_gates_passed": all_passed,
                "partition_quality": partition_quality,
                "source_open_high_low_loaded": False,
                "source_rows_mutated": False,
                "daily_prices_substituted_into_minute_rows": False,
                "forward_return_fields_read": False,
                "existing_factor_returns_reused": False,
                "training_or_model_fitting_performed": False,
                "aggregation_scoring_selection_sizing_or_orders_performed": False,
                "promotion_allowed": False,
            }
            atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
            output_parent.mkdir(parents=True, exist_ok=True)
            partial_root.replace(final_root)
            return final_root / "snapshot_manifest.json"
        except BaseException:
            shutil.rmtree(partial_root, ignore_errors=True)
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="build or resume the clean layer")
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--workers", type=int, default=4)
    fieldwise_parser = subparsers.add_parser(
        "build-fieldwise-overlay",
        help="build the factor-specific exception overlay without reading returns",
    )
    fieldwise_parser.add_argument("--data-root", type=Path, required=True)
    fieldwise_parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        if not 1 <= args.workers <= 16:
            raise CleaningError("--workers must be between 1 and 16")
        manifest_path = build(data_root=args.data_root, workers=args.workers)
        print(manifest_path, flush=True)
        return 0
    if args.command == "build-fieldwise-overlay":
        if not 1 <= args.workers <= 16:
            raise CleaningError("--workers must be between 1 and 16")
        manifest_path = build_fieldwise_overlay(
            data_root=args.data_root, workers=args.workers
        )
        print(manifest_path, flush=True)
        return 0
    raise CleaningError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
