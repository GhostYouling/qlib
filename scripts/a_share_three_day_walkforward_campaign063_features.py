#!/usr/bin/env python3
"""Build the frozen Campaign063 market-relative state-stability factor.

The feature reads only the exact fixed-grid close-return vector and the
fingerprint-bound cross-sectional return sum, squared sum, and count frame.
It never reads a daily price, forward return, provider API response, or a
Candidate49 historical outcome.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign031_features as campaign031
from scripts import a_share_three_day_walkforward_campaign062_features as campaign062


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign059_features.py"
BASE_RUNNER_SHA256 = "d96954a319caf6b7dd45eafd46fae7db2a6176abc292529d00480b4a9ad10cc0"
MOMENT_HELPER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign031_features.py"
MOMENT_HELPER_SHA256 = "24fce3915f1321232573f413531b79c4fe9646c7bc192c7117d1358826d12df2"
BASE_FACTOR = "intraday_market_directional_sign_agreement_238m"
FACTOR_NAME = "intraday_cross_sectional_standardized_return_state_stability_236p"
FACTOR_FORMULA = (
    "For each of the exact 238 within-half signed log-close return positions, "
    "compute the stock's leave-one-out cross-sectional population z state from "
    "the frozen return sum, squared sum, and count; return 1/(1+mean absolute "
    "adjacent z-state displacement) across the exact 236 within-half adjacent pairs."
)
PROTOCOL_SHA256 = "2effcee4ccbbba8d55f450c7add3eb6064968a60c9d856ac769aebd20e542dfb"
MECHANISM_AUDIT_SHA256 = "2a0b637a975ce8fbd9db5086adcfe86b92c748cba9ba1064f428220f26d049ee"
COMPARISON_COUNT = 94
COMPARISON_ORDER_SHA256 = "58f3137a7d8282097a9fd9859209889f7b2a959e043163d013b21ab8f38b853a"
MOMENT_MANIFEST_SHA256 = "bbb82784b4daa21080045a17239868b1063d233607f125d03acab2aefb4fee50"
MOMENT_BYTE_SHA256 = "317aa3cb1793498bbce03018b692e6252939e689f0b9982e7c991a0da82d8827"
MOMENT_FRAME_SHA256 = "c4933078610a4a14597a35d54ac98f9089a90522b73d8d428cde9e5eec79201f"
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
SELECTED_CLOSE_COUNT = 240
RETURN_POSITION_COUNT = 238
ADJACENT_STATE_PAIR_COUNT = 236
NEGATIVE_VARIANCE_TOLERANCE = 1e-18
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign063_feature_library_v1"
)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


for _path, _expected, _label in (
    (BASE_RUNNER, BASE_RUNNER_SHA256, "frozen Campaign059 feature runner"),
    (MOMENT_HELPER, MOMENT_HELPER_SHA256, "frozen cross-sectional moment helper"),
):
    if not _path.is_file() or _local_sha256(_path) != _expected:
        raise RuntimeError(f"{_label} changed")


# Reuse the immutable partition/checkpoint/publication engine from Campaign059.
# The replacements change only the new campaign namespace and frozen bindings;
# formula execution and protocol validation are overridden below.
_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign059", "Campaign063"),
    ("campaign059", "campaign063"),
    ("campaign_059", "campaign_063"),
    ("20260804", "20260805"),
    (BASE_FACTOR, FACTOR_NAME),
    ("50cf7b067b1dfd5dc31d6c6ef85090788abdf6a2bbc054eda6e7c3824d5c60d6", PROTOCOL_SHA256),
    ("46d7c44bb35993a36ff1b53f126049d2e1f50d40768857d138a3e2f32b91c45e", MECHANISM_AUDIT_SHA256),
    ("09bc36308ce5d3af7a484fd9b233a02a9f5d3f37cd5169d400ab72737071caee", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 90", "COMPARISON_COUNT = 94"),
    ("all_90_must_pass", "all_94_must_pass"),
    ("954b71d571bcd89cbf4eae4eedad014091a9b40e6b2b083e0071cbf870634ef0", MOMENT_MANIFEST_SHA256),
    ("5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf", MOMENT_BYTE_SHA256),
    ("5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1", MOMENT_FRAME_SHA256),
    ("MINIMUM_INFORMATIVE_POSITIONS = 60", "MINIMUM_INFORMATIVE_POSITIONS = 236"),
    ('"minimum_informative_positions"', '"adjacent_state_pair_count"'),
    (
        "from scripts import a_share_three_day_walkforward_campaign004_features as campaign004",
        "from scripts import a_share_three_day_walkforward_campaign031_features as campaign004",
    ),
    (
        'REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign004_features.py"',
        'REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign031_features.py"',
    ),
    ("46b4c8b36698e64612b4b2c98e8cb4e81041100327d93e862722a3c5fb84b33c", MOMENT_HELPER_SHA256),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign063_features_runtime",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_engine"]

Campaign063FeatureError = _runtime["Campaign063FeatureError"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_feature_implementation_freeze_20260805.json"
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
    link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _local_sha256(path) != str(link.get("sha256") or ""):
        raise Campaign063FeatureError("Campaign062 comparison protocol changed")
    prior = json.loads(path.read_text(encoding="utf-8"))
    inherited = campaign062.reconstruct_comparisons(prior)
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
        raise Campaign063FeatureError(f"Campaign063 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign063FeatureError("Campaign063 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    source = spec.get("source_chain") or {}
    benchmark_manifest = source.get("frozen_cross_sectional_moment_manifest") or {}
    benchmark_frame = source.get("frozen_cross_sectional_moment_frame") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind") == "a_share_three_day_walkforward_campaign063_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign063_source_benchmark_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256") == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["open", "high", "low", "volume", "amount"]
        and tuple(candidate.get("benchmark_projection") or ()) == tuple(campaign031.market.BENCHMARK_COLUMNS)
        and candidate.get("selected_close_count") == SELECTED_CLOSE_COUNT
        and candidate.get("signed_return_position_count") == RETURN_POSITION_COUNT
        and candidate.get("adjacent_state_pair_count") == ADJACENT_STATE_PAIR_COUNT
        and candidate.get("minimum_leave_one_out_peers_per_position") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("population_variance_denominator") == "n"
        and candidate.get("tiny_negative_variance_canonicalization_tolerance") == NEGATIVE_VARIANCE_TOLERANCE
        and candidate.get("strictly_positive_leave_one_out_variance_required_each_position") is True
        and candidate.get("displacement_loss") == "mean absolute difference with equal weight for every one of the 236 pairs"
        and candidate.get("score_transform") == "1/(1+mean_absolute_displacement)"
        and candidate.get("valid_range") == {
            "lower": 0.0,
            "lower_inclusive": False,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and benchmark_manifest.get("sha256") == MOMENT_MANIFEST_SHA256
        and benchmark_frame.get("sha256") == MOMENT_BYTE_SHA256
        and benchmark_frame.get("frame_sha256") == MOMENT_FRAME_SHA256
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
        and uniqueness.get("all_94_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf063_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign063FeatureError("Campaign063 protocol semantics changed")
    return spec


def compute_state_stability_values(
    stock_returns: np.ndarray,
    peer_means: np.ndarray,
    peer_variances: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the exact 236-pair reciprocal mean-absolute z displacement."""

    stock = np.asarray(stock_returns, dtype=float)
    means = np.asarray(peer_means, dtype=float)
    raw_variances = np.asarray(peer_variances, dtype=float)
    peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITION_COUNT
        or means.shape != stock.shape
        or raw_variances.shape != stock.shape
        or peers.shape != stock.shape
    ):
        raise Campaign063FeatureError("Campaign063 state input arrays are invalid")
    material_negative = np.isfinite(raw_variances) & (
        raw_variances < -NEGATIVE_VARIANCE_TOLERANCE
    )
    tiny_negative = (
        np.isfinite(raw_variances)
        & (raw_variances < 0.0)
        & ~material_negative
    )
    variances = np.where(tiny_negative, 0.0, raw_variances)
    finite_inputs = (
        np.isfinite(stock).all(axis=1)
        & np.isfinite(means).all(axis=1)
        & np.isfinite(variances).all(axis=1)
        & ~material_negative.any(axis=1)
    )
    positive_variances = (variances > 0.0).all(axis=1)
    sufficient_rows = peers.all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        states = (stock - means) / np.sqrt(variances)
        morning = np.abs(np.diff(states[:, :119], axis=1))
        afternoon = np.abs(np.diff(states[:, 119:], axis=1))
        displacements = np.concatenate([morning, afternoon], axis=1)
        mean_displacement = np.mean(displacements, axis=1)
        score = 1.0 / (1.0 + mean_displacement)
    finite_states = np.isfinite(states).all(axis=1)
    finite_displacements = np.isfinite(displacements).all(axis=1)
    finite_scores = np.isfinite(score)
    in_range = (score > 0.0) & (score <= 1.0)
    eligible = (
        finite_inputs
        & positive_variances
        & sufficient_rows
        & finite_states
        & finite_displacements
        & finite_scores
        & in_range
    )
    quality = {
        "rows": int(len(stock)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_input_rows": int((~finite_inputs).sum()),
        "material_negative_variance_rows": int(material_negative.any(axis=1).sum()),
        "tiny_negative_variance_positions_canonicalized": int(tiny_negative.sum()),
        "nonpositive_variance_rows": int((finite_inputs & ~positive_variances).sum()),
        "insufficient_peer_rows": int((finite_inputs & positive_variances & ~sufficient_rows).sum()),
        "insufficient_peer_positions": int((~peers).sum()),
        "nonfinite_state_or_displacement_rows": int(
            (finite_inputs & positive_variances & sufficient_rows & (~finite_states | ~finite_displacements)).sum()
        ),
        "exact_zero_stock_return_positions": int((stock == 0.0).sum()),
        "exact_zero_peer_mean_positions": int((means == 0.0).sum()),
        "exact_zero_state_positions": int((states == 0.0).sum()),
        "exact_zero_displacement_pairs": int((displacements == 0.0).sum()),
        "range_or_nonfinite_score_rows": int(
            (finite_inputs & positive_variances & sufficient_rows & finite_states & finite_displacements & (~finite_scores | ~in_range)).sum()
        ),
    }
    return np.where(eligible, score, np.nan), eligible, quality


extract_signed_return_profiles = _runtime["extract_signed_return_profiles"]


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


_MOMENT_CACHE: Any = None
_MOMENT_LOCK = threading.Lock()


def _load_moment_benchmark() -> Any:
    global _MOMENT_CACHE
    with _MOMENT_LOCK:
        if _MOMENT_CACHE is None:
            value = campaign031._load_dispersion_benchmark(DEFAULT_DATA_ROOT)
            if getattr(value, "frame_sha256", None) != MOMENT_FRAME_SHA256:
                raise Campaign063FeatureError("frozen cross-sectional moment frame changed")
            _MOMENT_CACHE = value
    return _MOMENT_CACHE


def reconstruct_leave_one_out_moments(
    stock_returns: np.ndarray,
    return_sums: np.ndarray,
    return_sum_squares: np.ndarray,
    valid_stock_counts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Remove a complete stock vector from frozen same-position moments."""

    stock = np.asarray(stock_returns, dtype=float)
    sums = np.asarray(return_sums, dtype=float)
    sum_squares = np.asarray(return_sum_squares, dtype=float)
    counts = np.asarray(valid_stock_counts, dtype=np.int64)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITION_COUNT
        or sums.shape != stock.shape
        or sum_squares.shape != stock.shape
        or counts.shape != stock.shape
    ):
        raise Campaign063FeatureError("Campaign063 moment input arrays are invalid")
    complete = np.isfinite(stock).all(axis=1)
    own = np.where(complete[:, None], stock, 0.0)
    own_square = own * own
    own_count = complete.astype(np.int64)[:, None]
    peer_counts = counts - own_count
    peer_sums = sums - own
    peer_sum_squares = sum_squares - own_square
    sufficient = peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        means = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        second_moments = np.divide(
            peer_sum_squares,
            peer_counts,
            out=np.full_like(peer_sum_squares, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        variances = second_moments - means * means
    return means, variances, sufficient, {
        "complete_stock_return_rows": int(complete.sum()),
        "incomplete_stock_return_rows": int((~complete).sum()),
        "minimum_leave_one_out_peer_count": int(peer_counts.min()) if peer_counts.size else 0,
        "insufficient_leave_one_out_peer_positions": int((~sufficient).sum()),
    }


def compute_output_frame(
    base_frame: pd.DataFrame,
    profiles: dict[pd.Timestamp, np.ndarray],
    _calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign063FeatureError(f"unexpected base columns for {symbol}: {tuple(base_frame.columns)}")
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
        raise Campaign063FeatureError(f"base identity changed for {symbol}")
    base = base.sort_values("trade_date", kind="stable").reset_index(drop=True)
    missing = np.full(RETURN_POSITION_COUNT, np.nan, dtype=float)
    stock = np.empty((len(base), RETURN_POSITION_COUNT), dtype=float)
    current_missing = np.zeros(len(base), dtype=bool)
    for index, date in enumerate(base["trade_date"]):
        value = profiles.get(pd.Timestamp(date))
        if value is None:
            current_missing[index] = True
            stock[index] = missing
        else:
            stock[index] = value
    if current_missing.any():
        raise Campaign063FeatureError(f"base current session is absent from raw source for {symbol}")
    benchmark = _load_moment_benchmark()
    sums, sum_squares, counts = campaign031._benchmark_for_dates(
        benchmark, list(base["trade_date"])
    )
    means, variances, sufficient, moment_quality = reconstruct_leave_one_out_moments(
        stock, sums, sum_squares, counts
    )
    values, eligible, factor_quality = compute_state_stability_values(
        stock, means, variances, sufficient
    )
    frame = pd.DataFrame(
        {
            "trade_date": base["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare_leave_one_out_cross_sectional_state",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    quality = {
        "base_rows": int(len(frame)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
    }
    for key, value in {**moment_quality, **factor_quality}.items():
        if key not in {"rows", "eligible_rows"}:
            quality[f"{FACTOR_NAME}__{key}"] = int(value)
    return frame, quality


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign063_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_amount_read") is False
        and manifest.get("cross_session_lookback") == 0
        and manifest.get("market_benchmark_manifest_sha256") == MOMENT_MANIFEST_SHA256
        and manifest.get("market_benchmark_byte_sha256") == MOMENT_BYTE_SHA256
        and manifest.get("market_benchmark_frame_sha256") == MOMENT_FRAME_SHA256
        and manifest.get("market_benchmark_fields_read") == list(campaign031.market.BENCHMARK_COLUMNS)
        and manifest.get("minimum_leave_one_out_peers_per_position") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and manifest.get("adjacent_state_pair_count") == ADJACENT_STATE_PAIR_COUNT
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
        raise Campaign063FeatureError("Campaign063 snapshot semantics changed")


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
    "MINIMUM_INFORMATIVE_POSITIONS": ADJACENT_STATE_PAIR_COUNT,
    "SELECTED_BAR_COUNT": RETURN_POSITION_COUNT,
    "RAW_COLUMNS": RAW_COLUMNS,
    "BASE_COLUMNS": BASE_COLUMNS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "LOWER_BOUND": 0.0,
    "UPPER_BOUND": 1.0,
    "_load_protocol": load_protocol,
    "extract_amount_profiles": extract_signed_return_profiles,
    "empty_output_frame": empty_output_frame,
    "compute_output_frame": compute_output_frame,
    "_load_market_benchmark": lambda _data_root=DEFAULT_DATA_ROOT: _load_moment_benchmark(),
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
            "cross_sectional_moment_manifest_sha256": MOMENT_MANIFEST_SHA256,
            "cross_sectional_moment_byte_sha256": MOMENT_BYTE_SHA256,
            "cross_sectional_moment_frame_sha256": MOMENT_FRAME_SHA256,
            "cross_sectional_moment_fields_read_by_build": list(campaign031.market.BENCHMARK_COLUMNS),
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
