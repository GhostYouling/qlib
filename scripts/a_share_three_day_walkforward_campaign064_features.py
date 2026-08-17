#!/usr/bin/env python3
"""Build the frozen Campaign064 high/low range weak-order entropy factor.

The feature reads only the exact fixed-grid ``datetime,symbol,provider,high,low``
projection.  It never reads a daily price, forward return, provider API response,
or Candidate49 historical outcome.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign063_features as campaign063


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_features.py"
BASE_RUNNER_SHA256 = "3706ac11c551dd02c8d6d8cf30c95a6f076d6a6e6c5dbba4beb07dde10aca66a"
BASE_FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_NAME = "intraday_range_weak_order_entropy_236t"
FACTOR_FORMULA = (
    "For the exact 236 overlapping within-half triples of x_i=ln(high_i/low_i), "
    "classify each exact zero-tolerance comparison key "
    "(cmp(x0,x1),cmp(x0,x2),cmp(x1,x2)) into one of the 13 transitive "
    "weak-order states and return -sum(p_k*ln(p_k))/ln(13)."
)
PROTOCOL_SHA256 = "441cbeef589593c2ef0ae3e58325f5ab0acb506cc54eaa040c79f26c8ca6a887"
MECHANISM_AUDIT_SHA256 = "422dd1a23708c069ff55b14105032e5fbf1ac2ed77cbd6d2439be896ef11cbae"
COMPARISON_COUNT = 95
COMPARISON_ORDER_SHA256 = "d471615fc35bc482efcfe0fea1e8f7b79dce8826b649d3a3e43c3ba784c2ed6b"
SELECTED_BAR_COUNT = 240
TRIPLES_PER_HALF = 118
POOLED_TRIPLE_COUNT = 236
WEAK_ORDER_STATE_COUNT = 13
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign064_feature_library_v1"
)

# These are bound only after an immutable snapshot is published.
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not BASE_RUNNER.is_file() or _local_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign057 partition engine changed")


# Clone only the tested partition/checkpoint/hash/atomic-publication machinery.
# Campaign064 replaces the source projection, formula, protocol, output, and
# manifest validation below.  The source adapter also freezes zero lookback and
# truthful high/low-only evidence before any source value is opened.
_module_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign057", "Campaign064"),
    ("campaign057", "campaign064"),
    ("campaign_057", "campaign_064"),
    ("20260804", "20260805"),
    (BASE_FACTOR, FACTOR_NAME),
    ("9eb8607e91e952b9e22e436374d68de0a90df251065720bed8a6285f2e3b7ff1", PROTOCOL_SHA256),
    ("c4d81c004de89e9a94bfbea344bd92b5fd56e5fcaa74aa8f9bdcde40a4093e9f", MECHANISM_AUDIT_SHA256),
    ("67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 80", "COMPARISON_COUNT = 95"),
):
    _module_source = _module_source.replace(_old, _new)

_insertion_marker = "_generated: dict[str, Any] = {"
if _module_source.count(_insertion_marker) != 1:
    raise RuntimeError("Campaign057 generated-namespace marker changed")
_inner_source_adapter = r'''
_source = _source.replace(
    '            "source_open_high_low_close_volume_read": True,\n'
    '            "source_close_read": True,\n'
    '            "source_amount_read": False,\n'
    '            "cross_session_lookback": 1,\n'
    '            "prior_session_rule": "immediately_preceding_accepted_local_market_session",\n'
    '            "bridge_missing_or_suspended_prior_session": False,\n',
    '            "source_open_high_low_close_volume_read": True,\n'
    '            "source_high_low_read": True,\n'
    '            "source_close_read": False,\n'
    '            "source_amount_read": False,\n'
    '            "cross_session_lookback": 0,\n',
    1,
)
'''
_module_source = _module_source.replace(
    _insertion_marker,
    _inner_source_adapter + "\n" + _insertion_marker,
    1,
)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign064_features_runtime",
}
exec(compile(_module_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_generated"]

Campaign064FeatureError = _runtime["Campaign064FeatureError"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_064_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_064_feature_implementation_freeze_v3_20260805.json"
)
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

# Base-3 encodings of the 13 transitive keys
# (cmp(a,b),cmp(a,c),cmp(b,c)), cmp in {-1,0,+1}.
WEAK_ORDER_CODES = np.asarray(
    [0, 1, 2, 5, 8, 9, 13, 17, 18, 21, 24, 25, 26],
    dtype=np.int8,
)


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reconstruct_comparisons(spec: dict[str, Any]) -> list[dict[str, str]]:
    link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _local_sha256(path) != str(link.get("sha256") or ""):
        raise Campaign064FeatureError("Campaign063 comparison protocol changed")
    prior = json.loads(path.read_text(encoding="utf-8"))
    inherited = campaign063.reconstruct_comparisons(prior)
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
        raise Campaign064FeatureError(f"Campaign064 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign064FeatureError("Campaign064 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    source = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind") == "a_share_three_day_walkforward_campaign064_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign064_source_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256") == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["open", "close", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("triple_rule") == "118 overlapping consecutive triples per 120-bar half, pooled into exactly 236 equal-weight triples with no lunch-spanning triple."
        and candidate.get("weak_order_state_count") == WEAK_ORDER_STATE_COUNT
        and candidate.get("exact_ties_retained") is True
        and candidate.get("valid_range") == {
            "lower": 0.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": True,
        }
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
        and uniqueness.get("all_95_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf064_{FACTOR_NAME}_single_higher"
        and finite.get("trial_type") == "single_factor"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign064FeatureError("Campaign064 protocol semantics changed")
    return spec


def _weak_order_entropy_from_ranges(
    ranges: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    values = np.asarray(ranges, dtype=float)
    if values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign064FeatureError("Campaign064 range matrix must have shape (n, 240)")
    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    valid = finite & nonnegative
    safe = np.where(np.isfinite(values) & (values >= 0.0), values, 0.0)
    tuples = np.concatenate(
        (
            np.stack((safe[:, :118], safe[:, 1:119], safe[:, 2:120]), axis=2),
            np.stack((safe[:, 120:238], safe[:, 121:239], safe[:, 122:240]), axis=2),
        ),
        axis=1,
    )
    if tuples.shape[1:] != (POOLED_TRIPLE_COUNT, 3):
        raise Campaign064FeatureError("Campaign064 triple support changed")
    first, second, third = tuples[:, :, 0], tuples[:, :, 1], tuples[:, :, 2]
    comparisons = np.stack(
        (np.sign(first - second), np.sign(first - third), np.sign(second - third)),
        axis=2,
    ).astype(np.int8)
    codes = (
        (comparisons[:, :, 0] + 1) * 9
        + (comparisons[:, :, 1] + 1) * 3
        + comparisons[:, :, 2]
        + 1
    ).astype(np.int8)
    counts = np.stack([(codes == code).sum(axis=1) for code in WEAK_ORDER_CODES], axis=1)
    state_count = counts.sum(axis=1)
    state_count_valid = state_count == POOLED_TRIPLE_COUNT
    probabilities = counts.astype(float) / float(POOLED_TRIPLE_COUNT)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(probabilities > 0.0, probabilities * np.log(probabilities), 0.0)
    scores = -np.sum(terms, axis=1) / np.log(WEAK_ORDER_STATE_COUNT)
    finite_scores = np.isfinite(scores)
    in_range = (scores >= 0.0) & (scores <= 1.0)
    eligible = valid & state_count_valid & finite_scores & in_range
    tie_triples = ((comparisons == 0).any(axis=2) & valid[:, None]).sum()
    quality = {
        "rows": int(len(values)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_range_rows": int((~finite).sum()),
        "negative_range_rows": int((finite & ~nonnegative).sum()),
        "state_count_mismatch_rows": int((valid & ~state_count_valid).sum()),
        "exact_tie_triple_observations": int(tie_triples),
        "recognized_state_observations": int(state_count[valid].sum()),
        "range_or_nonfinite_score_rows": int(
            (valid & state_count_valid & (~finite_scores | ~in_range)).sum()
        ),
    }
    return np.where(eligible, scores, np.nan), eligible, quality


def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    if (
        highs.ndim != 2
        or lows.ndim != 2
        or highs.shape != lows.shape
        or highs.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign064FeatureError("Campaign064 high/low matrices must share shape (n, 240)")
    finite = np.isfinite(highs).all(axis=1) & np.isfinite(lows).all(axis=1)
    positive_low = (lows > 0.0).all(axis=1)
    ordered = (highs >= lows).all(axis=1)
    valid = finite & positive_low & ordered
    safe_highs = np.where(np.isfinite(highs) & (highs > 0.0), highs, 1.0)
    safe_lows = np.where(np.isfinite(lows) & (lows > 0.0), lows, 1.0)
    safe_highs = np.where(safe_highs >= safe_lows, safe_highs, safe_lows)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(safe_highs / safe_lows)
    ranges[~valid] = np.nan
    scores, eligible, entropy_quality = _weak_order_entropy_from_ranges(ranges)
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_low_rows": int((finite & ~positive_low).sum()),
        f"{FACTOR_NAME}__misordered_high_low_rows": int(
            (finite & positive_low & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__zero_range_bar_observations": int(
            ((ranges == 0.0) & valid[:, None]).sum()
        ),
    }
    for key, value in entropy_quality.items():
        if key not in {"rows", "eligible_rows"}:
            quality[f"{FACTOR_NAME}__{key}"] = int(value)
    quality[f"{FACTOR_NAME}__eligible_rows"] = int(eligible.sum())
    return (
        {FACTOR_NAME: scores},
        {FACTOR_NAME: eligible},
        quality,
    )


def extract_range_profiles(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, np.ndarray], dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign064FeatureError(f"unexpected raw columns for {symbol}: {tuple(raw.columns)}")
    if raw.empty:
        return {}, {
            "source_sessions": 0,
            "source_rows": 0,
            "source_valid_high_low_grid_rows": 0,
            "source_invalid_required_high_low_grid_rows": 0,
            "source_nonpositive_low_grid_rows": 0,
            "source_misordered_high_low_grid_rows": 0,
            "source_zero_range_bar_observations": 0,
            "manifest_declared_empty_partition_accepted": 1,
        }
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign064FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if (
        counts.empty
        or not counts.eq(len(SOURCE_MINUTE_CODES)).all()
        or not codes.eq(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign064FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = tuple(pd.Timestamp(value) for value in counts.index)
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign064FeatureError(f"continuous grid changed for {symbol}")
    highs = continuous["high"].to_numpy(dtype=float).reshape(len(dates), SELECTED_BAR_COUNT)
    lows = continuous["low"].to_numpy(dtype=float).reshape(len(dates), SELECTED_BAR_COUNT)
    finite = np.isfinite(highs).all(axis=1) & np.isfinite(lows).all(axis=1)
    positive_low = (lows > 0.0).all(axis=1)
    ordered = (highs >= lows).all(axis=1)
    valid = finite & positive_low & ordered
    safe_highs = np.where(np.isfinite(highs) & (highs > 0.0), highs, 1.0)
    safe_lows = np.where(np.isfinite(lows) & (lows > 0.0), lows, 1.0)
    safe_highs = np.where(safe_highs >= safe_lows, safe_highs, safe_lows)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(safe_highs / safe_lows)
    ranges[~valid] = np.nan
    return (
        {date: ranges[index].copy() for index, date in enumerate(dates)},
        {
            "source_sessions": len(dates),
            "source_rows": len(work),
            "source_valid_high_low_grid_rows": int(valid.sum()),
            "source_invalid_required_high_low_grid_rows": int((~finite).sum()),
            "source_nonpositive_low_grid_rows": int((finite & ~positive_low).sum()),
            "source_misordered_high_low_grid_rows": int(
                (finite & positive_low & ~ordered).sum()
            ),
            "source_zero_range_bar_observations": int(
                ((ranges == 0.0) & valid[:, None]).sum()
            ),
            "manifest_declared_empty_partition_accepted": 0,
        },
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


def compute_output_frame(
    base_frame: pd.DataFrame,
    profiles: dict[pd.Timestamp, np.ndarray],
    _calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign064FeatureError(f"unexpected base columns for {symbol}: {tuple(base_frame.columns)}")
    base = base_frame.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        return empty_output_frame(), {"base_rows": 0}
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign064FeatureError(f"base identity changed for {symbol}")
    base = base.sort_values("trade_date", kind="stable").reset_index(drop=True)
    matrix = np.empty((len(base), SELECTED_BAR_COUNT), dtype=float)
    missing = np.zeros(len(base), dtype=bool)
    for index, date in enumerate(base["trade_date"]):
        profile = profiles.get(pd.Timestamp(date))
        if profile is None:
            missing[index] = True
            matrix[index] = np.nan
        else:
            matrix[index] = profile
    if missing.any():
        raise Campaign064FeatureError(f"base current session is absent from raw source for {symbol}")
    values, eligible, factor_quality = _weak_order_entropy_from_ranges(matrix)
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
        "base_rows": int(len(frame)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
    }
    for key, value in factor_quality.items():
        if key not in {"rows", "eligible_rows"}:
            quality[f"{FACTOR_NAME}__{key}"] = int(value)
    return frame, quality


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign064_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is True
        and manifest.get("source_high_low_read") is True
        and manifest.get("source_close_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("cross_session_lookback") == 0
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
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
        raise Campaign064FeatureError("Campaign064 snapshot semantics changed")


PRE_MANIFEST_REPAIR_RUNNER_SHA256 = (
    "774f47073de3520a1b7fd818e5b8e16ac145f406c86d999368d35ec90b8aa21d"
)
PRE_MANIFEST_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "05b65cb001dfeec100c3ed3bcb105c9d59d26d0c4cdae8415d75ce589f5593b8"
)


def _validate_checkpoint_with_frozen_lineage(
    frame_path: Path,
    record_path: Path,
    *,
    symbol: str,
    year: int,
    runner_sha256: str,
    implementation_freeze_sha256: str,
) -> dict[str, Any] | None:
    """Validate current checkpoints or the sole frozen pre-repair identity pair."""

    if not frame_path.exists() and not record_path.exists():
        return None
    if not frame_path.is_file() or not record_path.is_file():
        raise Campaign064FeatureError(
            f"partial Campaign064 checkpoint is incomplete: {symbol} {year}"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    identity_pair = (
        record.get("feature_runner_sha256"),
        record.get("implementation_freeze_sha256"),
    )
    accepted_identity_pairs = {
        (runner_sha256, implementation_freeze_sha256),
        (
            PRE_MANIFEST_REPAIR_RUNNER_SHA256,
            PRE_MANIFEST_REPAIR_IMPLEMENTATION_FREEZE_SHA256,
        ),
    }
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign064_feature_partition"
        and record.get("symbol") == symbol
        and record.get("year") == year
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and identity_pair in accepted_identity_pairs
        and record.get("output_byte_sha256") == _local_sha256(frame_path)
    ):
        raise Campaign064FeatureError(
            f"partial Campaign064 checkpoint changed: {symbol} {year}"
        )
    frame = pd.read_parquet(frame_path, columns=list(OUTPUT_COLUMNS))
    if (
        record.get("rows") != len(frame)
        or record.get("output_frame_sha256") != foundation.frame_digest(frame)
    ):
        raise Campaign064FeatureError(
            f"partial Campaign064 frame changed: {symbol} {year}"
        )
    return record


for _name, _value in {
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
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
    "LOWER_BOUND": 0.0,
    "UPPER_BOUND": 1.0,
    "_load_protocol": load_protocol,
    "extract_amount_profiles": extract_range_profiles,
    "empty_output_frame": empty_output_frame,
    "compute_output_frame": compute_output_frame,
    "_validate_checkpoint": _validate_checkpoint_with_frozen_lineage,
    "_validate_manifest": _validate_manifest,
}.items():
    _engine[_name] = _value

build_snapshot = _engine["build_snapshot"]
verify_snapshot_files = _engine["verify_snapshot_files"]
output_root = _engine["output_root"]


def status(data_root: Path) -> dict[str, Any]:
    result = _engine["status"](data_root)
    result.update(
        {
            "source_fields_read_by_build": list(RAW_COLUMNS),
            "source_high_low_read_by_build": True,
            "source_close_volume_amount_read_by_build": False,
            "daily_price_or_forward_return_read_by_build": False,
        }
    )
    return result


def main() -> int:
    import argparse

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
    args = parser.parse_args()
    if args.command == "build":
        payload = {"snapshot_manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
