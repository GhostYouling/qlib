#!/usr/bin/env python3
"""Build the frozen Campaign061 consecutive-session volatility-scale factor.

The factor compares the same stock's total fixed-grid within-half realized
variance on the signal session and its exact accepted-calendar predecessor.
It reads no daily price, forward return, provider API, or Candidate49 outcome.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign060_features as campaign060


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_features.py"
BASE_RUNNER_SHA256 = "3706ac11c551dd02c8d6d8cf30c95a6f076d6a6e6c5dbba4beb07dde10aca66a"
BASE_FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_NAME = "intraday_day_over_day_realized_variance_stability_238b"
FACTOR_FORMULA = (
    "For signal session t and accepted market session t-1, form the exact 238 "
    "fixed within-half signed log-close returns for each session; let RV_t and "
    "RV_t_minus_1 be their unannualized sums of squared returns, and return "
    "2*min(RV_t,RV_t_minus_1)/(RV_t+RV_t_minus_1)."
)
PROTOCOL_SHA256 = "8bb79b587a64dab98a3a32d6a04ad6be8985979519ed436bc4062bbe64ff8dab"
MECHANISM_AUDIT_SHA256 = "3e2ea8227d439c9d3b3d1c3860ba3f0034df93367ea591e0f5f687994cce69e7"
COMPARISON_COUNT = 92
COMPARISON_ORDER_SHA256 = "c6b4ce432891c251443d8672705d1ecf0977912c1f3e82d42c00863001288c76"
SELECTED_CLOSE_COUNT = 240
SELECTED_BAR_COUNT = 238
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign061_feature_library_v1"
)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign057 feature runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign057", "Campaign061"),
    ("campaign057", "campaign061"),
    ("campaign_057", "campaign_061"),
    ("campaign_061_feature_implementation_freeze_20260804", "campaign_061_feature_implementation_freeze_20260805"),
    (BASE_FACTOR, FACTOR_NAME),
    ("9eb8607e91e952b9e22e436374d68de0a90df251065720bed8a6285f2e3b7ff1", PROTOCOL_SHA256),
    ("c4d81c004de89e9a94bfbea344bd92b5fd56e5fcaa74aa8f9bdcde40a4093e9f", MECHANISM_AUDIT_SHA256),
    ("67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 80", "COMPARISON_COUNT = 92"),
    ("all_80_must_pass", "all_92_must_pass"),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign061_features_runtime",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_generated"]

Campaign061FeatureError = _runtime["Campaign061FeatureError"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL: Path = _runtime["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_061_feature_implementation_freeze_20260805.json"
)
_runtime["DEFAULT_IMPLEMENTATION_FREEZE"] = DEFAULT_IMPLEMENTATION_FREEZE
_engine["DEFAULT_IMPLEMENTATION_FREEZE"] = DEFAULT_IMPLEMENTATION_FREEZE
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
RAW_MANIFEST_RELATIVE: Path = _runtime["RAW_MANIFEST_RELATIVE"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
RAW_MANIFEST_SHA256 = _runtime["RAW_MANIFEST_SHA256"]
CLEAN_MANIFEST_SHA256 = _runtime["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _runtime["CLEAN_DATASET_SHA256"]
CALENDAR_SHA256 = _runtime["CALENDAR_SHA256"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
CONTINUOUS_MINUTE_CODES = tuple(_runtime["CONTINUOUS_MINUTE_CODES"])
CONTINUOUS_MINUTE_CODE_SET = frozenset(_runtime["CONTINUOUS_MINUTE_CODE_SET"])
SOURCE_MINUTE_CODES = tuple(_runtime["SOURCE_MINUTE_CODES"])
SOURCE_MINUTE_CODE_SET = frozenset(_runtime["SOURCE_MINUTE_CODE_SET"])
foundation = _runtime["foundation"]
bindings = _runtime["bindings"]
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reconstruct_comparisons(spec: dict[str, Any]) -> list[dict[str, str]]:
    prior_link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    prior_path = REPO_ROOT / str(prior_link.get("path") or "")
    if (
        not prior_path.is_file()
        or _local_sha256(prior_path) != str(prior_link.get("sha256") or "")
    ):
        raise Campaign061FeatureError("Campaign060 comparison protocol changed")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    inherited = campaign060.reconstruct_comparisons(prior)
    appended = list(
        ((spec.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get(
            "appended_comparison_factors"
        )
        or []
    )
    return [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in [*inherited, *appended]
    ]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != PROTOCOL_SHA256:
        raise Campaign061FeatureError(f"Campaign061 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign061FeatureError("Campaign061 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign061_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign061_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_close_count_per_session") == SELECTED_CLOSE_COUNT
        and candidate.get("signed_return_position_count_per_session") == SELECTED_BAR_COUNT
        and candidate.get("bridge_missing_or_suspended_prior_stock_session") is False
        and candidate.get("strictly_positive_realized_variance_required_on_both_sessions") is True
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
        and uniqueness.get("all_92_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf061_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign061FeatureError("Campaign061 protocol semantics changed")
    return spec


def compute_variance_stability_values(
    current_returns: np.ndarray,
    prior_returns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the frozen symmetric realized-variance stability coefficient."""

    current = np.asarray(current_returns, dtype=float)
    prior = np.asarray(prior_returns, dtype=float)
    if (
        current.ndim != 2
        or prior.ndim != 2
        or current.shape != prior.shape
        or current.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign061FeatureError("return matrices must share shape (n, 238)")
    current_finite = np.isfinite(current).all(axis=1)
    prior_finite = np.isfinite(prior).all(axis=1)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        current_rv = np.sum(np.square(current), axis=1)
        prior_rv = np.sum(np.square(prior), axis=1)
        current_positive = np.isfinite(current_rv) & (current_rv > 0.0)
        prior_positive = np.isfinite(prior_rv) & (prior_rv > 0.0)
        denominator = current_rv + prior_rv
        raw_score = 2.0 * np.minimum(current_rv, prior_rv) / denominator
    input_valid = current_finite & prior_finite & current_positive & prior_positive
    score_finite = np.isfinite(raw_score)
    score_in_range = (raw_score > 0.0) & (raw_score <= 1.0)
    eligible = input_valid & score_finite & score_in_range
    quality = {
        "pair_rows": int(len(current)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_current_return_rows": int((~current_finite).sum()),
        "nonfinite_prior_return_rows": int((~prior_finite).sum()),
        "nonpositive_or_nonfinite_current_realized_variance_rows": int(
            (current_finite & ~current_positive).sum()
        ),
        "nonpositive_or_nonfinite_prior_realized_variance_rows": int(
            (prior_finite & ~prior_positive).sum()
        ),
        "eligible_exact_zero_current_return_positions": int(
            (current[eligible] == 0.0).sum()
        ),
        "eligible_exact_zero_prior_return_positions": int(
            (prior[eligible] == 0.0).sum()
        ),
        "range_or_nonfinite_score_rows": int(
            (input_valid & (~score_finite | ~score_in_range)).sum()
        ),
    }
    return np.where(eligible, raw_score, np.nan), eligible, quality


def extract_signed_return_profiles(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, np.ndarray], dict[str, int]]:
    """Validate one raw symbol-year frame and return fixed signed returns."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign061FeatureError(
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
        raise Campaign061FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    if counts.empty or not counts.eq(len(SOURCE_MINUTE_CODES)).all():
        raise Campaign061FeatureError(
            f"every raw stock-day must retain 241 rows for {symbol}"
        )
    codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise Campaign061FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign061FeatureError(f"continuous grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        len(dates), SELECTED_CLOSE_COUNT
    )
    finite = np.isfinite(closes).all(axis=1)
    positive = (closes > 0.0).all(axis=1)
    valid = finite & positive
    returns = np.full((len(dates), SELECTED_BAR_COUNT), np.nan, dtype=float)
    if valid.any():
        log_close = np.log(closes[valid])
        returns[valid, :119] = np.diff(log_close[:, :120], axis=1)
        returns[valid, 119:] = np.diff(log_close[:, 120:], axis=1)
    return (
        {date: returns[index].copy() for index, date in enumerate(dates)},
        {
            "source_sessions": len(dates),
            "source_rows": len(work),
            "source_nonfinite_close_rows": int((~finite).sum()),
            "source_nonpositive_close_rows": int((finite & ~positive).sum()),
            "source_valid_close_grid_rows": int(valid.sum()),
            "source_exact_zero_return_positions": int((returns[valid] == 0.0).sum()),
        },
    )


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
    "SELECTED_CLOSE_COUNT": SELECTED_CLOSE_COUNT,
    "SELECTED_BAR_COUNT": SELECTED_BAR_COUNT,
    "RAW_COLUMNS": RAW_COLUMNS,
    "BASE_COLUMNS": BASE_COLUMNS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "_load_protocol": load_protocol,
    "compute_similarity_values": compute_variance_stability_values,
    "compute_variance_stability_values": compute_variance_stability_values,
    "extract_amount_profiles": extract_signed_return_profiles,
    "extract_signed_return_profiles": extract_signed_return_profiles,
}.items():
    _runtime[_name] = _value
    _engine[_name] = _value

previous_session_map = _runtime["previous_session_map"]
load_calendar = _runtime["load_calendar"]
output_root = _runtime["output_root"]
empty_output_frame = _runtime["empty_output_frame"]
compute_output_frame = _runtime["compute_output_frame"]
_load_implementation_freeze = _runtime["_load_implementation_freeze"]
_load_source_manifests = _runtime["_load_source_manifests"]
build_snapshot = _runtime["build_snapshot"]
verify_snapshot_files = _runtime["verify_snapshot_files"]
status = _runtime["status"]
main = _runtime["main"]


if __name__ == "__main__":
    raise SystemExit(main())
