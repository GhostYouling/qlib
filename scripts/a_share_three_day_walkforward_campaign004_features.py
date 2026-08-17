#!/usr/bin/env python3
"""Build and audit the three no-return feature mechanisms for Campaign004.

The builder reads only the immutable joint-clean Tushare one-minute source and
the already-frozen leave-one-out market-return benchmark.  It never reads a
daily price, a forward return, Candidate49 outcome, or provider credential.

The ordered audit first applies quality/listing coverage gates to each new
factor.  Only coverage-passers may load the 24 terminal comparison factors,
Candidate49's historical no-return snapshot, or another Campaign004 factor for
the uniqueness screen.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate49  # noqa: E402
import a_share_tushare_intraday_market_idiosyncratic_share as market  # noqa: E402


foundation = market.foundation
research = market.research
comparison_engine = candidate49.comparison_engine
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_004_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_004"
    / "no_return"
)

PROTOCOL_SHA256 = (
    "39e2147b75bcc3a0fd3cb39dee3932f794331142654f0bfe63679b2c8ecc2a4e"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "8eefc381d006997f1dcd95edcd9be4db8485e0c4954d6166d94f1981ae3b57fe"
)
SNAPSHOT_DATASET_SHA256 = (
    "1359e755e669c7b949b26b2086d1c1328ec0cdf53b45ce7e67d117a274c7fc8a"
)
NO_RETURN_AUDIT_SHA256 = (
    "d7cdce80d0ac2923695b866a7cf034f5049ec4da1a5a8dd5fc36d4f41f1cb755"
)

SOURCE_RUN_ID = market.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_walkforward_campaign004_feature_library_v1"
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
BASE_COLUMNS = ("trade_date", "symbol")
FACTOR_NAMES = (
    "intraday_market_neutral_late_residual_drift_238m",
    "intraday_negative_return_absorption_rate_236p",
    "intraday_signed_path_efficiency_239m",
)
MARKET_NEUTRAL_FACTOR, ABSORPTION_FACTOR, PATH_EFFICIENCY_FACTOR = FACTOR_NAMES
FACTOR_DIRECTIONS = {name: "higher" for name in FACTOR_NAMES}
FACTOR_RANGES = {
    MARKET_NEUTRAL_FACTOR: (-1.0, 1.0),
    ABSORPTION_FACTOR: (0.0, 1.0),
    PATH_EFFICIENCY_FACTOR: (-1.0, 1.0),
}
FACTOR_FORMULAS = {
    MARKET_NEUTRAL_FACTOR: (
        "sum(e_i,t for the final 60 afternoon returns ending 14:01-15:00) / "
        "sum(abs(e_i,t) over all 238 within-half returns), where "
        "e_i,t=r_i,t-beta_i*m_-i,t, beta_i=sum(r_i,t*m_-i,t)/sum(m_-i,t^2), "
        "and m_-i,t is the equal-weight leave-one-out market return"
    ),
    ABSORPTION_FACTOR: (
        "sum(amount_at_destination_of_r_t for within-half adjacent pairs with "
        "r_t<0 and r_t+1>0) / sum(amount_at_destination_of_r_t for "
        "within-half adjacent pairs with r_t<0)"
    ),
    PATH_EFFICIENCY_FACTOR: (
        "log(close_15:00/close_09:31) / sum(abs(adjacent log close return)) "
        "over the collapsed 240-close path including the 11:30-to-13:01 pair"
    ),
}
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    MARKET_NEUTRAL_FACTOR,
    f"{MARKET_NEUTRAL_FACTOR}_eligible",
    ABSORPTION_FACTOR,
    f"{ABSORPTION_FACTOR}_eligible",
    PATH_EFFICIENCY_FACTOR,
    f"{PATH_EFFICIENCY_FACTOR}_eligible",
)
RETURN_POSITIONS = 238
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
ENDPOINT_TOLERANCE = 1e-12
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_SYMBOLS = 5_396
MARKET_SNAPSHOT_SHA256 = market.CANDIDATE_MANIFEST_SHA256
MARKET_BENCHMARK_BYTE_SHA256 = (
    "5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf"
)
MARKET_BENCHMARK_FRAME_SHA256 = (
    "5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1"
)


class Campaign004FeatureError(RuntimeError):
    """Fail-closed Campaign004 feature or no-return audit error."""


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise Campaign004FeatureError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign004_feature_library"
        / OUTPUT_RUN_ID
    )


def empty_output_frame() -> pd.DataFrame:
    columns: dict[str, pd.Series] = {
        "trade_date": pd.Series(dtype="datetime64[ns]"),
        "symbol": pd.Series(dtype="string"),
        "provider": pd.Series(dtype="string"),
    }
    for name in FACTOR_NAMES:
        columns[name] = pd.Series(dtype="float64")
        columns[f"{name}_eligible"] = pd.Series(dtype="bool")
    return pd.DataFrame(columns).loc[:, OUTPUT_COLUMNS]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign004 factor value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign004FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign004 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign004 no-return protocol")
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign004_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
    observed_names = tuple(str(item.get("name") or "") for item in candidates)
    observed_formulas = {
        str(item.get("name") or ""): str(item.get("formula") or "")
        for item in candidates
    }
    observed_directions = {
        str(item.get("name") or ""): str(item.get("direction") or "")
        for item in candidates
    }
    audit = spec.get("ordered_no_return_gates") or {}
    coverage = audit.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = audit.get("uniqueness_after_coverage_only") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign004_candidate_or_comparison_values_or_returns"
        and observed_names == FACTOR_NAMES
        and observed_formulas == FACTOR_FORMULAS
        and observed_directions == FACTOR_DIRECTIONS
        and all(tuple(item.get("source_fields_allowed") or ()) == RAW_COLUMNS for item in candidates)
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign004FeatureError("Campaign004 no-return protocol semantics changed")
    return spec


def _canonicalize_range(
    values: np.ndarray,
    *,
    lower: float,
    upper: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    low_near = (values < lower) & (values >= lower - ENDPOINT_TOLERANCE)
    high_near = (values > upper) & (values <= upper + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    adjusted = np.where(low_near, lower, np.where(high_near, upper, values))
    in_range = (adjusted >= lower) & (adjusted <= upper)
    return adjusted, canonicalized, in_range


def compute_factor_values(
    *,
    closes: np.ndarray,
    amounts: np.ndarray,
    within_half_returns: np.ndarray,
    leave_one_out_market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute all three frozen mechanisms from aligned no-return arrays."""

    if (
        closes.ndim != 2
        or closes.shape[1] != 240
        or amounts.shape != closes.shape
        or within_half_returns.shape != (len(closes), RETURN_POSITIONS)
        or leave_one_out_market_returns.shape != within_half_returns.shape
        or sufficient_peers.shape != (len(closes),)
    ):
        raise Campaign004FeatureError("Campaign004 aligned array shapes are invalid")
    close_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    returns_valid = np.isfinite(within_half_returns).all(axis=1)
    amount_valid = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)

    market_energy = np.sum(
        leave_one_out_market_returns * leave_one_out_market_returns,
        axis=1,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        beta = np.sum(
            within_half_returns * leave_one_out_market_returns,
            axis=1,
        ) / market_energy
        residuals = (
            within_half_returns
            - beta[:, None] * leave_one_out_market_returns
        )
        residual_denominator = np.sum(np.abs(residuals), axis=1)
        residual_late_sum = np.sum(residuals[:, 178:238], axis=1)
        market_values = residual_late_sum / residual_denominator
    market_values, market_canonicalized, market_in_range = _canonicalize_range(
        market_values,
        lower=-1.0,
        upper=1.0,
    )
    market_finite = np.isfinite(market_values)
    market_eligible = (
        close_valid
        & returns_valid
        & sufficient_peers
        & (market_energy > 0.0)
        & (residual_denominator > 0.0)
        & market_finite
        & market_in_range
    )

    morning = within_half_returns[:, :119]
    afternoon = within_half_returns[:, 119:]
    initiating = np.concatenate([morning[:, :-1], afternoon[:, :-1]], axis=1)
    following = np.concatenate([morning[:, 1:], afternoon[:, 1:]], axis=1)
    initiating_amount = np.concatenate(
        [amounts[:, 1:119], amounts[:, 121:239]],
        axis=1,
    )
    negative = initiating < 0.0
    recovered = negative & (following > 0.0)
    absorption_denominator = np.sum(
        np.where(negative, initiating_amount, 0.0),
        axis=1,
    )
    absorption_numerator = np.sum(
        np.where(recovered, initiating_amount, 0.0),
        axis=1,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        absorption_values = absorption_numerator / absorption_denominator
    (
        absorption_values,
        absorption_canonicalized,
        absorption_in_range,
    ) = _canonicalize_range(absorption_values, lower=0.0, upper=1.0)
    absorption_finite = np.isfinite(absorption_values)
    absorption_eligible = (
        close_valid
        & returns_valid
        & amount_valid
        & (absorption_denominator > 0.0)
        & absorption_finite
        & absorption_in_range
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        log_closes = np.log(closes)
        full_path_returns = log_closes[:, 1:] - log_closes[:, :-1]
        path_denominator = np.sum(np.abs(full_path_returns), axis=1)
        path_values = (log_closes[:, -1] - log_closes[:, 0]) / path_denominator
    path_values, path_canonicalized, path_in_range = _canonicalize_range(
        path_values,
        lower=-1.0,
        upper=1.0,
    )
    path_finite = np.isfinite(path_values)
    path_eligible = (
        close_valid
        & (path_denominator > 0.0)
        & path_finite
        & path_in_range
    )

    values = {
        MARKET_NEUTRAL_FACTOR: np.where(
            market_eligible, market_values, np.nan
        ),
        ABSORPTION_FACTOR: np.where(
            absorption_eligible, absorption_values, np.nan
        ),
        PATH_EFFICIENCY_FACTOR: np.where(
            path_eligible, path_values, np.nan
        ),
    }
    eligible = {
        MARKET_NEUTRAL_FACTOR: market_eligible,
        ABSORPTION_FACTOR: absorption_eligible,
        PATH_EFFICIENCY_FACTOR: path_eligible,
    }
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~close_valid).sum()),
        f"{MARKET_NEUTRAL_FACTOR}__eligible_rows": int(market_eligible.sum()),
        f"{MARKET_NEUTRAL_FACTOR}__insufficient_peer_rows": int(
            (close_valid & returns_valid & ~sufficient_peers).sum()
        ),
        f"{MARKET_NEUTRAL_FACTOR}__zero_market_energy_rows": int(
            (close_valid & returns_valid & sufficient_peers & (market_energy <= 0.0)).sum()
        ),
        f"{MARKET_NEUTRAL_FACTOR}__zero_residual_path_rows": int(
            (
                close_valid
                & returns_valid
                & sufficient_peers
                & (market_energy > 0.0)
                & (residual_denominator <= 0.0)
            ).sum()
        ),
        f"{MARKET_NEUTRAL_FACTOR}__endpoint_canonicalized_rows": int(
            (market_canonicalized & market_eligible).sum()
        ),
        f"{MARKET_NEUTRAL_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & returns_valid
                & sufficient_peers
                & (market_energy > 0.0)
                & (residual_denominator > 0.0)
                & (~market_finite | ~market_in_range)
            ).sum()
        ),
        f"{ABSORPTION_FACTOR}__eligible_rows": int(absorption_eligible.sum()),
        f"{ABSORPTION_FACTOR}__invalid_required_amount_rows": int(
            (close_valid & returns_valid & ~amount_valid).sum()
        ),
        f"{ABSORPTION_FACTOR}__zero_negative_amount_denominator_rows": int(
            (
                close_valid
                & returns_valid
                & amount_valid
                & (absorption_denominator <= 0.0)
            ).sum()
        ),
        f"{ABSORPTION_FACTOR}__endpoint_canonicalized_rows": int(
            (absorption_canonicalized & absorption_eligible).sum()
        ),
        f"{ABSORPTION_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & returns_valid
                & amount_valid
                & (absorption_denominator > 0.0)
                & (~absorption_finite | ~absorption_in_range)
            ).sum()
        ),
        f"{PATH_EFFICIENCY_FACTOR}__eligible_rows": int(path_eligible.sum()),
        f"{PATH_EFFICIENCY_FACTOR}__zero_path_variation_rows": int(
            (close_valid & (path_denominator <= 0.0)).sum()
        ),
        f"{PATH_EFFICIENCY_FACTOR}__endpoint_canonicalized_rows": int(
            (path_canonicalized & path_eligible).sum()
        ),
        f"{PATH_EFFICIENCY_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & (path_denominator > 0.0)
                & (~path_finite | ~path_in_range)
            ).sum()
        ),
    }
    return values, eligible, quality


