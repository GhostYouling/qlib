#!/usr/bin/env python3
"""Build the frozen Campaign065 range-state time-reversal divergence factor.

The builder projects only ``datetime,symbol,provider,high,low`` from the frozen
minute source. It never reads daily prices, forward returns, provider responses,
or Candidate49 historical outcomes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign064_features as campaign064


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign064_features.py"
BASE_RUNNER_SHA256 = "8087660639444aec35ea256446257de3a242cca9e0a9f7875107e4cf5196e486"
BASE_FACTOR = "intraday_range_weak_order_entropy_236t"
FACTOR_NAME = "intraday_range_weak_order_time_reversal_divergence_236t"
FACTOR_FORMULA = (
    "For the exact 236 overlapping within-half triples of x_i=ln(high_i/low_i), "
    "classify each exact zero-tolerance comparison key into one of 13 transitive "
    "weak-order states, let p be their pooled frequency and q_s=p_R(s) under "
    "exact triple reversal, and return JSD(p,q)/ln(2)."
)
PROTOCOL_SHA256 = "332c233850e1a2ebf6fa87fa725d1933635708d31a447395ab2f83be1538863b"
MECHANISM_AUDIT_SHA256 = "2038915c6b42a02990195604214f70c55f52478e0becf249ba710330c3da3a6a"
FULL_DEFINITION_COUNT = 96
FULL_DEFINITION_ORDER_SHA256 = "974e3acd06536dcfbcc13524932f771f3636ac32023b2712f5d2d76f4d1f2d92"
COMPARISON_COUNT = 95
COMPARISON_ORDER_SHA256 = "2418a9e28bdc6b3484ede7b4e0ae6293131af2f4644930ca2c21bff9060c331d"
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)
SELECTED_BAR_COUNT = 240
TRIPLES_PER_HALF = 118
POOLED_TRIPLE_COUNT = 236
WEAK_ORDER_STATE_COUNT = 13
ENDPOINT_TOLERANCE = 1e-12
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign065_feature_library_v1"
)

# Filled only after an immutable snapshot has been published.
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not BASE_RUNNER.is_file() or _local_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign064 feature engine changed")


# Execute the already-tested Campaign064 partition/checkpoint/publication engine
# in an independent namespace, then replace only the protocol and factor hooks.
_module_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign064", "Campaign065"),
    ("campaign064", "campaign065"),
    ("campaign_064", "campaign_065"),
    (BASE_FACTOR, FACTOR_NAME),
    ("441cbeef589593c2ef0ae3e58325f5ab0acb506cc54eaa040c79f26c8ca6a887", PROTOCOL_SHA256),
    ("422dd1a23708c069ff55b14105032e5fbf1ac2ed77cbd6d2439be896ef11cbae", MECHANISM_AUDIT_SHA256),
    ("d471615fc35bc482efcfe0fea1e8f7b79dce8826b649d3a3e43c3ba784c2ed6b", COMPARISON_ORDER_SHA256),
):
    _module_source = _module_source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign065_features_runtime",
}
exec(compile(_module_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_engine"]
GENERATED_PUBLICATION_SOURCE: str = _runtime["_runtime"]["_source"]

Campaign065FeatureError = _runtime["Campaign065FeatureError"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_065_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_065_feature_implementation_freeze_20260805.json"
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
extract_range_profiles = _runtime["extract_range_profiles"]
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

# Base-3 encodings of the exact 13 transitive comparison keys
# (cmp(a,b),cmp(a,c),cmp(b,c)), cmp in {-1,0,+1}.
WEAK_ORDER_CODES = np.asarray(
    [0, 1, 2, 5, 8, 9, 13, 17, 18, 21, 24, 25, 26],
    dtype=np.int8,
)


def _decode_code(code: int) -> tuple[int, int, int]:
    value = int(code)
    first = value // 9 - 1
    remainder = value % 9
    second = remainder // 3 - 1
    third = remainder % 3 - 1
    return first, second, third


def _encode_key(key: tuple[int, int, int]) -> int:
    first, second, third = key
    return (first + 1) * 9 + (second + 1) * 3 + third + 1


_code_to_index = {int(code): index for index, code in enumerate(WEAK_ORDER_CODES)}
REVERSAL_INDEX = np.asarray(
    [
        _code_to_index[_encode_key((-third, -second, -first))]
        for first, second, third in map(_decode_code, WEAK_ORDER_CODES)
    ],
    dtype=np.int8,
)
if not np.array_equal(REVERSAL_INDEX[REVERSAL_INDEX], np.arange(WEAK_ORDER_STATE_COUNT)):
    raise RuntimeError("weak-order reversal map is not an involution")


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return campaign064._comparison_order_digest(items)


def reconstruct_complete_definitions(_spec: dict[str, Any] | None = None) -> list[dict[str, str]]:
    prior_spec = campaign064.load_protocol()
    full = campaign064.reconstruct_comparisons(prior_spec) + [
        {"name": campaign064.FACTOR_NAME, "score_direction": "higher"}
    ]
    if len(full) != FULL_DEFINITION_COUNT or _comparison_order_digest(full) != FULL_DEFINITION_ORDER_SHA256:
        raise Campaign065FeatureError("Campaign065 full historical definition order changed")
    return full


def reconstruct_comparisons(spec: dict[str, Any] | None = None) -> list[dict[str, str]]:
    numeric = [
        item
        for item in reconstruct_complete_definitions(spec)
        if item["name"] != STRUCTURALLY_NONNUMERIC_FACTOR
    ]
    if len(numeric) != COMPARISON_COUNT or _comparison_order_digest(numeric) != COMPARISON_ORDER_SHA256:
        raise Campaign065FeatureError("Campaign065 numeric comparison order changed")
    return numeric


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != PROTOCOL_SHA256:
        raise Campaign065FeatureError(f"Campaign065 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign065FeatureError("Campaign065 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    source = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    full = reconstruct_complete_definitions(spec)
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign065_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign065_source_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "close", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("weak_order_state_count") == WEAK_ORDER_STATE_COUNT
        and candidate.get("exact_ties_retained") is True
        and candidate.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
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
        and uniqueness.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and len(full) == FULL_DEFINITION_COUNT
        and uniqueness.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and uniqueness.get("numeric_comparator_count") == COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and uniqueness.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_95_numeric_comparators_must_pass") is True
        and uniqueness.get("candidate_specific_comparator_drop_allowed") is False
        and uniqueness.get("structurally_nonnumeric_mechanism_challenges")
        == [STRUCTURALLY_NONNUMERIC_FACTOR]
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf065_{FACTOR_NAME}_single_higher"
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
        raise Campaign065FeatureError("Campaign065 protocol semantics changed")
    return spec


def _weak_order_time_reversal_divergence_from_ranges(
    ranges: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    values = np.asarray(ranges, dtype=float)
    if values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign065FeatureError("Campaign065 range matrix must have shape (n, 240)")
    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    valid = finite & nonnegative
    safe = np.where(np.isfinite(values) & (values >= 0.0), values, 0.0)
    triples = np.concatenate(
        (
            np.stack((safe[:, :118], safe[:, 1:119], safe[:, 2:120]), axis=2),
            np.stack((safe[:, 120:238], safe[:, 121:239], safe[:, 122:240]), axis=2),
        ),
        axis=1,
    )
    if triples.shape[1:] != (POOLED_TRIPLE_COUNT, 3):
        raise Campaign065FeatureError("Campaign065 triple support changed")
    first, second, third = triples[:, :, 0], triples[:, :, 1], triples[:, :, 2]
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
    reversed_probabilities = probabilities[:, REVERSAL_INDEX]
    mixture = 0.5 * (probabilities + reversed_probabilities)
    with np.errstate(divide="ignore", invalid="ignore"):
        forward_terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities / mixture),
            0.0,
        )
        reverse_terms = np.where(
            reversed_probabilities > 0.0,
            reversed_probabilities * np.log(reversed_probabilities / mixture),
            0.0,
        )
    scores = 0.5 * (forward_terms.sum(axis=1) + reverse_terms.sum(axis=1)) / np.log(2.0)
    scores = np.where(
        (scores < 0.0) & (scores >= -ENDPOINT_TOLERANCE), 0.0, scores
    )
    scores = np.where(
        (scores > 1.0) & (scores <= 1.0 + ENDPOINT_TOLERANCE), 1.0, scores
    )
    finite_scores = np.isfinite(scores)
    in_range = (scores >= 0.0) & (scores <= 1.0)
    eligible = valid & state_count_valid & finite_scores & in_range
    tie_triples = ((comparisons == 0).any(axis=2) & valid[:, None]).sum()
    self_reversing = REVERSAL_INDEX == np.arange(WEAK_ORDER_STATE_COUNT)
    self_reversing_observations = counts[:, self_reversing][valid].sum()
    quality = {
        "rows": int(len(values)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_range_rows": int((~finite).sum()),
        "negative_range_rows": int((finite & ~nonnegative).sum()),
        "state_count_mismatch_rows": int((valid & ~state_count_valid).sum()),
        "exact_tie_triple_observations": int(tie_triples),
        "recognized_state_observations": int(state_count[valid].sum()),
        "self_reversing_state_observations": int(self_reversing_observations),
        "reversal_invariant_rows": int((eligible & (scores == 0.0)).sum()),
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
        raise Campaign065FeatureError(
            "Campaign065 high/low matrices must share shape (n, 240)"
        )
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
    scores, eligible, factor_quality = _weak_order_time_reversal_divergence_from_ranges(
        ranges
    )
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
    for key, value in factor_quality.items():
        if key not in {"rows", "eligible_rows"}:
            quality[f"{FACTOR_NAME}__{key}"] = int(value)
    quality[f"{FACTOR_NAME}__eligible_rows"] = int(eligible.sum())
    return {FACTOR_NAME: scores}, {FACTOR_NAME: eligible}, quality


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
        raise Campaign065FeatureError(
            f"unexpected base columns for {symbol}: {tuple(base_frame.columns)}"
        )
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
        raise Campaign065FeatureError(f"base identity changed for {symbol}")
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
        raise Campaign065FeatureError(
            f"base current session is absent from raw source for {symbol}"
        )
    values, eligible, factor_quality = _weak_order_time_reversal_divergence_from_ranges(
        matrix
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
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign065_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
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
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
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
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign065FeatureError("Campaign065 snapshot semantics changed")


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
        raise Campaign065FeatureError(
            f"partial Campaign065 checkpoint is incomplete: {symbol} {year}"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign065_feature_partition"
        and record.get("symbol") == symbol
        and record.get("year") == year
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("feature_runner_sha256") == runner_sha256
        and record.get("implementation_freeze_sha256")
        == implementation_freeze_sha256
        and record.get("output_byte_sha256") == _local_sha256(frame_path)
    ):
        raise Campaign065FeatureError(
            f"partial Campaign065 checkpoint changed: {symbol} {year}"
        )
    frame = pd.read_parquet(frame_path, columns=list(OUTPUT_COLUMNS))
    if (
        record.get("rows") != len(frame)
        or record.get("output_frame_sha256") != foundation.frame_digest(frame)
    ):
        raise Campaign065FeatureError(
            f"partial Campaign065 frame changed: {symbol} {year}"
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
    "_validate_checkpoint": _validate_checkpoint,
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
