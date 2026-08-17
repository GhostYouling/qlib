#!/usr/bin/env python3
"""Build Campaign056 cross-session amount-profile similarity features.

The factor compares the normalized 240-bin CNY amount clock on a signal
session with the same stock's profile on the immediately preceding accepted
market session.  This module never reads a daily price or forward return.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_tushare_one_minute_sentiment_clean as foundation
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_tushare_one_minute_sentiment_clean as foundation


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_056_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_056_feature_implementation_freeze_20260804.json"
)
DEFAULT_CALENDAR = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
RAW_MANIFEST_RELATIVE = Path(
    "raw/a_share/rich/tushare/minutes/1m/snapshots/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f/snapshot_manifest.json"
)
CLEAN_MANIFEST_RELATIVE = Path(
    "derived/a_share/rich/tushare/minute_sentiment_clean/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_sentiment_clean_v1/"
    "snapshot_manifest.json"
)

FACTOR_NAME = "intraday_day_over_day_amount_profile_similarity_240b"
FACTOR_FORMULA = (
    "For signal session t and accepted market session t-1, normalize the exact "
    "240 matching-clock CNY amount vectors independently to p and q, compute "
    "equal-mixture natural-log Jensen-Shannon divergence JSD(p,q), and return "
    "1-JSD/ln(2)."
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}

PROTOCOL_SHA256 = "7e7c9502e1018431f33a072dd12f8aa8f55a83b4afca30528245d1ea04ad1682"
MECHANISM_AUDIT_SHA256 = "c8df81ec46a42756fd81a58d33ca43587e7614736eaf996b1dee98ee95abc7d5"
RAW_MANIFEST_SHA256 = "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
CLEAN_MANIFEST_SHA256 = "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
CLEAN_DATASET_SHA256 = "0e4fe7c05536cdfcecc2936bc880726902f5560061188ffff82ef7ee6f346983"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
COMPARISON_COUNT = 79
COMPARISON_ORDER_SHA256 = "669a996cc0b8d2582f8a1c0cd2f7d9a8503fdcfe7fb5f1b79033ac7832bb4e67"
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498

SELECTED_BAR_COUNT = 240
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
ENDPOINT_TOLERANCE = 1e-12
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign056_feature_library_v1"
)


def _minute_codes(start: str, periods: int) -> tuple[int, ...]:
    values = pd.date_range(f"2000-01-03 {start}", periods=periods, freq="1min")
    return tuple(int(item.hour * 60 + item.minute) for item in values)


CONTINUOUS_MINUTE_CODES = (
    *_minute_codes("09:31", 120),
    *_minute_codes("13:01", 120),
)
SOURCE_MINUTE_CODES = (9 * 60 + 30, *CONTINUOUS_MINUTE_CODES)
CONTINUOUS_MINUTE_CODE_SET = frozenset(CONTINUOUS_MINUTE_CODES)
SOURCE_MINUTE_CODE_SET = frozenset(SOURCE_MINUTE_CODES)


class Campaign056FeatureError(RuntimeError):
    """Fail-closed Campaign056 feature or publication error."""


def _sha256(path: Path) -> str:
    return foundation.file_digest(path)


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign056FeatureError(f"{label} changed: {path}")


def _value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _value_sha256(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign056_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign056 no-return protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign056FeatureError("Campaign056 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign056_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign056_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "close", "volume"]
        and candidate.get("selected_bar_count_per_session") == SELECTED_BAR_COUNT
        and candidate.get("matched_clock_bin_count") == SELECTED_BAR_COUNT
        and candidate.get("bridge_missing_or_suspended_prior_stock_session")
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_79_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf056_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign056FeatureError("Campaign056 protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    path = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not path.is_file():
        raise Campaign056FeatureError("Campaign056 implementation is not frozen")
    record = json.loads(path.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("version") == 1
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign056_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign056_source_values"
        and Path(str(runner.get("path") or "")).expanduser().resolve()
        == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("path")
        == "docs/a_share_three_day_walkforward_campaign_056_no_return_preregistration.json"
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("source_partition_values_read_before_freeze") is False
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_return_fields_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign056FeatureError("Campaign056 implementation freeze changed")
    return record


def load_calendar(path: Path = DEFAULT_CALENDAR) -> tuple[pd.Timestamp, ...]:
    _require_file(path, CALENDAR_SHA256, "accepted local calendar")
    values = pd.to_datetime(
        [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()],
        errors="raise",
    ).normalize()
    if len(values) != len(set(values)) or not values.is_monotonic_increasing:
        raise Campaign056FeatureError("accepted local calendar is invalid")
    return tuple(pd.Timestamp(value) for value in values)


def previous_session_map(
    sessions: Iterable[pd.Timestamp],
) -> dict[pd.Timestamp, pd.Timestamp]:
    ordered = tuple(pd.Timestamp(value).normalize() for value in sessions)
    return {ordered[index]: ordered[index - 1] for index in range(1, len(ordered))}


def compute_similarity_values(
    current_amounts: np.ndarray,
    prior_amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the frozen equal-mixture Jensen-Shannon similarity."""

    current = np.asarray(current_amounts, dtype=float)
    prior = np.asarray(prior_amounts, dtype=float)
    if (
        current.ndim != 2
        or prior.ndim != 2
        or current.shape != prior.shape
        or current.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign056FeatureError("amount matrices must share shape (n, 240)")
    rows = len(current)
    current_finite = np.isfinite(current).all(axis=1)
    prior_finite = np.isfinite(prior).all(axis=1)
    current_nonnegative = (current >= 0.0).all(axis=1)
    prior_nonnegative = (prior >= 0.0).all(axis=1)
    current_total = np.sum(np.where(np.isfinite(current), current, 0.0), axis=1)
    prior_total = np.sum(np.where(np.isfinite(prior), prior, 0.0), axis=1)
    current_total_positive = np.isfinite(current_total) & (current_total > 0.0)
    prior_total_positive = np.isfinite(prior_total) & (prior_total > 0.0)
    input_valid = (
        current_finite
        & prior_finite
        & current_nonnegative
        & prior_nonnegative
        & current_total_positive
        & prior_total_positive
    )
    safe_current_total = np.where(current_total_positive, current_total, 1.0)
    safe_prior_total = np.where(prior_total_positive, prior_total, 1.0)
    p = current / safe_current_total[:, None]
    q = prior / safe_prior_total[:, None]
    mixture = 0.5 * (p + q)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        p_terms = np.where(p > 0.0, p * np.log(p / mixture), 0.0)
        q_terms = np.where(q > 0.0, q * np.log(q / mixture), 0.0)
        divergence = 0.5 * np.sum(p_terms, axis=1) + 0.5 * np.sum(q_terms, axis=1)
        raw_score = 1.0 - divergence / math.log(2.0)
    low_fix = (raw_score < LOWER_BOUND) & (
        raw_score >= LOWER_BOUND - ENDPOINT_TOLERANCE
    )
    high_fix = (raw_score > UPPER_BOUND) & (
        raw_score <= UPPER_BOUND + ENDPOINT_TOLERANCE
    )
    score = np.where(low_fix, LOWER_BOUND, raw_score)
    score = np.where(high_fix, UPPER_BOUND, score)
    score_finite = np.isfinite(score)
    score_in_range = (score >= LOWER_BOUND) & (score <= UPPER_BOUND)
    eligible = input_valid & score_finite & score_in_range
    quality = {
        "pair_rows": int(rows),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_current_amount_rows": int((~current_finite).sum()),
        "nonfinite_prior_amount_rows": int((~prior_finite).sum()),
        "negative_current_amount_rows": int((current_finite & ~current_nonnegative).sum()),
        "negative_prior_amount_rows": int((prior_finite & ~prior_nonnegative).sum()),
        "nonpositive_current_total_rows": int(
            (current_finite & current_nonnegative & ~current_total_positive).sum()
        ),
        "nonpositive_prior_total_rows": int(
            (prior_finite & prior_nonnegative & ~prior_total_positive).sum()
        ),
        "eligible_zero_current_bins": int((current[eligible] == 0.0).sum()),
        "eligible_zero_prior_bins": int((prior[eligible] == 0.0).sum()),
        "endpoint_canonicalized_rows": int((eligible & (low_fix | high_fix)).sum()),
        "range_or_nonfinite_score_rows": int(
            (input_valid & (~score_finite | ~score_in_range)).sum()
        ),
    }
    return np.where(eligible, score, np.nan), eligible, quality


def extract_amount_profiles(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, np.ndarray], dict[str, int]]:
    """Validate a raw symbol-year frame and return all 240-bin profiles."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign056FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or work.empty
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign056FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    if counts.empty or not counts.eq(len(SOURCE_MINUTE_CODES)).all():
        raise Campaign056FeatureError(
            f"every raw stock-day must retain 241 rows for {symbol}"
        )
    codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise Campaign056FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    dates = tuple(pd.Timestamp(value) for value in counts.index)
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign056FeatureError(f"continuous grid changed for {symbol}")
    matrix = continuous["amount"].to_numpy(dtype=float).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    return (
        {date: matrix[index].copy() for index, date in enumerate(dates)},
        {
            "source_sessions": len(dates),
            "source_rows": len(work),
            "source_nonfinite_amount_rows": int((~np.isfinite(matrix)).any(axis=1).sum()),
            "source_negative_amount_rows": int(
                (np.isfinite(matrix).all(axis=1) & (matrix < 0.0).any(axis=1)).sum()
            ),
        },
    )


def compute_output_frame(
    base_frame: pd.DataFrame,
    profiles: dict[pd.Timestamp, np.ndarray],
    calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Align one base partition with current and exact prior-session profiles."""

    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign056FeatureError(
            f"unexpected base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base = base_frame.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or (not base.empty and set(base["symbol"].unique()) != {symbol.upper()})
        or (not base.empty and set(base["provider"].unique()) != {"tushare"})
    ):
        raise Campaign056FeatureError(f"base identity changed for {symbol}")
    base = base.sort_values("trade_date", kind="stable").reset_index(drop=True)
    rows = len(base)
    if rows == 0:
        return empty_output_frame(), {"base_rows": 0}
    missing = np.full(SELECTED_BAR_COUNT, np.nan, dtype=float)
    current_matrix = np.empty((rows, SELECTED_BAR_COUNT), dtype=float)
    prior_matrix = np.empty((rows, SELECTED_BAR_COUNT), dtype=float)
    current_missing = np.zeros(rows, dtype=bool)
    prior_calendar_missing = np.zeros(rows, dtype=bool)
    prior_profile_missing = np.zeros(rows, dtype=bool)
    for index, date in enumerate(base["trade_date"]):
        date = pd.Timestamp(date)
        current = profiles.get(date)
        if current is None:
            current_missing[index] = True
            current_matrix[index] = missing
        else:
            current_matrix[index] = current
        previous = calendar_previous.get(date)
        if previous is None:
            prior_calendar_missing[index] = True
            prior_matrix[index] = missing
            continue
        prior = profiles.get(previous)
        if prior is None:
            prior_profile_missing[index] = True
            prior_matrix[index] = missing
        else:
            prior_matrix[index] = prior
    if current_missing.any():
        raise Campaign056FeatureError(
            f"base current session is absent from bound raw source for {symbol}"
        )
    values, eligible, pair_quality = compute_similarity_values(
        current_matrix, prior_matrix
    )
    frame = pd.DataFrame(
        {
            "trade_date": base["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    quality = {
        "base_rows": rows,
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__missing_prior_calendar_rows": int(
            prior_calendar_missing.sum()
        ),
        f"{FACTOR_NAME}__missing_prior_stock_session_rows": int(
            prior_profile_missing.sum()
        ),
        f"{FACTOR_NAME}__nonfinite_current_amount_rows": pair_quality[
            "nonfinite_current_amount_rows"
        ],
        f"{FACTOR_NAME}__nonfinite_prior_amount_rows": pair_quality[
            "nonfinite_prior_amount_rows"
        ],
        f"{FACTOR_NAME}__negative_current_amount_rows": pair_quality[
            "negative_current_amount_rows"
        ],
        f"{FACTOR_NAME}__negative_prior_amount_rows": pair_quality[
            "negative_prior_amount_rows"
        ],
        f"{FACTOR_NAME}__nonpositive_current_total_rows": pair_quality[
            "nonpositive_current_total_rows"
        ],
        f"{FACTOR_NAME}__nonpositive_prior_total_rows": pair_quality[
            "nonpositive_prior_total_rows"
        ],
        f"{FACTOR_NAME}__eligible_zero_current_bins": pair_quality[
            "eligible_zero_current_bins"
        ],
        f"{FACTOR_NAME}__eligible_zero_prior_bins": pair_quality[
            "eligible_zero_prior_bins"
        ],
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": pair_quality[
            "endpoint_canonicalized_rows"
        ],
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": pair_quality[
            "range_or_nonfinite_score_rows"
        ],
    }
    return frame, quality


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