def _load_market_benchmark(data_root: Path) -> market.MarketBenchmark:
    root = market.output_root(data_root)
    manifest_path = root / "snapshot_manifest.json"
    _require_file(manifest_path, MARKET_SNAPSHOT_SHA256, "market benchmark manifest")
    manifest = research.load_json_record(manifest_path)
    market._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    evidence = manifest.get("market_benchmark") or {}
    benchmark_path = Path(str(evidence.get("path") or ""))
    _require_file(
        benchmark_path,
        MARKET_BENCHMARK_BYTE_SHA256,
        "market benchmark frame",
    )
    frame = pd.read_parquet(
        benchmark_path,
        columns=list(market.BENCHMARK_COLUMNS),
    )
    if (
        foundation.frame_digest(frame) != MARKET_BENCHMARK_FRAME_SHA256
        or len(frame) != 1_699 * RETURN_POSITIONS
    ):
        raise Campaign004FeatureError("market benchmark frame semantics changed")
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    frame["return_position"] = pd.to_numeric(
        frame["return_position"], errors="coerce"
    ).astype("int16")
    frame = frame.sort_values(
        ["trade_date", "return_position"],
        kind="stable",
    ).reset_index(drop=True)
    dates = pd.DatetimeIndex(frame["trade_date"].drop_duplicates())
    positions = frame["return_position"].to_numpy().reshape(-1, RETURN_POSITIONS)
    expected_positions = np.tile(
        np.arange(RETURN_POSITIONS, dtype=np.int16),
        (len(dates), 1),
    )
    sums = pd.to_numeric(frame["return_sum"], errors="coerce").to_numpy(dtype=float)
    counts = pd.to_numeric(
        frame["valid_stock_count"], errors="coerce"
    ).to_numpy(dtype=np.int32)
    sums = sums.reshape(-1, RETURN_POSITIONS)
    counts = counts.reshape(-1, RETURN_POSITIONS)
    if (
        dates.hasnans
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or not np.array_equal(positions, expected_positions)
        or not np.isfinite(sums).all()
        or (counts < MINIMUM_LEAVE_ONE_OUT_PEERS + 1).any()
        or not np.equal(counts, counts[:, :1]).all()
    ):
        raise Campaign004FeatureError("market benchmark values or grid changed")
    return market.MarketBenchmark(
        dates=dates,
        return_sums=sums,
        valid_stock_counts=counts,
        date_to_index={date: index for index, date in enumerate(dates)},
        frame_sha256=MARKET_BENCHMARK_FRAME_SHA256,
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    benchmark: market.MarketBenchmark,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute the frozen feature library."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign004FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, within_half_returns, return_valid = market.extract_partition_returns(
        raw.loc[:, market.RAW_COLUMNS],
        base,
        symbol=symbol,
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign004FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"],
        kind="stable",
    )
    if len(continuous) != len(base_work) * 240:
        raise Campaign004FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 240)
    amounts = continuous["amount"].to_numpy(dtype=float).reshape(-1, 240)
    sums, counts = market._benchmark_for_dates(
        benchmark,
        list(base_work["trade_date"]),
    )
    own = np.where(np.isfinite(within_half_returns), within_half_returns, 0.0)
    own_count = np.isfinite(within_half_returns).astype(np.int32)
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        leave_one_out = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
    values, eligible, quality = compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half_returns,
        leave_one_out_market_returns=leave_one_out,
        sufficient_peers=sufficient,
    )
    if not np.array_equal(
        return_valid,
        np.isfinite(within_half_returns).all(axis=1),
    ):
        raise Campaign004FeatureError(f"return validity changed for {symbol}")
    output: dict[str, Any] = {
        "trade_date": base_work["trade_date"],
        "symbol": symbol.upper(),
        "provider": "tushare",
    }
    for name in FACTOR_NAMES:
        output[name] = values[name]
        output[f"{name}_eligible"] = eligible[name]
    return pd.DataFrame(output).loc[:, OUTPUT_COLUMNS], quality


