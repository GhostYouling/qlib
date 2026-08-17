#!/usr/bin/env python3
"""Build and no-return audit the cumulative-VWAP crossing-rate candidate.

The module reads only immutable Tushare minute identity, close, volume, and
amount fields.  It never reads historical daily prices or forward returns.
If all historical no-return gates pass, the unchanged factor may be
registered separately for observations first seen after registration.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_market_amount_profile_synchronization as previous  # noqa: E402
import a_share_tushare_intraday_opening_auction_amount_share as build_engine  # noqa: E402
from _a_share_runtime import resolve_data_root  # noqa: E402


foundation = previous.foundation
research = previous.research
comparison_engine = previous.engine
REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DATA_ROOT = resolve_data_root(REPO_ROOT)
DEFAULT_POLICY = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_future_only_minute_research_policy_20260725.json"
)
POLICY_SHA256 = "52ca8bfa7201509fe891d0af3d1c87aeebd64e47e6ec6641e897849411df408c"
DEFAULT_MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
        "mechanism_overlap_reaudit_20260725.json"
    )
)
MECHANISM_AUDIT_SHA256 = (
    "f86ba3cdfd7ead04963519e1c86e0d022467896a68ac3422fb5d742f716dcdcd"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
        "no_return_preregistration.json"
    )
)
PREREGISTRATION_SHA256 = (
    "cefa5f23b5214e123d0bdea1511a398cb4a70c0ee4cc8da7d1f69f52bdbe4aeb"
)
DEFAULT_CURRENT_STATUS = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260725.json"
)
CURRENT_STATUS_SHA256 = (
    "355b992452b73607034a182699d4fff337905e484229441e7ae138db1ffdefef"
)
PREVIOUS_TERMINAL_RECORD_SHA256 = previous.TERMINAL_RECORD_SHA256
PREVIOUS_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
PREVIOUS_DATASET_SHA256 = previous.CANDIDATE_DATASET_SHA256
RAW_MANIFEST_SHA256 = previous.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = previous.JOINT_MANIFEST_SHA256
SOURCE_RUN_ID = previous.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_cumulative_vwap_crossing_rate_v1"
FACTOR_NAME = "intraday_cumulative_vwap_crossing_rate_240m"
FACTOR_FORMULA = (
    "adjacent sign-change share after removing exact-zero signs from "
    "sign(log(close_t/(cumulative_amount_t/cumulative_volume_t))) across "
    "the exact 240-position continuous-session path"
)
COMPARISON_FACTORS = (*previous.COMPARISON_FACTORS, previous.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*previous.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "volume", "amount")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
CONTINUOUS_MINUTE_CODES = previous.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = frozenset(CONTINUOUS_MINUTE_CODES)
ENDPOINT_TOLERANCE = 1e-12

# Bound after the first deterministic no-return build.
CANDIDATE_MANIFEST_SHA256 = (
    "f3dd3417bd6adcaa06d8927865ea3f464ebc02df302b8f488e43450f7c620196"
)
CANDIDATE_DATASET_SHA256 = (
    "67bda6df74747a0f39fe6eb252aada84ea7850fff2c05bdae4951aa41fcc7037"
)
EXPECTED_ELIGIBLE_ROWS = 7_714_026
EXPECTED_QUALITY: dict[str, int] = {
    "invalid_required_close_rows": 0,
    "invalid_required_volume_amount_rows": 0,
    "one_sided_zero_volume_or_amount_rows": 47,
    "fewer_than_two_valid_cumulative_vwap_positions_rows": 1,
    "fewer_than_two_nonzero_deviation_sign_rows": 10_425,
    "endpoint_canonicalized_rows": 0,
    "range_violation_rows": 0,
}
NO_RETURN_AUDIT_SHA256 = (
    "51bb248b1071983cf9a05fca94c6cc08770a2d10fbef1d6d087f2d5a875fdf7d"
)
DEFAULT_FUTURE_REGISTRATION = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
        "future_observation_registration.json"
    )
)
FUTURE_REGISTRATION_SHA256 = (
    "431cb0b3b078823f08b888bf4c499bcc5088309a2e58e9de5cb9a9aaa849ffa9"
)
DEFAULT_FUTURE_EXECUTION_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_candidate49_future_execution_protocol.json"
)
FUTURE_EXECUTION_PROTOCOL_SHA256 = (
    "b9b4ea8906924c8303cb7a434db5f21ed6383ce7d794e50936b675acfa869486"
)
DEFAULT_FUTURE_ONLY_STATUS = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260725_future_only.json"
)
FUTURE_ONLY_STATUS_SHA256 = (
    "d44e1cb3707cce194eed37e99cc90f865396b1de8c35e02a393a2a243d973466"
)
DEFAULT_PROVIDER_URI = ACTIVE_DATA_ROOT / "qlib" / "cn_a_share"
FUTURE_SIGNAL_LEDGER = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_signal_ledger.json"
)
FUTURE_EXECUTION_LEDGER = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_execution_ledger.json"
)
FUTURE_SIGNAL_LEDGER_KIND = (
    "a_share_tushare_intraday_cumulative_vwap_crossing_rate_future_signal_ledger"
)
FUTURE_EXECUTION_LEDGER_KIND = (
    "a_share_tushare_intraday_cumulative_vwap_crossing_rate_future_execution_ledger"
)
FUTURE_REGISTRATION_ID = "candidate49_intraday_cumulative_vwap_crossing_rate_240m_v1"
EARLIEST_FUTURE_SESSION = dt.date(2026, 7, 27)
SESSION_CLOSE_READINESS_TIME = dt.time(16, 30)
CHINA_TZ = ZoneInfo("Asia/Shanghai")


class IntradayCumulativeVwapCrossingRateError(RuntimeError):
    """Raised when a frozen source, formula, or no-return gate changes."""


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise IntradayCumulativeVwapCrossingRateError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


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


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if path != DEFAULT_PREREGISTRATION.resolve():
        raise IntradayCumulativeVwapCrossingRateError(
            "the cumulative-VWAP no-return protocol path is fixed"
        )
    _require_file(path, PREREGISTRATION_SHA256, "candidate 49 no-return protocol")
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
            "no_return_preregistration"
        ),
    )
    candidate = spec.get("candidate") or {}
    grid = candidate.get("bar_grid") or {}
    validity = candidate.get("validity") or {}
    coverage = (spec.get("ordered_no_return_gates") or {}).get(
        "coverage_and_capacity_before_comparison_values"
    ) or {}
    uniqueness = (spec.get("ordered_no_return_gates") or {}).get(
        "uniqueness_after_coverage_only"
    ) or {}
    comparisons = uniqueness.get("comparison_factors") or []
    observed_pairs = tuple(
        (str(item.get("name")), str(item.get("score_direction")))
        for item in comparisons
    )
    if not (
        spec.get("status")
        == (
            "frozen_before_candidate_factor_values_comparison_values_"
            "daily_prices_or_forward_returns"
        )
        and candidate.get("ordinal") == 49
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("prospective_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and grid.get("continuous_rows") == 240
        and grid.get("09_30_included") is False
        and grid.get("source_rows_merged") is False
        and validity.get("one_sided_zero_volume_or_amount_policy")
        == "whole_stock_day_missing"
        and validity.get("joint_zero_volume_amount_policy") == "inactive_bar_retained"
        and validity.get("minimum_nonzero_deviation_signs") == 2
        and validity.get("allowed_closed_interval") == [0, 1]
        and validity.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("holding_period_sessions") == 3
        and coverage.get("pilot_capital_cny") == 200_000
        and coverage.get("pilot_buy_lot_size_shares") == 100
        and uniqueness.get("screen_start") == "2019-01-01"
        and uniqueness.get("screen_end") == "2025-12-31"
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("all_twenty_four_comparisons_must_pass") is True
        and observed_pairs
        == tuple(zip(COMPARISON_FACTORS, COMPARISON_DIRECTIONS, strict=True))
        and (spec.get("post_no_return_decision") or {}).get(
            "historical_return_diagnostic_allowed"
        )
        is False
        and (spec.get("research_boundary") or {}).get(
            "historical_daily_price_fields_read"
        )
        is False
        and (spec.get("research_boundary") or {}).get(
            "historical_forward_return_fields_read"
        )
        is False
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 no-return protocol semantics changed"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    links = (
        (
            DEFAULT_POLICY,
            POLICY_SHA256,
            "future-only minute research policy",
        ),
        (
            DEFAULT_MECHANISM_AUDIT,
            MECHANISM_AUDIT_SHA256,
            "candidate 49 mechanism audit",
        ),
        (
            DEFAULT_CURRENT_STATUS,
            CURRENT_STATUS_SHA256,
            "current three-day iteration state",
        ),
        (
            previous.DEFAULT_TERMINAL_RECORD,
            PREVIOUS_TERMINAL_RECORD_SHA256,
            "candidate 48 terminal record",
        ),
    )
    evidence: dict[str, Any] = {}
    for path, expected, label in links:
        _require_file(path, expected, label)
        evidence[label.replace(" ", "_")] = {
            "path": str(path.resolve()),
            "sha256": expected,
        }
    source_chain = spec.get("source_chain") or {}
    if not (
        (source_chain.get("future_only_policy") or {}).get("sha256") == POLICY_SHA256
        and (source_chain.get("mechanism_overlap_reaudit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (source_chain.get("prior_terminal_record") or {}).get("sha256")
        == PREVIOUS_TERMINAL_RECORD_SHA256
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 repository source chain changed"
        )
    for name, record in (spec.get("point_in_time_context") or {}).items():
        if not isinstance(record, dict) or "path" not in record:
            continue
        path = _repository_path(str(record["path"]))
        expected = str(record["sha256"])
        _require_file(path, expected, f"point-in-time {name}")
        evidence[f"point_in_time_{name}"] = {
            "path": str(path),
            "sha256": expected,
        }
        manifest_path_value = record.get("manifest_path")
        if manifest_path_value:
            manifest_path = _repository_path(str(manifest_path_value))
            manifest_expected = str(record["manifest_sha256"])
            _require_file(
                manifest_path,
                manifest_expected,
                f"point-in-time {name} manifest",
            )
            evidence[f"point_in_time_{name}_manifest"] = {
                "path": str(manifest_path),
                "sha256": manifest_expected,
            }
    return evidence


def _validate_previous_manifest(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], Path]:
    link = (spec.get("source_chain") or {})["latest_comparison_manifest"]
    path = (data_root / str(link["path_below_data_root"])).resolve()
    _require_file(path, PREVIOUS_MANIFEST_SHA256, "candidate 48 manifest")
    manifest = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_" "synchronization_snapshot"
        ),
    )
    previous._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    if manifest.get("dataset_sha256") != PREVIOUS_DATASET_SHA256:
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 48 comparison dataset changed"
        )
    return manifest, path


def validate_external_chain(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[Any, ...]:
    chain = previous.validate_external_chain(
        previous.load_preregistration(),
        data_root,
    )
    prior_manifest, prior_path = _validate_previous_manifest(spec, data_root)
    return (*chain, prior_manifest, prior_path)


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute exact cumulative-VWAP crossing rate without daily prices."""

    quality_names = (
        "base_rows",
        "eligible_rows",
        "invalid_required_close_rows",
        "invalid_required_volume_amount_rows",
        "one_sided_zero_volume_or_amount_rows",
        "fewer_than_two_valid_cumulative_vwap_positions_rows",
        "fewer_than_two_nonzero_deviation_sign_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    empty_quality = {name: 0 for name in quality_names}
    if tuple(raw.columns) != RAW_COLUMNS:
        raise IntradayCumulativeVwapCrossingRateError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = build_engine.previous._normalized_base(base, symbol)
    if base_work.empty:
        return empty_output_frame(), empty_quality
    symbol = symbol.upper()
    if raw.empty:
        raise IntradayCumulativeVwapCrossingRateError(
            f"raw source is empty for nonempty base partition {symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("close", "volume", "amount"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            f"raw identity or timestamp violation for {symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    work = work.loc[
        work["trade_date"].isin(base_work["trade_date"])
        & work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET)
    ].copy()
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(240).all():
        raise IntradayCumulativeVwapCrossingRateError(
            f"every candidate stock-day must retain the exact 240-row grid for {symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(CONTINUOUS_MINUTE_CODE_SET).all():
        raise IntradayCumulativeVwapCrossingRateError(
            f"continuous-session minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise IntradayCumulativeVwapCrossingRateError(
            f"joint-clean base dates do not match raw dates for {symbol}"
        )
    work["minute_code"] = pd.Categorical(
        work["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    work = work.sort_values(["trade_date", "minute_code"], kind="stable")
    closes = work["close"].to_numpy(dtype=float).reshape(-1, 240)
    volumes = work["volume"].to_numpy(dtype=float).reshape(-1, 240)
    amounts = work["amount"].to_numpy(dtype=float).reshape(-1, 240)
    valid_close = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    valid_volume_amount = (
        np.isfinite(volumes).all(axis=1)
        & np.isfinite(amounts).all(axis=1)
        & (volumes >= 0.0).all(axis=1)
        & (amounts >= 0.0).all(axis=1)
    )
    one_sided_zero = ((volumes == 0.0) ^ (amounts == 0.0)).any(axis=1)
    required_valid = valid_close & valid_volume_amount & ~one_sided_zero
    cumulative_volume = np.cumsum(
        np.where(required_valid[:, None], volumes, 0.0),
        axis=1,
    )
    cumulative_amount = np.cumsum(
        np.where(required_valid[:, None], amounts, 0.0),
        axis=1,
    )
    cumulative_valid = (
        required_valid[:, None]
        & np.isfinite(cumulative_volume)
        & np.isfinite(cumulative_amount)
        & (cumulative_volume > 0.0)
        & (cumulative_amount > 0.0)
    )
    active_bar = (volumes > 0.0) & (amounts > 0.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        deviations = np.log(closes * cumulative_volume / cumulative_amount)
    finite_deviation = cumulative_valid & active_bar & np.isfinite(deviations)
    signs = np.where(
        finite_deviation & (deviations > 0.0),
        1,
        np.where(finite_deviation & (deviations < 0.0), -1, 0),
    ).astype(np.int8)
    nonzero = signs != 0
    nonzero_counts = nonzero.sum(axis=1)
    positions = np.broadcast_to(np.arange(240, dtype=np.int16), signs.shape)
    last_nonzero = np.maximum.accumulate(
        np.where(nonzero, positions, -1),
        axis=1,
    )
    previous_index = np.empty_like(last_nonzero)
    previous_index[:, 0] = -1
    previous_index[:, 1:] = last_nonzero[:, :-1]
    gathered_previous = np.take_along_axis(
        signs,
        np.maximum(previous_index, 0),
        axis=1,
    )
    crossings = (nonzero & (previous_index >= 0) & (signs != gathered_previous)).sum(
        axis=1
    )
    denominators = nonzero_counts - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        values = crossings / denominators
    finite = np.isfinite(values)
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = (
        required_valid & (nonzero_counts >= 2) & finite & (low_near | high_near)
    )
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = required_valid & (nonzero_counts >= 2) & finite & in_range
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol,
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    valid_cumulative_counts = finite_deviation.sum(axis=1)
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "invalid_required_close_rows": int((~valid_close).sum()),
        "invalid_required_volume_amount_rows": int((~valid_volume_amount).sum()),
        "one_sided_zero_volume_or_amount_rows": int(one_sided_zero.sum()),
        "fewer_than_two_valid_cumulative_vwap_positions_rows": int(
            (required_valid & (valid_cumulative_counts < 2)).sum()
        ),
        "fewer_than_two_nonzero_deviation_sign_rows": int(
            (required_valid & (nonzero_counts < 2)).sum()
        ),
        "endpoint_canonicalized_rows": int(canonicalized.sum()),
        "range_violation_rows": int(
            (required_valid & (nonzero_counts >= 2) & finite & ~in_range).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_intraday_cumulative_vwap_crossing_rate"
        / OUTPUT_RUN_ID
    )


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: Any,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind")
        == "a_share_tushare_intraday_cumulative_vwap_crossing_rate_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256")
        == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and foundation.file_digest(raw_path) == raw_record.get("byte_sha256")
        and foundation.file_digest(base_path) == joint_record.get("output_byte_sha256")
        and foundation.file_digest(paths.partial_data)
        == record.get("output_byte_sha256")
    )
    if not valid:
        raise IntradayCumulativeVwapCrossingRateError(
            f"completed candidate checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise IntradayCumulativeVwapCrossingRateError(
            f"completed candidate frame changed: {paths.partial_data}"
        )
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates


def _process_partition(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = foundation.partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayCumulativeVwapCrossingRateError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayCumulativeVwapCrossingRateError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    output, quality = compute_partition_frame(
        raw,
        base,
        symbol=str(joint_record["symbol"]),
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_cumulative_vwap_crossing_rate_partition",
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "output_run_id": OUTPUT_RUN_ID,
        "symbol": str(joint_record["symbol"]),
        "code": str(joint_record["code"]),
        "year": int(joint_record["year"]),
        "raw_source_path": str(raw_path),
        "raw_source_rows": int(raw_record["rows"]),
        "raw_source_byte_sha256": str(raw_record["byte_sha256"]),
        "joint_base_path": str(base_path),
        "joint_base_rows": int(joint_record["rows"]),
        "joint_base_byte_sha256": str(joint_record["output_byte_sha256"]),
        "path": str(paths.final_data),
        "sidecar_path": str(paths.final_sidecar),
        "rows": int(len(output)),
        "eligible_rows": int(output[f"{FACTOR_NAME}_eligible"].sum()),
        "output_byte_sha256": foundation.file_digest(paths.partial_data),
        "output_frame_sha256": foundation.frame_digest(output),
        "quality": quality,
        "source_fields_read": list(RAW_COLUMNS),
        "minute_close_volume_amount_fields_read": ["close", "volume", "amount"],
        "source_open_high_low_read": False,
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    foundation.atomic_write_json(record, paths.partial_sidecar)
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates, False


def _process_symbol(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    eligible_dates: Counter[str] = Counter()
    resumed = 0
    for raw_record, joint_record in sorted(
        pairs,
        key=lambda pair: int(pair[1]["year"]),
    ):
        record, dates, was_resumed = _process_partition(
            raw_record,
            joint_record,
            partial_root=partial_root,
            final_root=final_root,
        )
        records.append(record)
        eligible_dates.update(dates)
        resumed += int(was_resumed)
    return records, eligible_dates, resumed


def _aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for record in records:
        total.update({key: int(value) for key, value in record["quality"].items()})
    return dict(total)


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    quality = manifest.get("quality") or {}
    quality_names = (
        "invalid_required_close_rows",
        "invalid_required_volume_amount_rows",
        "one_sided_zero_volume_or_amount_rows",
        "fewer_than_two_valid_cumulative_vwap_positions_rows",
        "fewer_than_two_nonzero_deviation_sign_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    if not (
        manifest.get("kind")
        == "a_share_tushare_intraday_cumulative_vwap_crossing_rate_snapshot"
        and manifest.get("status")
        == (
            "candidate_feature_complete_pending_ordered_no_return_"
            "coverage_capacity_and_uniqueness"
        )
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("factor_formula") == FACTOR_FORMULA
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and all(
            isinstance(quality.get(name), int) and quality.get(name) >= 0
            for name in quality_names
        )
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_close_volume_amount_read") is True
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("cumulative_vwap_is_causal") is True
        and manifest.get("one_sided_zero_invalidates_stock_day") is True
        and manifest.get("joint_zero_bar_retained_as_inactive") is True
        and manifest.get("exact_zero_deviation_sign_removed") is True
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("historical_return_diagnostic_allowed") is False
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 snapshot identity is rejected"
        )
    if require_fingerprint_constants and not (
        CANDIDATE_MANIFEST_SHA256
        and CANDIDATE_DATASET_SHA256
        and EXPECTED_ELIGIBLE_ROWS > 0
        and manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and all(quality.get(key) == value for key, value in EXPECTED_QUALITY.items())
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 fingerprint and aggregate constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all candidate partitions without provider or return access."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise IntradayCumulativeVwapCrossingRateError(
                f"published candidate root has no manifest: {final_root}"
            )
        if not CANDIDATE_MANIFEST_SHA256:
            raise IntradayCumulativeVwapCrossingRateError(
                "bind the published candidate manifest before reusing it"
            )
        _require_file(
            final_manifest,
            CANDIDATE_MANIFEST_SHA256,
            "published candidate 49 manifest",
        )
        manifest = research.load_json_record(final_manifest)
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
        return final_manifest
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise IntradayCumulativeVwapCrossingRateError(
            "external data root has less than 5 GiB free"
        )
    _, joint_by_key, by_symbol = build_engine.previous._partition_maps(raw, joint)
    lock_path = (
        data_root / ".a_share_tushare_intraday_cumulative_vwap_crossing_rate.lock"
    )
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_by_key):,} cumulative-VWAP crossing partitions "
            f"across {len(by_symbol):,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
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
                    if completed_symbols % 50 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"candidate progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{len(joint_by_key):,} "
                            f"eligible_rows={sum(eligible_dates.values()):,} "
                            f"resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != 33_015:
            raise IntradayCumulativeVwapCrossingRateError(
                "not every source partition produced a candidate checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path,
            JOINT_MANIFEST_SHA256,
            "joint-clean manifest",
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_intraday_cumulative_vwap_crossing_rate_snapshot",
            "status": (
                "candidate_feature_complete_pending_ordered_no_return_"
                "coverage_capacity_and_uniqueness"
            ),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PREREGISTRATION.resolve()),
            "protocol_sha256": PREREGISTRATION_SHA256,
            "future_only_policy_path": str(DEFAULT_POLICY.resolve()),
            "future_only_policy_sha256": POLICY_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_name": FACTOR_NAME,
            "factor_direction": "higher",
            "factor_formula": FACTOR_FORMULA,
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "eligible_rows": int(quality.get("eligible_rows", -1)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": list(RAW_COLUMNS),
            "source_close_volume_amount_read": True,
            "source_open_high_low_read": False,
            "standalone_09_30_row_excluded_from_formula": True,
            "continuous_session_positions": 240,
            "cumulative_vwap_is_causal": True,
            "one_sided_zero_invalidates_stock_day": True,
            "joint_zero_bar_retained_as_inactive": True,
            "exact_zero_deviation_sign_removed": True,
            "source_rows_merged": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "historical_return_diagnostic_allowed": False,
            "provider_request_issued": False,
            "training_or_model_fitting_performed": False,
            "aggregation_scoring_selection_sizing_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed,
            "repository_evidence": repository_evidence,
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
) -> dict[str, int]:
    records = list(manifest.get("files") or [])
    if len(records) != 33_015:
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 snapshot partition count changed"
        )
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise IntradayCumulativeVwapCrossingRateError(
                f"candidate partition escapes its frozen root: {path}"
            ) from exc
        _require_file(path, str(record["output_byte_sha256"]), "candidate partition")
        _require_file(
            Path(str(record["raw_source_path"])),
            str(record["raw_source_byte_sha256"]),
            "raw source partition",
        )
        _require_file(
            Path(str(record["joint_base_path"])),
            str(record["joint_base_byte_sha256"]),
            "joint-base partition",
        )
        return int(record["rows"]), int(record["eligible_rows"]), path.stat().st_size

    rows = eligible = byte_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for index, result in enumerate(pool.map(verify, records), start=1):
            partition_rows, partition_eligible, partition_bytes = result
            rows += partition_rows
            eligible += partition_eligible
            byte_count += partition_bytes
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified candidate partitions {index}/{len(records)}",
                    flush=True,
                )
    if rows != manifest.get("rows") or eligible != manifest.get("eligible_rows"):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate snapshot aggregate counts changed"
        )
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
    }


def load_candidate_frame(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    dataset = pa_dataset.dataset(
        str(manifest_path.parent / "partitions"),
        format="parquet",
    )
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate frame row count changed"
        )
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"],
        errors="coerce",
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{FACTOR_NAME}_eligible"] = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[FACTOR_NAME] = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"]
    values = frame.loc[eligible, FACTOR_NAME].to_numpy(dtype=float)
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < 0.0).any()
        or (values > 1.0).any()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate frame values or keys are invalid"
        )
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    original_name = build_engine.FACTOR_NAME
    build_engine.FACTOR_NAME = FACTOR_NAME
    try:
        return build_engine.coverage_and_capacity(candidate, eligible_keys, spec)
    finally:
        build_engine.FACTOR_NAME = original_name


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    chain: tuple[Any, ...],
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    """Evaluate all 24 terminal comparisons serially with bounded memory."""

    print(
        "coverage passed; loading twenty-four terminal comparisons serially",
        flush=True,
    )
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    candidate = candidate_quality[["trade_date", "symbol", FACTOR_NAME]].copy()
    candidate_keys = comparison_engine._compact_stock_day_keys(
        candidate["trade_date"],
        candidate["symbol"],
    )
    candidate_values = pd.to_numeric(
        candidate[FACTOR_NAME],
        errors="coerce",
    ).to_numpy(dtype=float)
    order = np.argsort(candidate_keys, kind="stable")
    candidate_keys = candidate_keys[order]
    candidate_values = candidate_values[order]
    if (
        len(np.unique(candidate_keys)) != len(candidate_keys)
        or not np.isfinite(candidate_values).all()
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate quality keys or values changed before uniqueness"
        )
    del candidate, candidate_quality, order
    gc.collect()
    results: list[dict[str, Any]] = []
    verifications: dict[str, Any] = {}
    joint_manifest_path = Path(chain[3])
    base_factors = COMPARISON_FACTORS[:4]
    base_values = comparison_engine._load_filtered_comparison_values(
        joint_manifest_path.parent / "partitions",
        base_factors,
        candidate_keys,
    )
    for factor, direction in zip(
        base_factors,
        COMPARISON_DIRECTIONS[:4],
        strict=True,
    ):
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
    expected_factors = COMPARISON_FACTORS[4:]
    if (
        len(comparison_pairs) != len(expected_factors)
        or tuple(str(manifest.get("factor_name")) for manifest, _ in comparison_pairs)
        != expected_factors
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "comparison manifest order changed"
        )
    for index, ((manifest, manifest_path), factor, direction) in enumerate(
        zip(
            comparison_pairs,
            expected_factors,
            COMPARISON_DIRECTIONS[4:],
            strict=True,
        ),
        start=5,
    ):
        manifest_path = Path(manifest_path)
        print(f"serial uniqueness comparison {index}/24: {factor}", flush=True)
        verifications[factor] = comparison_engine._verify_comparison_snapshot_outputs(
            manifest,
            manifest_path,
            workers,
        )
        values = comparison_engine._load_filtered_comparison_values(
            manifest_path.parent / "partitions",
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
    observed = [
        item["absolute_median_daily_rank_correlation"]
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    return {
        "comparison_values_loaded_after_coverage_pass": True,
        "comparison_field_count": len(results),
        "prior_candidate_snapshot_file_verification": verifications,
        "minimum_pairwise_names_per_session": int(
            gate["minimum_pairwise_names_per_session"]
        ),
        "minimum_pairwise_sessions_per_comparison": int(
            gate["minimum_pairwise_sessions_per_comparison"]
        ),
        "maximum_allowed_absolute_median_daily_rank_correlation": float(
            gate["maximum_allowed_absolute_median_daily_rank_correlation"]
        ),
        "comparisons": results,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "base_four_comparisons_passed": bool(
            len(results) >= 4 and all(item["gate_passed"] for item in results[:4])
        ),
        "all_twenty_four_comparisons_passed": bool(
            len(results) == 24 and all(item["gate_passed"] for item in results)
        ),
    }


def _find_existing_audit(
    experiment_root: Path,
    manifest_sha256: str,
) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_intraday_cumulative_vwap_crossing_rate_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == (
                "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
                "no_return_audit"
            )
            and (record.get("candidate_snapshot") or {}).get("sha256")
            == manifest_sha256
        ):
            return path
    return None


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Run coverage/capacity before loading the 24 comparisons."""

    if not CANDIDATE_MANIFEST_SHA256:
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate snapshot fingerprint must be bound before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "candidate 49 manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        if not NO_RETURN_AUDIT_SHA256:
            raise IntradayCumulativeVwapCrossingRateError(
                "bind the completed no-return audit before reusing it"
            )
        _require_file(existing, NO_RETURN_AUDIT_SHA256, "candidate 49 no-return audit")
        return existing
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    candidate = load_candidate_frame(manifest_path, manifest)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate_quality, coverage = coverage_and_capacity(candidate, eligible_keys, spec)
    del candidate, eligible_keys
    gc.collect()
    uniqueness: dict[str, Any] = {
        "comparison_values_loaded_after_coverage_pass": False,
        "all_twenty_four_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, chain, spec, workers)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_twenty_four_comparisons_passed"]
    )
    status = (
        "passed_no_return_gates_pending_future_only_registration"
        if passed
        else "terminally_rejected_by_ordered_no_return_gate_without_historical_return_read"
    )
    run_id = (
        f"{research._timestamp()}_intraday_cumulative_vwap_"
        "crossing_rate_no_return_audit"
    )
    audit = {
        "schema_version": 1,
        "kind": (
            "a_share_tushare_intraday_cumulative_vwap_crossing_rate_" "no_return_audit"
        ),
        "status": status,
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
        },
        "future_only_policy": {
            "path": str(DEFAULT_POLICY.resolve()),
            "sha256": POLICY_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "dataset_sha256": manifest["dataset_sha256"],
            "factor_name": FACTOR_NAME,
            "factor_direction": "higher",
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": coverage,
        "uniqueness": uniqueness,
        "repository_evidence": repository_evidence,
        "source_fields_read": list(RAW_COLUMNS),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "aggregation_scoring_selection_sizing_or_orders_performed": False,
        "future_only_registration_allowed": passed,
        "historical_return_diagnostic_allowed": False,
        "candidate_50_activation_allowed": False,
        "decision": (
            "freeze one append-only future-only registration for the unchanged "
            "candidate before its first eligible signal"
            if passed
            else (
                "retire the exact candidate without inversion, formula or window "
                "change, historical return access, or replacement"
            )
        ),
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(audit, destination)
    return destination


def load_future_registration() -> dict[str, Any]:
    """Validate the immutable future-only registration."""

    _require_file(
        DEFAULT_FUTURE_REGISTRATION,
        FUTURE_REGISTRATION_SHA256,
        "candidate 49 future-only registration",
    )
    record = research.load_json_record(
        DEFAULT_FUTURE_REGISTRATION,
        kind=(
            "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
            "future_observation_registration"
        ),
    )
    evidence = record.get("source_evidence") or {}
    factor = record.get("factor") or {}
    boundary = record.get("future_data_boundary") or {}
    decision = record.get("decision") or {}
    if not (
        record.get("status")
        == "prospective_observation_registered_pending_first_future_source_session"
        and record.get("registration_id")
        == "candidate49_intraday_cumulative_vwap_crossing_rate_240m_v1"
        and (evidence.get("future_only_policy") or {}).get("sha256") == POLICY_SHA256
        and (evidence.get("mechanism_overlap_reaudit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (evidence.get("no_return_preregistration") or {}).get("sha256")
        == PREREGISTRATION_SHA256
        and (evidence.get("historical_candidate_snapshot") or {}).get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (evidence.get("historical_candidate_snapshot") or {}).get("dataset_sha256")
        == CANDIDATE_DATASET_SHA256
        and (evidence.get("ordered_no_return_audit") or {}).get("sha256")
        == NO_RETURN_AUDIT_SHA256
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and tuple(factor.get("source_fields") or ()) == RAW_COLUMNS
        and boundary.get("earliest_eligible_signal_session")
        == "the first accepted local provider-calendar session on or after 2026-07-27"
        and boundary.get("backfill_before_registration_allowed") is False
        and decision.get("historical_return_diagnostic_allowed") is False
        and decision.get("future_observation_registered") is True
        and decision.get("current_signal_exists") is False
        and decision.get("aggregation_allowed") is False
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 future-only registration semantics changed"
        )
    return record


def load_future_execution_protocol() -> dict[str, Any]:
    """Validate the supplemental paper-execution protocol without outcomes."""

    _require_file(
        DEFAULT_FUTURE_EXECUTION_PROTOCOL,
        FUTURE_EXECUTION_PROTOCOL_SHA256,
        "candidate 49 future execution protocol",
    )
    record = research.load_json_record(
        DEFAULT_FUTURE_EXECUTION_PROTOCOL,
        kind="a_share_tushare_candidate49_future_execution_protocol",
    )
    registration = (
        (record.get("source_chain") or {}).get(
            "future_observation_registration"
        )
        or {}
    )
    current = record.get("current_state") or {}
    if not (
        record.get("status")
        == "frozen_before_first_eligible_future_signal_entry_open_or_outcome"
        and record.get("registration_id") == FUTURE_REGISTRATION_ID
        and registration.get("sha256") == FUTURE_REGISTRATION_SHA256
        and (record.get("portfolio") or {}).get("paper_only") is True
        and current.get("real_future_signal_count") == 0
        and current.get("real_entry_count") == 0
        and current.get("real_exit_count") == 0
        and current.get("completed_future_rank_ic_count") == 0
        and current.get("portfolio_return_exists") is False
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 future execution protocol semantics changed"
        )
    return record


def _ledger_genesis(kind: str) -> str:
    payload = f"{FUTURE_REGISTRATION_ID}|{FUTURE_REGISTRATION_SHA256}|{kind}|genesis"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ledger_entry_digest(entry: dict[str, Any]) -> str:
    payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _empty_future_ledger(kind: str) -> dict[str, Any]:
    genesis = _ledger_genesis(kind)
    return {
        "schema_version": 1,
        "kind": kind,
        "status": "empty_pending_first_eligible_future_session",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "registration_id": FUTURE_REGISTRATION_ID,
        "registration_sha256": FUTURE_REGISTRATION_SHA256,
        "future_only_policy_sha256": POLICY_SHA256,
        "append_only": True,
        "historical_backfill_allowed": False,
        "genesis_sha256": genesis,
        "entries": [],
        "chain_tip_sha256": genesis,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "provider_request_issued": False,
    }


def validate_future_ledger(path: Path, kind: str) -> dict[str, Any]:
    """Validate one logical append-only ledger and its complete hash chain."""

    path = path.expanduser().resolve()
    record = research.load_json_record(path, kind=kind)
    entries = record.get("entries")
    genesis = _ledger_genesis(kind)
    if not (
        record.get("schema_version") == 1
        and record.get("registration_id") == FUTURE_REGISTRATION_ID
        and record.get("registration_sha256") == FUTURE_REGISTRATION_SHA256
        and record.get("future_only_policy_sha256") == POLICY_SHA256
        and record.get("append_only") is True
        and record.get("historical_backfill_allowed") is False
        and record.get("genesis_sha256") == genesis
        and isinstance(entries, list)
        and record.get("historical_daily_price_fields_read") == []
        and record.get("historical_forward_return_fields_read") is False
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            f"candidate 49 future ledger header changed: {path}"
        )
    previous_sha256 = genesis
    seen_ids: set[str] = set()
    for ordinal, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise IntradayCumulativeVwapCrossingRateError(
                f"candidate 49 future ledger entry is not an object: {path}"
            )
        entry_id = str(entry.get("entry_id") or "")
        session_value = str(entry.get("session_date") or "")
        try:
            session_date = dt.date.fromisoformat(session_value)
        except ValueError as exc:
            raise IntradayCumulativeVwapCrossingRateError(
                f"candidate 49 future ledger session is invalid: {path}"
            ) from exc
        if not (
            entry.get("ordinal") == ordinal
            and entry_id
            and entry_id not in seen_ids
            and session_date >= EARLIEST_FUTURE_SESSION
            and entry.get("previous_entry_sha256") == previous_sha256
            and entry.get("entry_sha256") == _ledger_entry_digest(entry)
        ):
            raise IntradayCumulativeVwapCrossingRateError(
                f"candidate 49 future ledger hash chain changed: {path}"
            )
        seen_ids.add(entry_id)
        previous_sha256 = str(entry["entry_sha256"])
    if record.get("chain_tip_sha256") != previous_sha256:
        raise IntradayCumulativeVwapCrossingRateError(
            f"candidate 49 future ledger chain tip changed: {path}"
        )
    expected_status = (
        "empty_pending_first_eligible_future_session"
        if not entries
        else "active_append_only_future_observation"
    )
    if record.get("status") != expected_status:
        raise IntradayCumulativeVwapCrossingRateError(
            f"candidate 49 future ledger status changed: {path}"
        )
    return record


def initialize_future_ledgers(
    *,
    signal_path: Path = FUTURE_SIGNAL_LEDGER,
    execution_path: Path = FUTURE_EXECUTION_LEDGER,
) -> dict[str, Any]:
    """Create both empty future ledgers atomically per file and never reset them."""

    load_future_registration()
    _require_file(
        DEFAULT_FUTURE_ONLY_STATUS,
        FUTURE_ONLY_STATUS_SHA256,
        "candidate 49 future-only iteration state",
    )
    signal_path = signal_path.expanduser().resolve()
    execution_path = execution_path.expanduser().resolve()
    existence = (signal_path.exists(), execution_path.exists())
    if existence in {(True, False), (False, True)}:
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 future ledgers are in a partial initialization state"
        )
    if not any(existence):
        signal_path.parent.mkdir(parents=True, exist_ok=True)
        execution_path.parent.mkdir(parents=True, exist_ok=True)
        foundation.atomic_write_json(
            _empty_future_ledger(FUTURE_SIGNAL_LEDGER_KIND),
            signal_path,
        )
        try:
            foundation.atomic_write_json(
                _empty_future_ledger(FUTURE_EXECUTION_LEDGER_KIND),
                execution_path,
            )
        except BaseException:
            signal_path.unlink(missing_ok=True)
            raise
    signal = validate_future_ledger(signal_path, FUTURE_SIGNAL_LEDGER_KIND)
    execution = validate_future_ledger(
        execution_path,
        FUTURE_EXECUTION_LEDGER_KIND,
    )
    return {
        "status": "initialized_empty_append_only_ledgers",
        "signal_ledger": str(signal_path),
        "signal_entries": len(signal["entries"]),
        "execution_ledger": str(execution_path),
        "execution_entries": len(execution["entries"]),
        "historical_backfill_allowed": False,
        "provider_request_issued": False,
    }


def append_future_ledger_entry(
    *,
    path: Path,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Append one hash-linked entry while preserving all existing entries."""

    record = validate_future_ledger(path, kind)
    entries = list(record["entries"])
    entry_id = str(payload.get("entry_id") or "")
    session_value = str(payload.get("session_date") or "")
    try:
        session_date = dt.date.fromisoformat(session_value)
    except ValueError as exc:
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 future ledger entry needs an ISO session_date"
        ) from exc
    if (
        not entry_id
        or any(str(item.get("entry_id")) == entry_id for item in entries)
        or session_date < EARLIEST_FUTURE_SESSION
        or "entry_sha256" in payload
        or "previous_entry_sha256" in payload
        or "ordinal" in payload
    ):
        raise IntradayCumulativeVwapCrossingRateError(
            "candidate 49 future ledger append violates identity or date boundary"
        )
    entry = {
        **payload,
        "ordinal": len(entries) + 1,
        "previous_entry_sha256": record["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _ledger_entry_digest(entry)
    updated = {
        **record,
        "status": "active_append_only_future_observation",
        "entries": [*entries, entry],
        "chain_tip_sha256": entry["entry_sha256"],
    }
    foundation.atomic_write_json(updated, path.expanduser().resolve())
    validate_future_ledger(path, kind)
    return entry


def _active_buyable_symbols(
    instrument_path: Path,
    session_date: dt.date,
) -> list[str]:
    rows: list[str] = []
    for line in instrument_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            raise IntradayCumulativeVwapCrossingRateError(
                "buyable instrument file has an invalid row"
            )
        symbol, start_value, end_value = parts
        if (
            dt.date.fromisoformat(start_value)
            <= session_date
            <= dt.date.fromisoformat(end_value)
        ):
            rows.append(symbol.upper())
    if len(rows) != len(set(rows)):
        raise IntradayCumulativeVwapCrossingRateError(
            "buyable instrument file contains duplicate active symbols"
        )
    return sorted(rows)


def future_session_time_boundary_failures(
    *,
    session_date: dt.date,
    now: dt.datetime | None = None,
) -> tuple[dt.datetime, list[str]]:
    """Return the local no-backfill timing failures for a new future session."""

    local_now = now or dt.datetime.now(CHINA_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=CHINA_TZ)
    else:
        local_now = local_now.astimezone(CHINA_TZ)
    failures: list[str] = []
    if session_date < EARLIEST_FUTURE_SESSION:
        failures.append("session_precedes_immutable_future_boundary")
    if session_date < local_now.date():
        failures.append(
            "past_session_delayed_source_to_signal_backfill_forbidden"
        )
    elif session_date > local_now.date() or (
        local_now.time().replace(tzinfo=None) < SESSION_CLOSE_READINESS_TIME
    ):
        failures.append("session_not_yet_complete_after_close_buffer")
    return local_now, failures


def future_session_preflight(
    *,
    session_date: dt.date,
    data_root: Path,
    provider_uri: Path = DEFAULT_PROVIDER_URI,
    now: dt.datetime | None = None,
    token_configured: bool | None = None,
    signal_path: Path = FUTURE_SIGNAL_LEDGER,
    execution_path: Path = FUTURE_EXECUTION_LEDGER,
) -> dict[str, Any]:
    """Check a future session locally without issuing a provider request."""

    registration = load_future_registration()
    load_future_execution_protocol()
    _require_file(
        DEFAULT_FUTURE_ONLY_STATUS,
        FUTURE_ONLY_STATUS_SHA256,
        "candidate 49 future-only iteration state",
    )
    provider_uri = provider_uri.expanduser().resolve()
    data_root = data_root.expanduser().resolve()
    local_now, failures = future_session_time_boundary_failures(
        session_date=session_date,
        now=now,
    )
    price_basis_path = provider_uri / "price_basis.json"
    calendar_path = provider_uri / "calendars" / "day.txt"
    instrument_path = provider_uri / "instruments" / "buyable_main_chinext.txt"
    price_basis: dict[str, Any] = {}
    if price_basis_path.is_file():
        price_basis = json.loads(price_basis_path.read_text(encoding="utf-8"))
    if not (
        price_basis.get("status") == "passed"
        and price_basis.get("price_basis") == research.REQUIRED_PRICE_BASIS
        and not price_basis.get("failures")
    ):
        failures.append("local_daily_price_basis_not_passed")
    daily_sources = price_basis.get("daily_sources")
    if not (
        isinstance(daily_sources, list)
        and len(daily_sources) == 1
        and daily_sources[0] in {"eastmoney", "baostock", "tushare"}
    ):
        failures.append("local_daily_source_not_single_accepted_provider")
    calendar: list[dt.date] = []
    if calendar_path.is_file():
        try:
            calendar = [
                dt.date.fromisoformat(value)
                for value in calendar_path.read_text(encoding="utf-8").splitlines()
                if value
            ]
        except ValueError:
            failures.append("local_calendar_invalid")
    if session_date not in set(calendar):
        failures.append("session_not_in_accepted_local_calendar")
    symbols: list[str] = []
    if instrument_path.is_file():
        symbols = _active_buyable_symbols(instrument_path, session_date)
    if len(symbols) < 50:
        failures.append("fewer_than_50_active_buyable_symbols")
    if (
        not signal_path.expanduser().resolve().is_file()
        or not execution_path.expanduser().resolve().is_file()
    ):
        failures.append("future_ledgers_not_initialized")
        milestone_evaluation_status = "future_ledgers_not_initialized"
        execution_stop_required = False
    else:
        validate_future_ledger(signal_path, FUTURE_SIGNAL_LEDGER_KIND)
        execution_ledger = validate_future_ledger(
            execution_path,
            FUTURE_EXECUTION_LEDGER_KIND,
        )
        import a_share_tushare_candidate49_future_execution as future_execution

        milestone_evaluation = (
            future_execution.synchronize_evaluation_records(
                entries=list(execution_ledger["entries"]),
                execution_path=execution_path,
                evaluation_root=future_execution.DEFAULT_EVALUATION_ROOT,
                write_missing_records=False,
            )
        )
        milestone_evaluation_status = str(milestone_evaluation["status"])
        execution_stop_required = bool(
            milestone_evaluation["execution_stop_required"]
        )
        if execution_stop_required:
            failures.append(
                "candidate49_terminal_evaluation_stops_new_signals"
            )
    if token_configured is None:
        token_configured = bool(os.environ.get("TUSHARE_TOKEN"))
    if not token_configured:
        failures.append("tushare_token_missing_from_current_process")
    storage = registration["storage"]
    raw_session_root = (
        data_root
        / storage["future_raw_root_below_data_root"]
        / session_date.isoformat()
    ).resolve()
    factor_session_root = (
        data_root
        / storage["future_factor_root_below_data_root"]
        / session_date.isoformat()
    ).resolve()
    if (
        raw_session_root.exists()
        and not (raw_session_root / "snapshot_manifest.json").is_file()
    ):
        failures.append("future_raw_session_root_exists_without_manifest")
    if (
        factor_session_root.exists()
        and not (factor_session_root / "factor_manifest.json").is_file()
    ):
        failures.append("future_factor_session_root_exists_without_manifest")
    ready = not failures
    return {
        "status": (
            "ready_for_explicit_future_session_collection"
            if ready
            else "not_ready_no_provider_request"
        ),
        "session_date": session_date.isoformat(),
        "earliest_eligible_session": EARLIEST_FUTURE_SESSION.isoformat(),
        "local_now": local_now.isoformat(),
        "active_buyable_symbol_count": len(symbols),
        "accepted_daily_sources": (
            daily_sources if isinstance(daily_sources, list) else []
        ),
        "price_basis_path": str(price_basis_path),
        "calendar_path": str(calendar_path),
        "instrument_path": str(instrument_path),
        "raw_session_root": str(raw_session_root),
        "factor_session_root": str(factor_session_root),
        "token_configured": token_configured,
        "future_milestone_evaluation_status": milestone_evaluation_status,
        "future_execution_stop_required": execution_stop_required,
        "failures": failures,
        "ready": ready,
        "recommended_cli_exit_code": 0 if ready else 2,
        "provider_request_issued": False,
        "minute_rows_read": False,
        "signal_or_execution_entry_written": False,
        "historical_backfill_allowed": False,
        "new_source_to_signal_collection_requires_same_local_date": True,
    }


def status_record(data_root: Path) -> dict[str, Any]:
    """Report immutable local candidate state without a provider request."""

    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    validate_repository_chain(spec)
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "candidate 49 manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    audit_path = (
        REPO_ROOT / "data/experiments/short_horizon/"
        "20260725T062547Z_intraday_cumulative_vwap_crossing_rate_no_return_audit.json"
    )
    _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "candidate 49 no-return audit")
    registration = load_future_registration()
    execution_protocol = load_future_execution_protocol()
    ledgers_initialized = (
        FUTURE_SIGNAL_LEDGER.is_file() and FUTURE_EXECUTION_LEDGER.is_file()
    )
    signal_entries = execution_entries = 0
    completed_rank_ic_count = 0
    cumulative_net_return: float | None = None
    latest_execution_session: str | None = None
    milestone_evaluation: dict[str, Any] = {
        "status": "future_ledgers_not_initialized",
        "candidate50_activation_allowed": False,
        "execution_stop_required": False,
    }
    if ledgers_initialized:
        signal_ledger = validate_future_ledger(
            FUTURE_SIGNAL_LEDGER,
            FUTURE_SIGNAL_LEDGER_KIND,
        )
        execution_ledger = validate_future_ledger(
            FUTURE_EXECUTION_LEDGER,
            FUTURE_EXECUTION_LEDGER_KIND,
        )
        signal_entries = len(signal_ledger["entries"])
        execution_entries = len(execution_ledger["entries"])
        import a_share_tushare_candidate49_future_execution as future_execution

        milestone_evaluation = future_execution.synchronize_evaluation_records(
            entries=list(execution_ledger["entries"]),
            execution_path=FUTURE_EXECUTION_LEDGER,
            evaluation_root=future_execution.DEFAULT_EVALUATION_ROOT,
            write_missing_records=False,
        )
        if execution_entries:
            latest = execution_ledger["entries"][-1]
            latest_state = latest.get("ending_state") or {}
            if latest.get("execution_protocol_sha256") != (
                FUTURE_EXECUTION_PROTOCOL_SHA256
            ):
                raise IntradayCumulativeVwapCrossingRateError(
                    "candidate49 latest execution protocol fingerprint changed"
                )
            completed_rank_ic_count = int(
                latest_state.get("completed_rank_ic_signals", 0)
            )
            cumulative_net_return = float(
                latest_state["cumulative_net_return"]
            )
            latest_execution_session = str(latest["session_date"])
    return {
        "status": registration["status"],
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "historical_candidate_manifest": str(manifest_path),
        "historical_candidate_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "historical_candidate_dataset_sha256": CANDIDATE_DATASET_SHA256,
        "historical_candidate_rows": int(manifest["rows"]),
        "historical_candidate_eligible_rows": int(manifest["eligible_rows"]),
        "historical_no_return_audit": str(audit_path),
        "historical_no_return_audit_sha256": NO_RETURN_AUDIT_SHA256,
        "future_registration": str(DEFAULT_FUTURE_REGISTRATION),
        "future_registration_sha256": FUTURE_REGISTRATION_SHA256,
        "future_execution_protocol_sha256": FUTURE_EXECUTION_PROTOCOL_SHA256,
        "source_to_signal_engine_ready": True,
        "paper_execution_engine_ready": True,
        "paper_execution_only": bool(
            (execution_protocol.get("portfolio") or {}).get("paper_only")
        ),
        "earliest_eligible_signal_session": registration["future_data_boundary"][
            "earliest_eligible_signal_session"
        ],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "current_signal_exists": signal_entries > 0,
        "real_future_signal_count": signal_entries,
        "completed_future_rank_ic_count": completed_rank_ic_count,
        "portfolio_return_exists": execution_entries > 0,
        "paper_portfolio_cumulative_net_return": cumulative_net_return,
        "latest_execution_session": latest_execution_session,
        "future_ledgers_initialized": ledgers_initialized,
        "future_signal_entries": signal_entries,
        "future_execution_entries": execution_entries,
        "future_milestone_evaluation_engine_ready": True,
        "future_milestone_evaluation": milestone_evaluation,
        "candidate50_activation_allowed": bool(
            milestone_evaluation["candidate50_activation_allowed"]
        ),
        "aggregation_allowed": False,
        "provider_request_issued": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser(
        "build",
        help="Build the immutable historical no-return candidate snapshot",
    )
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--workers", type=int, default=4)
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run ordered historical coverage/capacity and uniqueness without returns",
    )
    audit_parser.add_argument("--data-root", type=Path, required=True)
    audit_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    audit_parser.add_argument("--workers", type=int, default=8)
    status_parser = subparsers.add_parser(
        "status",
        help="Validate the frozen candidate and future-only registration locally",
    )
    status_parser.add_argument("--data-root", type=Path, required=True)
    subparsers.add_parser(
        "initialize-future-ledgers",
        help="Create the two empty hash-linked future-only ledgers",
    )
    preflight_parser = subparsers.add_parser(
        "future-preflight",
        help=(
            "Check one post-registration session without a provider request; "
            "exit 2 while not ready"
        ),
    )
    preflight_parser.add_argument("--data-root", type=Path, required=True)
    preflight_parser.add_argument(
        "--session", type=dt.date.fromisoformat, required=True
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
        output: dict[str, Any] = {"status": "ok", "path": str(path)}
    elif args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
        output = {"status": "ok", "path": str(path)}
    elif args.command == "initialize-future-ledgers":
        output = initialize_future_ledgers()
    elif args.command == "future-preflight":
        output = future_session_preflight(
            session_date=args.session,
            data_root=args.data_root,
        )
    else:
        output = status_record(args.data_root)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if args.command == "future-preflight" and not output["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
