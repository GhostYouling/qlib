#!/usr/bin/env python3
"""Build Campaign057 cross-session absolute-return clock similarity features.

The factor compares normalized fixed-bin absolute within-half close returns on
the signal session with the same stock on the immediately preceding accepted
market session.  This module never reads a daily price or forward return.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign056_features.py"
BASE_RUNNER_SHA256 = "3667567ea96260b314f2832f175913314c31bd091abfb6023a5e0c2d1f172169"
BASE_FACTOR = "intraday_day_over_day_amount_profile_similarity_240b"
FACTOR_NAME = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_FORMULA = (
    "For signal session t and accepted market session t-1, form the exact 238 "
    "fixed within-half absolute log-close returns for each session, normalize "
    "both magnitude vectors independently to p and q, compute equal-mixture "
    "natural-log Jensen-Shannon divergence JSD(p,q), and return 1-JSD/ln(2)."
)
PROTOCOL_SHA256 = "9eb8607e91e952b9e22e436374d68de0a90df251065720bed8a6285f2e3b7ff1"
MECHANISM_AUDIT_SHA256 = "c4d81c004de89e9a94bfbea344bd92b5fd56e5fcaa74aa8f9bdcde40a4093e9f"
COMPARISON_COUNT = 80
COMPARISON_ORDER_SHA256 = "67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae"
SELECTED_CLOSE_COUNT = 240
SELECTED_BAR_COUNT = 238
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign057_feature_library_v1"
)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign056 feature runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign056", "Campaign057"),
    ("campaign056", "campaign057"),
    ("campaign_056", "campaign_057"),
    (BASE_FACTOR, FACTOR_NAME),
    ("7e7c9502e1018431f33a072dd12f8aa8f55a83b4afca30528245d1ea04ad1682", PROTOCOL_SHA256),
    ("c8df81ec46a42756fd81a58d33ca43587e7614736eaf996b1dee98ee95abc7d5", MECHANISM_AUDIT_SHA256),
    ("669a996cc0b8d2582f8a1c0cd2f7d9a8503fdcfe7fb5f1b79033ac7832bb4e67", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 79", "COMPARISON_COUNT = 80"),
    ('"source_open_high_low_close_volume_read": False,', '"source_open_high_low_close_volume_read": True,\n            "source_close_read": True,'),
    ('"source_amount_read": True,', '"source_amount_read": False,'),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign057_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign057FeatureError = _generated["Campaign057FeatureError"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE = _generated["DEFAULT_IMPLEMENTATION_FREEZE"]
DEFAULT_CALENDAR = _generated["DEFAULT_CALENDAR"]
RAW_MANIFEST_RELATIVE = _generated["RAW_MANIFEST_RELATIVE"]
CLEAN_MANIFEST_RELATIVE = _generated["CLEAN_MANIFEST_RELATIVE"]
RAW_MANIFEST_SHA256 = _generated["RAW_MANIFEST_SHA256"]
CLEAN_MANIFEST_SHA256 = _generated["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _generated["CLEAN_DATASET_SHA256"]
CALENDAR_SHA256 = _generated["CALENDAR_SHA256"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
LOWER_BOUND = _generated["LOWER_BOUND"]
UPPER_BOUND = _generated["UPPER_BOUND"]
ENDPOINT_TOLERANCE = _generated["ENDPOINT_TOLERANCE"]
CONTINUOUS_MINUTE_CODES = _generated["CONTINUOUS_MINUTE_CODES"]
SOURCE_MINUTE_CODES = _generated["SOURCE_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _generated["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _generated["SOURCE_MINUTE_CODE_SET"]
foundation = _generated["foundation"]
bindings = _generated["bindings"]
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (LOWER_BOUND, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}

for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "FACTOR_NAMES": FACTOR_NAMES,
    "FACTOR_DIRECTIONS": FACTOR_DIRECTIONS,
    "FACTOR_RANGES": FACTOR_RANGES,
    "FACTOR_FORMULAS": FACTOR_FORMULAS,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "SELECTED_BAR_COUNT": SELECTED_BAR_COUNT,
    "RAW_COLUMNS": RAW_COLUMNS,
    "BASE_COLUMNS": BASE_COLUMNS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
}.items():
    _generated[_name] = _value

_sha256 = _generated["_sha256"]
_comparison_order_digest = _generated["_comparison_order_digest"]
previous_session_map = _generated["previous_session_map"]
load_calendar = _generated["load_calendar"]
output_root = _generated["output_root"]


def _load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign057FeatureError(f"Campaign057 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign057FeatureError("Campaign057 protocol binding failed")
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
        == "a_share_three_day_walkforward_campaign057_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign057_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_close_count_per_session") == SELECTED_CLOSE_COUNT
        and candidate.get("absolute_return_bin_count_per_session") == SELECTED_BAR_COUNT
        and candidate.get("bridge_missing_or_suspended_prior_stock_session") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_80_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf057_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign057FeatureError("Campaign057 protocol semantics changed")
    return spec


def compute_similarity_values(
    current_magnitudes: np.ndarray,
    prior_magnitudes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the frozen equal-mixture Jensen-Shannon similarity."""

    current = np.asarray(current_magnitudes, dtype=float)
    prior = np.asarray(prior_magnitudes, dtype=float)
    if (
        current.ndim != 2
        or prior.ndim != 2
        or current.shape != prior.shape
        or current.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign057FeatureError("magnitude matrices must share shape (n, 238)")
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
    p = current / np.where(current_total_positive, current_total, 1.0)[:, None]
    q = prior / np.where(prior_total_positive, prior_total, 1.0)[:, None]
    mixture = 0.5 * (p + q)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        p_terms = np.where(p > 0.0, p * np.log(p / mixture), 0.0)
        q_terms = np.where(q > 0.0, q * np.log(q / mixture), 0.0)
        divergence = 0.5 * np.sum(p_terms, axis=1) + 0.5 * np.sum(q_terms, axis=1)
        raw_score = 1.0 - divergence / math.log(2.0)
    low_fix = (raw_score < LOWER_BOUND) & (raw_score >= LOWER_BOUND - ENDPOINT_TOLERANCE)
    high_fix = (raw_score > UPPER_BOUND) & (raw_score <= UPPER_BOUND + ENDPOINT_TOLERANCE)
    score = np.where(low_fix, LOWER_BOUND, raw_score)
    score = np.where(high_fix, UPPER_BOUND, score)
    score_finite = np.isfinite(score)
    score_in_range = (score >= LOWER_BOUND) & (score <= UPPER_BOUND)
    eligible = input_valid & score_finite & score_in_range
    quality = {
        "pair_rows": int(len(current)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_current_absolute_return_rows": int((~current_finite).sum()),
        "nonfinite_prior_absolute_return_rows": int((~prior_finite).sum()),
        "negative_current_absolute_return_rows": int((current_finite & ~current_nonnegative).sum()),
        "negative_prior_absolute_return_rows": int((prior_finite & ~prior_nonnegative).sum()),
        "nonpositive_current_total_absolute_return_rows": int((current_finite & current_nonnegative & ~current_total_positive).sum()),
        "nonpositive_prior_total_absolute_return_rows": int((prior_finite & prior_nonnegative & ~prior_total_positive).sum()),
        "eligible_zero_current_bins": int((current[eligible] == 0.0).sum()),
        "eligible_zero_prior_bins": int((prior[eligible] == 0.0).sum()),
        "endpoint_canonicalized_rows": int((eligible & (low_fix | high_fix)).sum()),
        "range_or_nonfinite_score_rows": int((input_valid & (~score_finite | ~score_in_range)).sum()),
    }
    return np.where(eligible, score, np.nan), eligible, quality


def extract_absolute_return_profiles(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, np.ndarray], dict[str, int]]:
    """Validate one raw symbol-year frame and return fixed 238-bin profiles."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign057FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or work.empty
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign057FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    if counts.empty or not counts.eq(len(SOURCE_MINUTE_CODES)).all():
        raise Campaign057FeatureError(
            f"every raw stock-day must retain 241 rows for {symbol}"
        )
    codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise Campaign057FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = tuple(pd.Timestamp(value) for value in counts.index)
    if len(continuous) != len(dates) * SELECTED_CLOSE_COUNT:
        raise Campaign057FeatureError(f"continuous grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        len(dates), SELECTED_CLOSE_COUNT
    )
    finite = np.isfinite(closes).all(axis=1)
    positive = (closes > 0.0).all(axis=1)
    valid = finite & positive
    magnitudes = np.full((len(dates), SELECTED_BAR_COUNT), np.nan, dtype=float)
    if valid.any():
        log_close = np.log(closes[valid])
        magnitudes[valid, :119] = np.abs(np.diff(log_close[:, :120], axis=1))
        magnitudes[valid, 119:] = np.abs(np.diff(log_close[:, 120:], axis=1))
    return (
        {date: magnitudes[index].copy() for index, date in enumerate(dates)},
        {
            "source_sessions": len(dates),
            "source_rows": len(work),
            "source_nonfinite_close_rows": int((~finite).sum()),
            "source_nonpositive_close_rows": int((finite & ~positive).sum()),
            "source_valid_close_grid_rows": int(valid.sum()),
            "source_exact_zero_absolute_return_bins": int((magnitudes[valid] == 0.0).sum()),
        },
    )


extract_amount_profiles = extract_absolute_return_profiles


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


def compute_output_frame(
    base_frame: pd.DataFrame,
    profiles: dict[pd.Timestamp, np.ndarray],
    calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Align one base partition with current and exact prior-session profiles."""

    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign057FeatureError(
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
        raise Campaign057FeatureError(f"base identity changed for {symbol}")
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
        raise Campaign057FeatureError(
            f"base current session is absent from bound raw source for {symbol}"
        )
    values, eligible, pair_quality = compute_similarity_values(current_matrix, prior_matrix)
    frame = pd.DataFrame(
        {
            "trade_date": base["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    prefix = FACTOR_NAME
    quality = {
        "base_rows": rows,
        f"{prefix}__eligible_rows": int(eligible.sum()),
        f"{prefix}__missing_prior_calendar_rows": int(prior_calendar_missing.sum()),
        f"{prefix}__missing_prior_stock_session_rows": int(prior_profile_missing.sum()),
    }
    for key, value in pair_quality.items():
        if key not in {"pair_rows", "eligible_rows"}:
            quality[f"{prefix}__{key}"] = value
    return frame, quality


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign057_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_amount_read") is False
        and manifest.get("cross_session_lookback") == 1
        and manifest.get("bridge_missing_or_suspended_prior_session") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed") is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign057FeatureError("Campaign057 snapshot semantics changed")


for _name, _value in {
    "_load_protocol": _load_protocol,
    "compute_similarity_values": compute_similarity_values,
    "extract_amount_profiles": extract_absolute_return_profiles,
    "empty_output_frame": empty_output_frame,
    "compute_output_frame": compute_output_frame,
    "_validate_manifest": _validate_manifest,
}.items():
    _generated[_name] = _value

_load_implementation_freeze = _generated["_load_implementation_freeze"]
_load_source_manifests = _generated["_load_source_manifests"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