def _checkpoint_paths(
    partial_root: Path,
    symbol: str,
    year: int,
) -> tuple[Path, Path]:
    return (
        partial_root / "partitions" / symbol / f"{year}.parquet",
        partial_root / ".metadata" / symbol / f"{year}.json",
    )


def _load_checkpoint(
    *,
    partial_root: Path,
    final_root: Path,
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
) -> tuple[dict[str, Any], Counter[str]] | None:
    symbol = str(joint_record["symbol"])
    year = int(joint_record["year"])
    data_path, sidecar_path = _checkpoint_paths(partial_root, symbol, year)
    if not data_path.exists() and not sidecar_path.exists():
        return None
    if not data_path.is_file() or not sidecar_path.is_file():
        raise Campaign004FeatureError(
            f"incomplete Campaign004 checkpoint for {symbol}/{year}"
        )
    record = research.load_json_record(sidecar_path)
    if not (
        record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("raw_source_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_sha256") == joint_record.get("output_byte_sha256")
        and record.get("output_run_id") == OUTPUT_RUN_ID
        and record.get("factor_names") == list(FACTOR_NAMES)
        and record.get("output_byte_sha256") == foundation.file_digest(data_path)
    ):
        raise Campaign004FeatureError(
            f"Campaign004 checkpoint changed for {symbol}/{year}"
        )
    frame = pd.read_parquet(data_path, columns=list(OUTPUT_COLUMNS))
    if (
        len(frame) != int(record.get("rows", -1))
        or foundation.frame_digest(frame) != record.get("output_frame_sha256")
    ):
        raise Campaign004FeatureError(
            f"Campaign004 checkpoint frame changed for {symbol}/{year}"
        )
    final_data = final_root / "partitions" / symbol / f"{year}.parquet"
    record["path"] = str(final_data)
    dates: Counter[str] = Counter()
    for name in FACTOR_NAMES:
        eligible = frame[f"{name}_eligible"].astype("boolean").fillna(False)
        for value in pd.to_datetime(frame.loc[eligible, "trade_date"]):
            dates[f"{name}|{value.date().isoformat()}"] += 1
    return record, dates