def _load_source_manifests(
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_path = data_root / RAW_MANIFEST_RELATIVE
    clean_path = data_root / CLEAN_MANIFEST_RELATIVE
    _require_file(raw_path, RAW_MANIFEST_SHA256, "raw minute manifest")
    _require_file(clean_path, CLEAN_MANIFEST_SHA256, "joint-clean manifest")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    raw_files = list(raw.get("files") or [])
    clean_files = list(clean.get("files") or [])
    if not (
        len(raw_files) == EXPECTED_PARTITIONS
        and len(clean_files) == EXPECTED_PARTITIONS
        and clean.get("partitions") == EXPECTED_PARTITIONS
        and clean.get("rows") == EXPECTED_ROWS
        and clean.get("dataset_sha256") == CLEAN_DATASET_SHA256
        and clean.get("forward_return_fields_read") is False
    ):
        raise Campaign056FeatureError("source manifest population changed")
    raw_keys = {(str(item["symbol"]).upper(), int(item["year"])) for item in raw_files}
    clean_keys = {
        (str(item["symbol"]).upper(), int(item["year"])) for item in clean_files
    }
    if len(raw_keys) != EXPECTED_PARTITIONS or raw_keys != clean_keys:
        raise Campaign056FeatureError("raw and clean partition keys changed")
    return raw, clean


def _partition_paths(
    partial_root: Path, symbol: str, year: int
) -> tuple[Path, Path]:
    token = symbol.lower()
    frame_path = partial_root / "partitions" / token / f"{year}.parquet"
    record_path = partial_root / ".metadata/partitions" / token / f"{year}.json"
    return frame_path, record_path


def _validate_checkpoint(
    frame_path: Path,
    record_path: Path,
    *,
    symbol: str,
    year: int,
    runner_sha256: str,
    implementation_freeze_sha256: str,
) -> dict[str, Any] | None:
    if not frame_path.exists() and not record_path.exists():
        return None
    if not frame_path.is_file() or not record_path.is_file():
        raise Campaign056FeatureError(
            f"partial Campaign056 checkpoint is incomplete: {symbol} {year}"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not (
        record.get("kind") == "a_share_three_day_walkforward_campaign056_feature_partition"
        and record.get("symbol") == symbol
        and record.get("year") == year
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("feature_runner_sha256") == runner_sha256
        and record.get("implementation_freeze_sha256")
        == implementation_freeze_sha256
        and record.get("output_byte_sha256") == _sha256(frame_path)
    ):
        raise Campaign056FeatureError(
            f"partial Campaign056 checkpoint changed: {symbol} {year}"
        )
    frame = pd.read_parquet(frame_path, columns=list(OUTPUT_COLUMNS))
    if (
        record.get("rows") != len(frame)
        or record.get("output_frame_sha256") != foundation.frame_digest(frame)
    ):
        raise Campaign056FeatureError(
            f"partial Campaign056 frame changed: {symbol} {year}"
        )
    return record


def _build_symbol_partitions(
    symbol: str,
    raw_records: list[dict[str, Any]],
    clean_by_key: dict[tuple[str, int], dict[str, Any]],
    calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    partial_root: Path,
    runner_sha256: str,
    implementation_freeze_sha256: str,
) -> list[dict[str, Any]]:
    profiles: dict[pd.Timestamp, np.ndarray] = {}
    records: list[dict[str, Any]] = []
    for raw_record in sorted(raw_records, key=lambda item: int(item["year"])):
        year = int(raw_record["year"])
        key = (symbol, year)
        clean_record = clean_by_key[key]
        raw_path = Path(str(raw_record["path"])).expanduser().resolve()
        clean_path = Path(str(clean_record["path"])).expanduser().resolve()
        if not (
            raw_path.is_file()
            and clean_path.is_file()
            and str(clean_record.get("source_path")) == str(raw_path)
            and clean_record.get("source_byte_sha256") == raw_record.get("byte_sha256")
        ):
            raise Campaign056FeatureError(f"source path binding changed: {symbol} {year}")
        frame_path, record_path = _partition_paths(partial_root, symbol, year)
        checkpoint = _validate_checkpoint(
            frame_path,
            record_path,
            symbol=symbol,
            year=year,
            runner_sha256=runner_sha256,
            implementation_freeze_sha256=implementation_freeze_sha256,
        )
        if _sha256(raw_path) != str(raw_record["byte_sha256"]):
            raise Campaign056FeatureError(f"raw source bytes changed: {symbol} {year}")
        if _sha256(clean_path) != str(clean_record["output_byte_sha256"]):
            raise Campaign056FeatureError(f"clean source bytes changed: {symbol} {year}")
        raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
        current_profiles, source_quality = extract_amount_profiles(raw, symbol=symbol)
        if any(date.year != year for date in current_profiles):
            raise Campaign056FeatureError(f"raw partition year changed: {symbol} {year}")
        overlap = set(profiles).intersection(current_profiles)
        if overlap:
            raise Campaign056FeatureError(f"duplicate cross-year dates: {symbol} {year}")
        profiles.update(current_profiles)
        if checkpoint is not None:
            records.append(checkpoint)
            continue
        base = pd.read_parquet(clean_path, columns=list(BASE_COLUMNS))
        output, quality = compute_output_frame(
            base,
            profiles,
            calendar_previous,
            symbol=symbol,
        )
        quality = {**source_quality, **quality}
        foundation.atomic_write_frame(output, frame_path)
        record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign056_feature_partition",
            "status": "complete_pending_aggregate_publication",
            "symbol": symbol,
            "code": str(raw_record.get("code") or ""),
            "year": year,
            "path": str(
                output_root(DEFAULT_DATA_ROOT)
                / "partitions"
                / symbol.lower()
                / f"{year}.parquet"
            ),
            "rows": len(output),
            "quality": quality,
            "factor_eligible_rows": {
                FACTOR_NAME: int(output[f"{FACTOR_NAME}_eligible"].sum())
            },
            "source_path": str(raw_path),
            "source_byte_sha256": str(raw_record["byte_sha256"]),
            "joint_clean_path": str(clean_path),
            "joint_clean_byte_sha256": str(clean_record["output_byte_sha256"]),
            "output_byte_sha256": _sha256(frame_path),
            "output_frame_sha256": foundation.frame_digest(output),
            "protocol_sha256": PROTOCOL_SHA256,
            "feature_runner_sha256": runner_sha256,
            "implementation_freeze_sha256": implementation_freeze_sha256,
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "comparison_factor_values_read": False,
            "provider_request_issued": False,
        }
        foundation.atomic_write_json(record, record_path)
        records.append(record)
    return records


def _dataset_digest(records: list[dict[str, Any]]) -> str:
    ordered = sorted(records, key=lambda item: (item["symbol"], int(item["year"])))
    return _value_sha256(
        [
            [
                item["symbol"],
                int(item["year"]),
                item["output_frame_sha256"],
                item["output_byte_sha256"],
                int(item["rows"]),
            ]
            for item in ordered
        ]
    )


def _aggregate_quality(records: list[dict[str, Any]]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for record in records:
        for key, value in (record.get("quality") or {}).items():
            if isinstance(value, int) and not isinstance(value, bool):
                total[key] += value
    return dict(sorted(total.items()))


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign056_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is False
        and manifest.get("source_amount_read") is True
        and manifest.get("cross_session_lookback") == 1
        and manifest.get("bridge_missing_or_suspended_prior_session") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("partitions") == len(files)
        and manifest.get("rows") == EXPECTED_ROWS
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign056FeatureError("Campaign056 snapshot semantics changed")


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build and atomically publish the frozen Campaign056 feature snapshot."""

    if workers < 1:
        raise Campaign056FeatureError("workers must be positive")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign056FeatureError("Campaign056 data root changed")
    _load_protocol()
    _load_implementation_freeze()
    implementation_freeze_sha256 = _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
    runner_sha256 = _sha256(Path(__file__).resolve())
    calendar_previous = previous_session_map(load_calendar())
    raw_manifest, clean_manifest = _load_source_manifests(data_root)
    raw_files = list(raw_manifest["files"])
    clean_files = list(clean_manifest["files"])
    clean_by_key = {
        (str(item["symbol"]).upper(), int(item["year"])): item
        for item in clean_files
    }
    raw_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in raw_files:
        raw_by_symbol[str(item["symbol"]).upper()].append(item)
    final_root = output_root(data_root)
    manifest_path = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not manifest_path.is_file():
            raise Campaign056FeatureError("Campaign056 final root is incomplete")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _validate_manifest(manifest)
        return manifest_path
    partial_root = final_root.with_name(f".{final_root.name}.partial")
    partial_root.mkdir(parents=True, exist_ok=True)
    lock_path = data_root / ".a_share_walkforward_campaign056_feature.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise Campaign056FeatureError("Campaign056 feature build is already active") from exc
    os.close(descriptor)
    try:
        symbols = sorted(raw_by_symbol)
        records: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_by_symbol = {
                executor.submit(
                    _build_symbol_partitions,
                    symbol,
                    raw_by_symbol[symbol],
                    clean_by_key,
                    calendar_previous,
                    partial_root,
                    runner_sha256,
                    implementation_freeze_sha256,
                ): symbol
                for symbol in symbols
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_by_symbol):
                symbol = future_by_symbol[future]
                try:
                    records.extend(future.result())
                except Exception as exc:
                    raise Campaign056FeatureError(
                        f"Campaign056 symbol build failed: {symbol}: {exc}"
                    ) from exc
                completed += 1
                if completed % 100 == 0 or completed == len(symbols):
                    print(
                        f"Campaign056 feature progress symbols={completed}/{len(symbols)}",
                        flush=True,
                    )
        records = sorted(records, key=lambda item: (item["symbol"], int(item["year"])))
        if len(records) != EXPECTED_PARTITIONS:
            raise Campaign056FeatureError("Campaign056 partition count changed")
        rows = sum(int(item["rows"]) for item in records)
        quality = _aggregate_quality(records)
        eligible_rows = sum(
            int(item["factor_eligible_rows"][FACTOR_NAME]) for item in records
        )
        if rows != EXPECTED_ROWS:
            raise Campaign056FeatureError("Campaign056 row count changed")
        final_files: list[dict[str, Any]] = []
        for item in records:
            value = dict(item)
            value["path"] = str(
                final_root
                / "partitions"
                / str(item["symbol"]).lower()
                / f"{int(item['year'])}.parquet"
            )
            final_files.append(value)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign056_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "output_run_id": OUTPUT_RUN_ID,
            "data_root": str(data_root),
            "source_manifest_path": str(data_root / RAW_MANIFEST_RELATIVE),
            "source_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_clean_manifest_path": str(data_root / CLEAN_MANIFEST_RELATIVE),
            "joint_clean_manifest_sha256": CLEAN_MANIFEST_SHA256,
            "joint_clean_dataset_sha256": CLEAN_DATASET_SHA256,
            "calendar_path": str(DEFAULT_CALENDAR.resolve()),
            "calendar_sha256": CALENDAR_SHA256,
            "source_fields_read": list(RAW_COLUMNS),
            "source_open_high_low_close_volume_read": False,
            "source_amount_read": True,
            "cross_session_lookback": 1,
            "prior_session_rule": "immediately_preceding_accepted_local_market_session",
            "bridge_missing_or_suspended_prior_session": False,
            "factor_names": [FACTOR_NAME],
            "factor_directions": FACTOR_DIRECTIONS,
            "factor_ranges": {FACTOR_NAME: [LOWER_BOUND, UPPER_BOUND]},
            "factor_formulas": FACTOR_FORMULAS,
            "factor_eligible_rows": {FACTOR_NAME: eligible_rows},
            "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
            "protocol_sha256": PROTOCOL_SHA256,
            "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
            "feature_runner_path": str(Path(__file__).resolve()),
            "feature_runner_sha256": runner_sha256,
            "implementation_freeze_path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
            "implementation_freeze_sha256": implementation_freeze_sha256,
            "partitions": len(final_files),
            "rows": rows,
            "dataset_sha256": _dataset_digest(records),
            "quality": quality,
            "files": final_files,
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "comparison_factor_values_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "prospective_candidate_activation_created": False,
            "provider_request_issued": False,
            "survivorship_limitation": "The eligible universe derives from a current listing snapshot and may introduce survivorship bias.",
        }
        _validate_manifest(manifest)
        foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        partial_root.replace(final_root)
        return manifest_path
    finally:
        lock_path.unlink(missing_ok=True)


def verify_snapshot_files(manifest_path: Path, *, workers: int) -> dict[str, Any]:
    """Verify every published Campaign056 partition byte and frame digest."""

    if workers < 1:
        raise Campaign056FeatureError("workers must be positive")
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    records = list(manifest["files"])

    def verify(record: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(record["path"])).expanduser().resolve()
        if not path.is_file() or _sha256(path) != record["output_byte_sha256"]:
            raise Campaign056FeatureError(f"Campaign056 output bytes changed: {path}")
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if (
            len(frame) != int(record["rows"])
            or foundation.frame_digest(frame) != record["output_frame_sha256"]
        ):
            raise Campaign056FeatureError(f"Campaign056 output frame changed: {path}")
        return len(frame), int(frame[f"{FACTOR_NAME}_eligible"].sum())

    rows = 0
    eligible = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for frame_rows, frame_eligible in executor.map(verify, records):
            rows += frame_rows
            eligible += frame_eligible
    if rows != manifest["rows"] or eligible != manifest["factor_eligible_rows"][FACTOR_NAME]:
        raise Campaign056FeatureError("Campaign056 verified totals changed")
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "all_partition_byte_and_frame_hashes_passed": True,
    }


def status(data_root: Path) -> dict[str, Any]:
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    result = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "provider_request_issued_by_status": False,
    }
    if DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        result["implementation_freeze_sha256"] = _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
    if manifest_path.is_file():
        result["snapshot_manifest_sha256"] = _sha256(manifest_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "build":
        payload = {
            "snapshot_manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
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