def _process_partition(
    *,
    partial_root: Path,
    final_root: Path,
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    benchmark: market.MarketBenchmark,
) -> tuple[dict[str, Any], Counter[str], bool]:
    loaded = _load_checkpoint(
        partial_root=partial_root,
        final_root=final_root,
        raw_record=raw_record,
        joint_record=joint_record,
    )
    if loaded is not None:
        record, dates = loaded
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if (
        foundation.file_digest(raw_path) != raw_record.get("byte_sha256")
        or foundation.file_digest(base_path) != joint_record.get("output_byte_sha256")
    ):
        raise Campaign004FeatureError(
            f"source partition changed for {joint_record['symbol']}/{joint_record['year']}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=list(BASE_COLUMNS))
    frame, quality = compute_partition_frame(
        raw,
        base,
        benchmark,
        symbol=str(joint_record["symbol"]),
    )
    symbol = str(joint_record["symbol"])
    year = int(joint_record["year"])
    data_path, sidecar_path = _checkpoint_paths(partial_root, symbol, year)
    foundation.atomic_write_frame(frame, data_path)
    final_data = final_root / "partitions" / symbol / f"{year}.parquet"
    factor_eligible_rows = {
        name: int(frame[f"{name}_eligible"].sum()) for name in FACTOR_NAMES
    }
    record = {
        "symbol": symbol,
        "year": year,
        "path": str(final_data),
        "protocol_sha256": PROTOCOL_SHA256,
        "output_run_id": OUTPUT_RUN_ID,
        "factor_names": list(FACTOR_NAMES),
        "raw_source_path": str(raw_path),
        "raw_source_sha256": str(raw_record["byte_sha256"]),
        "joint_base_path": str(base_path),
        "joint_base_sha256": str(joint_record["output_byte_sha256"]),
        "rows": int(len(frame)),
        "factor_eligible_rows": factor_eligible_rows,
        "quality": quality,
        "source_fields_read": list(RAW_COLUMNS),
        "output_byte_sha256": foundation.file_digest(data_path),
        "output_frame_sha256": foundation.frame_digest(frame),
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    foundation.atomic_write_json(record, sidecar_path)
    dates: Counter[str] = Counter()
    for name in FACTOR_NAMES:
        eligible = frame[f"{name}_eligible"].astype(bool)
        for value in pd.to_datetime(frame.loc[eligible, "trade_date"]):
            dates[f"{name}|{value.date().isoformat()}"] += 1
    return record, dates, False


def _process_symbol(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    partial_root: Path,
    final_root: Path,
    benchmark: market.MarketBenchmark,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    dates: Counter[str] = Counter()
    resumed = 0
    for raw_record, joint_record in sorted(
        pairs,
        key=lambda pair: int(pair[1]["year"]),
    ):
        record, partition_dates, was_resumed = _process_partition(
            partial_root=partial_root,
            final_root=final_root,
            raw_record=raw_record,
            joint_record=joint_record,
            benchmark=benchmark,
        )
        records.append(record)
        dates.update(partition_dates)
        resumed += int(was_resumed)
    return records, dates, resumed


def _aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for record in records:
        for key, value in (record.get("quality") or {}).items():
            result[str(key)] += int(value)
    return dict(sorted(result.items()))


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    eligible = manifest.get("factor_eligible_rows") or {}
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign004_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("raw_manifest_sha256") == market.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == market.JOINT_MANIFEST_SHA256
        and manifest.get("market_benchmark_manifest_sha256")
        == MARKET_SNAPSHOT_SHA256
        and manifest.get("market_benchmark_byte_sha256")
        == MARKET_BENCHMARK_BYTE_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_names") == list(FACTOR_NAMES)
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and all(isinstance(eligible.get(name), int) for name in FACTOR_NAMES)
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_or_volume_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign004FeatureError("Campaign004 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign004FeatureError(
            "Campaign004 snapshot fingerprint constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all three features without comparison values or returns."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_protocol()
    final_root = output_root(data_root)
    final_manifest = final_root / "snapshot_manifest.json"
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists():
        if not final_manifest.is_file() or not SNAPSHOT_MANIFEST_SHA256:
            raise Campaign004FeatureError(
                "published snapshot exists but its fingerprint is not bound"
            )
        _require_file(
            final_manifest,
            SNAPSHOT_MANIFEST_SHA256,
            "Campaign004 snapshot manifest",
        )
        _validate_snapshot_manifest(
            research.load_json_record(final_manifest),
            require_fingerprint_constants=True,
        )
        return final_manifest
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise Campaign004FeatureError("external data root has less than 10 GiB free")

    candidate49_spec = candidate49.load_preregistration()
    chain = candidate49.validate_external_chain(candidate49_spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    _, joint_by_key, by_symbol = market._partition_maps(raw, joint)
    if len(joint_by_key) != EXPECTED_PARTITIONS or len(by_symbol) != EXPECTED_SYMBOLS:
        raise Campaign004FeatureError("Campaign004 source partition map changed")
    benchmark = _load_market_benchmark(data_root)
    lock_path = data_root / ".a_share_walkforward_campaign004_features.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {EXPECTED_PARTITIONS:,} Campaign004 partitions across "
            f"{EXPECTED_SYMBOLS:,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
                    benchmark=benchmark,
                ): symbol
                for symbol, pairs in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(dates)
                    resumed += resumed_count
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"Campaign004 progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{len(joint_by_key):,} resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != EXPECTED_PARTITIONS:
            raise Campaign004FeatureError(
                "not every source partition produced a Campaign004 checkpoint"
            )
        _require_file(
            Path(raw_manifest_path),
            market.RAW_MANIFEST_SHA256,
            "raw minute manifest",
        )
        _require_file(
            Path(joint_manifest_path),
            market.JOINT_MANIFEST_SHA256,
            "joint-clean manifest",
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        factor_eligible_rows = {
            name: int(
                sum(
                    int((record.get("factor_eligible_rows") or {}).get(name, 0))
                    for record in all_records
                )
            )
            for name in FACTOR_NAMES
        }
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        eligible_names_by_date: dict[str, dict[str, int]] = {
            name: {} for name in FACTOR_NAMES
        }
        for key, value in sorted(eligible_dates.items()):
            name, trade_date = key.split("|", 1)
            eligible_names_by_date[name][trade_date] = int(value)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign004_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
            "protocol_sha256": PROTOCOL_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": market.RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": market.JOINT_MANIFEST_SHA256,
            "market_benchmark_manifest_sha256": MARKET_SNAPSHOT_SHA256,
            "market_benchmark_byte_sha256": MARKET_BENCHMARK_BYTE_SHA256,
            "market_benchmark_frame_sha256": MARKET_BENCHMARK_FRAME_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_names": list(FACTOR_NAMES),
            "factor_directions": FACTOR_DIRECTIONS,
            "factor_formulas": FACTOR_FORMULAS,
            "factor_eligible_rows": factor_eligible_rows,
            "eligible_names_by_date": eligible_names_by_date,
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "quality": quality,
            "source_fields_read": list(RAW_COLUMNS),
            "source_open_high_low_or_volume_read": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "prospective_candidate_activation_created": False,
            "resumed_partitions": resumed,
            "protocol_evidence": {
                "campaign004_no_return_preregistration_sha256": PROTOCOL_SHA256,
                "candidate49_no_return_protocol_sha256": (
                    candidate49.PREREGISTRATION_SHA256
                ),
            },
        }
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
        foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, Any]:
    records = list(manifest.get("files") or [])
    root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[str, int, int]:
        path = Path(str(record["path"])).resolve()
        if path.parent.parent != root:
            raise Campaign004FeatureError(f"snapshot partition escapes root: {path}")
        _require_file(
            path,
            str(record["output_byte_sha256"]),
            "Campaign004 snapshot partition",
        )
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if (
            len(frame) != int(record["rows"])
            or foundation.frame_digest(frame) != record["output_frame_sha256"]
        ):
            raise Campaign004FeatureError(f"snapshot partition frame changed: {path}")
        return str(record["symbol"]), int(record["year"]), len(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        verified = list(pool.map(verify, records))
    if len(verified) != EXPECTED_PARTITIONS or sum(item[2] for item in verified) != EXPECTED_ROWS:
        raise Campaign004FeatureError("Campaign004 snapshot aggregate changed")
    return {
        "verified_partitions": len(verified),
        "verified_rows": sum(item[2] for item in verified),
        "all_partition_byte_and_frame_hashes_valid": True,
    }


def load_factor_frame(
    manifest_path: Path,
    manifest: dict[str, Any],
    factor: str,
) -> pd.DataFrame:
    records = list(manifest.get("files") or [])
    if len(records) != EXPECTED_PARTITIONS:
        raise Campaign004FeatureError(
            "Campaign004 manifest partition count changed before factor load"
        )
    dataset = pa_dataset.dataset(
        [str(Path(str(record["path"])).resolve()) for record in records],
        format="parquet",
    )
    columns = ["trade_date", "symbol", factor, f"{factor}_eligible"]
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise Campaign004FeatureError(f"{factor} row count changed")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{factor}_eligible"] = (
        frame[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[factor] = pd.to_numeric(frame[factor], errors="coerce")
    eligible = frame[f"{factor}_eligible"]
    values = frame.loc[eligible, factor].to_numpy(dtype=float)
    lower, upper = FACTOR_RANGES[factor]
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < lower).any()
        or (values > upper).any()
        or frame.loc[~eligible, factor].notna().any()
    ):
        raise Campaign004FeatureError(f"{factor} values or keys are invalid")
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
    factor: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    merged = eligible_keys.merge(
        candidate,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    candidate_eligible = (
        merged[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
        & pd.to_numeric(merged[factor], errors="coerce").notna()
    )
    denominators = merged.groupby("trade_date", observed=True, sort=True).size()
    numerators = (
        merged.loc[candidate_eligible]
        .groupby("trade_date", observed=True, sort=True)
        .size()
        .reindex(denominators.index, fill_value=0)
    )
    ratios = numerators / denominators
    gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    indices = np.arange(
        0,
        max(len(denominators) - int(gate["holding_period_sessions"]), 0),
        int(gate["holding_period_sessions"]),
    )
    minimum_names = int(gate["minimum_p05_eligible_names"])
    potential_mask = numerators.iloc[indices].ge(minimum_names)
    potential = int(potential_mask.sum())
    cohort_years = sorted(
        int(value)
        for value in pd.DatetimeIndex(
            numerators.index[indices][potential_mask]
        ).year.unique()
    )
    daily = pd.DataFrame(
        {
            "trade_date": denominators.index,
            "quality_listing_eligible_names": denominators.to_numpy(dtype=int),
            "candidate_eligible_names": numerators.to_numpy(dtype=int),
            "coverage": ratios.to_numpy(dtype=float),
        }
    )
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    names_p05 = float(numerators.quantile(0.05))
    passed = bool(
        median >= float(gate["minimum_median_coverage"])
        and p05 >= float(gate["minimum_p05_coverage"])
        and names_p05 >= minimum_names
        and potential >= int(gate["minimum_non_overlapping_three_session_cohorts"])
        and len(cohort_years) >= int(gate["minimum_observed_calendar_years"])
    )
    result = {
        "quality_listing_eligible_rows": int(len(eligible_keys)),
        "candidate_eligible_rows": int(candidate_eligible.sum()),
        "calendar_sessions": int(len(denominators)),
        "median_coverage": median,
        "p05_coverage": p05,
        "eligible_names_min": int(numerators.min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(numerators.median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": cohort_years,
        "daily_coverage_frame_sha256": research.dataframe_content_sha256(daily),
        "worst_ten_sessions": [
            {
                "trade_date": pd.Timestamp(row.trade_date).date().isoformat(),
                "quality_listing_eligible_names": int(
                    row.quality_listing_eligible_names
                ),
                "candidate_eligible_names": int(row.candidate_eligible_names),
                "coverage": float(row.coverage),
            }
            for row in daily.sort_values(["coverage", "trade_date"], kind="stable")
            .head(10)
            .itertuples(index=False)
        ],
        "gate": {
            key: gate[key]
            for key in (
                "minimum_median_coverage",
                "minimum_p05_coverage",
                "minimum_p05_eligible_names",
                "minimum_non_overlapping_three_session_cohorts",
                "minimum_observed_calendar_years",
            )
        },
        "gate_passed_before_comparison_values": passed,
    }
    return merged.loc[
        candidate_eligible,
        ["trade_date", "symbol", factor],
    ], result


def _comparison_chain(
    data_root: Path,
) -> tuple[tuple[Any, ...], Path, dict[str, Any]]:
    spec = candidate49.load_preregistration()
    chain = candidate49.validate_external_chain(spec, data_root)
    candidate49_manifest_path = (
        candidate49.output_root(data_root) / "snapshot_manifest.json"
    )
    _require_file(
        candidate49_manifest_path,
        candidate49.CANDIDATE_MANIFEST_SHA256,
        "Candidate49 no-return snapshot",
    )
    candidate49_manifest = research.load_json_record(candidate49_manifest_path)
    candidate49._validate_snapshot_manifest(
        candidate49_manifest,
        require_fingerprint_constants=True,
    )
    return chain, candidate49_manifest_path, candidate49_manifest


def _sorted_candidate_arrays(
    candidate_quality: pd.DataFrame,
    factor: str,
) -> tuple[np.ndarray, np.ndarray]:
    keys = comparison_engine._compact_stock_day_keys(
        candidate_quality["trade_date"],
        candidate_quality["symbol"],
    )
    values = pd.to_numeric(
        candidate_quality[factor],
        errors="coerce",
    ).to_numpy(dtype=float)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys) or not np.isfinite(values).all():
        raise Campaign004FeatureError(f"{factor} candidate keys changed")
    return keys, values


def _load_filtered_comparison_values_explicit(
    manifest: dict[str, Any],
    factors: Iterable[str],
    candidate_keys: np.ndarray,
) -> dict[str, np.ndarray]:
    """Load only manifest-listed files, avoiding recursive directory discovery."""

    factors = tuple(str(value) for value in factors)
    records = list(manifest.get("files") or [])
    if len(records) != EXPECTED_PARTITIONS:
        raise Campaign004FeatureError(
            "explicit comparison manifest partition count changed"
        )
    paths = [str(Path(str(record["path"])).resolve()) for record in records]
    if len(paths) != len(set(paths)):
        raise Campaign004FeatureError(
            "explicit comparison manifest contains duplicate paths"
        )
    dataset = pa_dataset.dataset(paths, format="parquet")
    scanner = dataset.scanner(
        columns=["trade_date", "symbol", *factors],
        batch_size=262_144,
        use_threads=True,
    )
    candidate_keys = np.asarray(candidate_keys, dtype=np.int64)
    selected_keys: list[np.ndarray] = []
    selected_values: dict[str, list[np.ndarray]] = {
        factor: [] for factor in factors
    }
    total_rows = 0
    for batch in scanner.to_batches():
        frame = batch.to_pandas(split_blocks=True, self_destruct=True)
        total_rows += len(frame)
        keys = comparison_engine._compact_stock_day_keys(
            frame["trade_date"],
            frame["symbol"],
        )
        positions = np.searchsorted(candidate_keys, keys, side="left")
        bounded = positions < len(candidate_keys)
        matched = np.zeros(len(keys), dtype=bool)
        matched[bounded] = candidate_keys[positions[bounded]] == keys[bounded]
        if matched.any():
            selected_keys.append(keys[matched])
            for factor in factors:
                selected_values[factor].append(
                    pd.to_numeric(
                        frame.loc[matched, factor],
                        errors="coerce",
                    ).to_numpy(dtype=float)
                )
        del frame, keys, positions, bounded, matched, batch
    del scanner, dataset
    gc.collect()
    if total_rows != EXPECTED_ROWS:
        raise Campaign004FeatureError(
            f"explicit comparison snapshot row count changed: {total_rows}"
        )
    observed_keys = (
        np.concatenate(selected_keys)
        if selected_keys
        else np.empty(0, dtype=np.int64)
    )
    if len(observed_keys) != len(candidate_keys):
        raise Campaign004FeatureError(
            "explicit comparison snapshot does not cover every candidate key"
        )
    order = np.argsort(observed_keys, kind="stable")
    observed_keys = observed_keys[order]
    if (
        len(np.unique(observed_keys)) != len(observed_keys)
        or not np.array_equal(observed_keys, candidate_keys)
    ):
        raise Campaign004FeatureError(
            "explicit comparison snapshot stock-day keys changed"
        )
    aligned: dict[str, np.ndarray] = {}
    for factor in factors:
        values = (
            np.concatenate(selected_values[factor])
            if selected_values[factor]
            else np.empty(0, dtype=float)
        )
        aligned[factor] = values[order]
    return aligned


def _uniqueness_against_frozen_library(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    chain: tuple[Any, ...],
    candidate49_manifest_path: Path,
    candidate49_manifest: dict[str, Any],
    gate: dict[str, Any],
    workers: int,
    frozen_verifications: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    verifications: dict[str, Any] = dict(frozen_verifications or {})
    directions = (*candidate49.COMPARISON_DIRECTIONS, "higher")
    joint_manifest = chain[1]
    base_factors = candidate49.COMPARISON_FACTORS[:4]
    base_values = _load_filtered_comparison_values_explicit(
        joint_manifest,
        base_factors,
        candidate_keys,
    )
    for factor, direction in zip(base_factors, directions[:4], strict=True):
        results.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=base_values.pop(factor),
                comparison=factor,
                direction=direction,
                gate=gate,
            )
        )
    del base_values
    gc.collect()
    comparison_pairs = list(zip(chain[4::2], chain[5::2], strict=True))
    expected = candidate49.COMPARISON_FACTORS[4:]
    if (
        len(comparison_pairs) != len(expected)
        or tuple(str(item[0].get("factor_name")) for item in comparison_pairs)
        != expected
    ):
        raise Campaign004FeatureError("terminal comparison manifest order changed")
    for (manifest, path), factor, direction in zip(
        comparison_pairs,
        expected,
        directions[4:24],
        strict=True,
    ):
        path = Path(path)
        if factor not in verifications:
            verifications[factor] = (
                comparison_engine._verify_comparison_snapshot_outputs(
                    manifest,
                    path,
                    workers,
                )
            )
        values = _load_filtered_comparison_values_explicit(
            manifest,
            [factor],
            candidate_keys,
        )[factor]
        results.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=values,
                comparison=factor,
                direction=direction,
                gate=gate,
            )
        )
        del values
        gc.collect()
    if candidate49.FACTOR_NAME not in verifications:
        verifications[candidate49.FACTOR_NAME] = (
            candidate49.verify_snapshot_files(
                candidate49_manifest,
                candidate49_manifest_path,
                workers,
            )
        )
    values = _load_filtered_comparison_values_explicit(
        candidate49_manifest,
        [candidate49.FACTOR_NAME],
        candidate_keys,
    )[candidate49.FACTOR_NAME]
    results.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            comparison_values=values,
            comparison=candidate49.FACTOR_NAME,
            direction="higher",
            gate=gate,
        )
    )
    return results, verifications


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply ordered coverage then uniqueness gates to the frozen library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign004FeatureError(
            "bind the Campaign004 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        SNAPSHOT_MANIFEST_SHA256,
        "Campaign004 snapshot manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign004_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign004FeatureError(
                "existing Campaign004 audit is ambiguous or not fingerprint-bound"
            )
        _require_file(existing[0], NO_RETURN_AUDIT_SHA256, "Campaign004 audit")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    coverage_records: dict[str, dict[str, Any]] = {}
    quality_frames: dict[str, pd.DataFrame] = {}
    for index, factor in enumerate(FACTOR_NAMES, start=1):
        print(f"coverage gate {index}/3: {factor}", flush=True)
        candidate = load_factor_frame(manifest_path, manifest, factor)
        quality_frame, coverage = coverage_and_capacity(
            candidate,
            eligible_keys,
            spec,
            factor,
        )
        coverage_records[factor] = coverage
        if coverage["gate_passed_before_comparison_values"]:
            quality_frames[factor] = quality_frame
        del candidate
        gc.collect()
    del eligible_keys
    gc.collect()

    chain: tuple[Any, ...] | None = None
    candidate49_manifest_path: Path | None = None
    candidate49_manifest: dict[str, Any] | None = None
    if quality_frames:
        chain, candidate49_manifest_path, candidate49_manifest = _comparison_chain(
            data_root
        )
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    uniqueness_records: dict[str, dict[str, Any]] = {}
    prior_passers: list[str] = []
    frozen_verifications: dict[str, Any] | None = None
    for factor in FACTOR_NAMES:
        if factor not in quality_frames:
            uniqueness_records[factor] = {
                "comparison_values_loaded_after_coverage_pass": False,
                "comparisons": [],
                "all_required_comparisons_passed": False,
                "failure_reason": "coverage_gate_failed",
            }
            continue
        assert chain is not None
        assert candidate49_manifest_path is not None
        assert candidate49_manifest is not None
        print(f"uniqueness gate: {factor}", flush=True)
        keys, values = _sorted_candidate_arrays(quality_frames[factor], factor)
        comparisons, verifications = _uniqueness_against_frozen_library(
            candidate_keys=keys,
            candidate_values=values,
            chain=chain,
            candidate49_manifest_path=candidate49_manifest_path,
            candidate49_manifest=candidate49_manifest,
            gate=gate,
            workers=workers,
            frozen_verifications=frozen_verifications,
        )
        if frozen_verifications is None:
            frozen_verifications = dict(verifications)
        for prior_factor in prior_passers:
            prior_keys, prior_values = _sorted_candidate_arrays(
                quality_frames[prior_factor],
                prior_factor,
            )
            positions = np.searchsorted(prior_keys, keys)
            matched = (positions < len(prior_keys)) & (
                prior_keys[np.minimum(positions, len(prior_keys) - 1)] == keys
            )
            comparison_values = np.full(len(keys), np.nan, dtype=float)
            comparison_values[matched] = prior_values[positions[matched]]
            comparisons.append(
                comparison_engine._aligned_comparison_result(
                    candidate_keys=keys,
                    candidate_values=values,
                    comparison_values=comparison_values,
                    comparison=prior_factor,
                    direction="higher",
                    gate=gate,
                )
            )
        observed = [
            item["absolute_median_daily_rank_correlation"]
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            len(comparisons) == 25 + len(prior_passers)
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness_records[factor] = {
            "comparison_values_loaded_after_coverage_pass": True,
            "frozen_library_comparison_count": 25,
            "prior_campaign004_comparison_count": len(prior_passers),
            "prior_snapshot_file_verification": verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_comparisons_passed": passed,
        }
        if passed:
            prior_passers.append(factor)
        del keys, values
        gc.collect()
    admissible = [
        factor
        for factor in FACTOR_NAMES
        if coverage_records[factor]["gate_passed_before_comparison_values"]
        and uniqueness_records[factor]["all_required_comparisons_passed"]
    ]
    run_id = f"{research._timestamp()}_campaign004_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign004_no_return_audit",
        "status": (
            "completed_with_admissible_factors_pending_walkforward_preregistration"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": coverage_records,
        "uniqueness": uniqueness_records,
        "admissible_factor_names": admissible,
        "admissible_factor_count": len(admissible),
        "failed_factor_names": [
            factor for factor in FACTOR_NAMES if factor not in admissible
        ],
        "next_action": (
            "freeze the exact finite single-and-pair Campaign004 trial catalog "
            "before reading 2019-2023 returns"
            if admissible
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "candidate50_prospective_activation_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign004_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": bool(PROTOCOL_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = foundation.file_digest(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = foundation.file_digest(audits[-1])
        record = research.load_json_record(audits[-1])
        result["admissible_factor_names"] = record.get("admissible_factor_names")
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Build and no-return audit Campaign004 feature mechanisms."
    )
    subparsers = value.add_subparsers(dest="command", required=True)
    for name in ("build", "audit", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
        command.add_argument(
            "--experiment-root",
            default=str(DEFAULT_EXPERIMENT_ROOT),
        )
        if name in {"build", "audit"}:
            command.add_argument("--workers", type=int, default=4)
    return value


def main() -> int:
    args = parser().parse_args()
    data_root = Path(args.data_root)
    experiment_root = Path(args.experiment_root)
    if args.command == "build":
        result: Any = {
            "status": "snapshot_ready",
            "manifest_path": str(
                build_snapshot(data_root=data_root, workers=int(args.workers))
            ),
            "forward_return_fields_read": False,
        }
    elif args.command == "audit":
        result = {
            "status": "no_return_audit_ready",
            "audit_path": str(
                run_no_return_audit(
                    data_root=data_root,
                    experiment_root=experiment_root,
                    workers=int(args.workers),
                )
            ),
            "forward_return_fields_read": False,
        }
    else:
        result = status(data_root, experiment_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
