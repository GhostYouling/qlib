#!/usr/bin/env python3
"""Build Campaign099's frozen leave-one-out market close-location snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign097_features as c97
from scripts import a_share_three_day_walkforward_campaign098_features as c98


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign099_features.py"
)

PROTOCOL_SHA256 = "a10f8cf03a1acda3a3632fd7a648f3ec22697ca4074e31d85e539788b37720fc"
MECHANISM_AUDIT_SHA256 = (
    "1af28eb9df503fd7b80cbfaf764206456b8cf2930a1579ef58efbd39d87b5009"
)
CURRENT_STATE_SHA256 = (
    "9c2b064fc32bb0db03c2bc8e91c20783101a41102c1cee705a1cd919028bd133"
)
NUMERIC_POLICY_SHA256 = (
    "1f528805f5b6518acd96f2427544bf7448e109390d1ab37da39098bbb9661981"
)
FACTOR_NAME = "intraday_market_close_location_profile_synchronization_240m"
C98_FACTOR = c98.FACTOR_NAME
FACTOR_FORMULA = (
    "for d_i=log(high_i/low_i), set s_i=0 when d_i=0 and otherwise "
    "s_i=(log(close_i/low_i)-log(high_i/close_i))/d_i; return the "
    "equal-clock-weight population Pearson correlation of the complete "
    "240-state stock profile and its same-date leave-one-out peer mean"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
PROFILE_POSITIONS = 240
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
ENDPOINT_TOLERANCE = 1e-12
FULL_DEFINITION_COUNT = 130
FULL_DEFINITION_ORDER_SHA256 = (
    "5146b99fc3c70723b0b62c541ba560b8456199d08546b81d2520fa69eb8a4b57"
)
COMPARISON_COUNT = 127
COMPARISON_ORDER_SHA256 = (
    "5777fbeab91e603c45d271dfe018388129bc7fab83cc9a77b7776529ba9d0990"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign099_feature_library_v1"
)
BENCHMARK_FILENAME = "market_close_location_profile_benchmark_240m.parquet"


class Campaign099FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign099 invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return c97._order_digest(items)


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c98.reconstruct_complete_definitions()]
    items.append({"name": C98_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign099FeatureError("Campaign099 complete definition order changed")
    return items


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c98.reconstruct_comparisons()]
    items.append({"name": C98_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign099FeatureError("Campaign099 numeric comparator order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign099FeatureError(f"Campaign099 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign099FeatureError("Campaign099 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    support = gates.get("support_predicate_before_source_rows") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign099_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign099_minute_source_market_benchmark_candidate_comparator_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_and_support_predicate_audit") or {}).get(
            "sha256"
        )
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v47") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and candidate.get("selected_bar_count") == PROFILE_POSITIONS
        and candidate.get("minimum_leave_one_out_peers_per_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("correlation_estimator")
        == "equal-clock-weight population Pearson correlation over all 240 positions"
        and candidate.get("endpoint_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
            "lower": -1,
            "lower_inclusive": True,
            "upper": 1,
            "upper_inclusive": True,
        }
        and candidate.get("exact_support_predicate_gate_passed_before_source_rows")
        is True
        and support.get("required") is True
        and support.get("known_terminal_coverage_failure_inventory_reviewed") is True
        and support.get(
            "candidate_identical_to_or_provably_narrower_than_known_failure"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and uniqueness.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and uniqueness.get("numeric_comparator_count") == COMPARISON_COUNT
        and uniqueness.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_127_numeric_comparators_must_pass") is True
        and uniqueness.get("candidate_specific_comparator_drop_allowed") is False
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf099_intraday_market_close_location_profile_synchronization_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and finite.get("purge_local_signal_sessions_before_each_partition_boundary")
        == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition") is True
        and boundary.get("candidate_source_rows_read_before_freeze") is False
        and boundary.get("market_benchmark_values_read_before_freeze") is False
        and boundary.get("candidate_values_read_before_freeze") is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign099FeatureError("Campaign099 protocol semantics changed")
    return spec


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


def compute_close_location_profiles(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != PROFILE_POSITIONS:
        raise Campaign099FeatureError("Campaign099 requires an n-by-240 high array")
    if low.shape != high.shape or close.shape != high.shape:
        raise Campaign099FeatureError("Campaign099 HLC arrays must match")
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
        & (low <= close).all(axis=1)
        & (close <= high).all(axis=1)
    )
    profiles = np.full_like(high, np.nan, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        width = np.log(high / low)
        numerator = np.log(close / low) - np.log(high / close)
    finite_geometry = (
        np.isfinite(width).all(axis=1)
        & np.isfinite(numerator).all(axis=1)
        & (width >= 0.0).all(axis=1)
    )
    valid_geometry = source_valid & finite_geometry
    profiles[valid_geometry, :] = 0.0
    positive = valid_geometry[:, None] & (width > 0.0)
    np.divide(numerator, width, out=profiles, where=positive)
    low_near = (profiles < -1.0) & (profiles >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (profiles > 1.0) & (profiles <= 1.0 + ENDPOINT_TOLERANCE)
    profiles = np.where(low_near, -1.0, np.where(high_near, 1.0, profiles))
    in_range = (
        np.isfinite(profiles).all(axis=1)
        & (profiles >= -1.0).all(axis=1)
        & (profiles <= 1.0).all(axis=1)
    )
    valid = valid_geometry & in_range
    profiles[~valid, :] = np.nan
    return (
        profiles,
        valid,
        {
            "invalid_required_hlc_rows": int((~source_valid).sum()),
            "nonfinite_or_out_of_range_profile_rows": int(
                (source_valid & ~in_range).sum()
            ),
            "zero_range_state_count": int(
                (valid_geometry[:, None] & (width == 0.0)).sum()
            ),
            "endpoint_canonicalized_state_count": int((low_near | high_near).sum()),
        },
    )


def extract_partition_profiles(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign099FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = c97.base.engine._normalized_base(base_frame, symbol)
    empty_quality = {
        "invalid_required_amount_rows": 0,
        "nonpositive_total_amount_rows": 0,
        "invalid_required_hlc_rows": 0,
        "nonfinite_or_out_of_range_profile_rows": 0,
        "zero_range_state_count": 0,
        "endpoint_canonicalized_state_count": 0,
    }
    if base_work.empty:
        return (
            base_work,
            np.empty((0, PROFILE_POSITIONS)),
            np.empty(0, dtype=bool),
            empty_quality,
        )
    normalized_symbol = symbol.upper()
    if raw.empty:
        raise Campaign099FeatureError(
            f"raw source is empty for nonempty base partition {normalized_symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {normalized_symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign099FeatureError(
            f"raw identity or timestamp violation for {normalized_symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign099FeatureError(
            f"every source stock-day must retain 241 rows for {normalized_symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(c97.base.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign099FeatureError(
            f"source minute grid changed for {normalized_symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign099FeatureError(
            f"joint-clean dates do not match raw dates for {normalized_symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(c97.base.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c97.base.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    highs = continuous["high"].to_numpy(dtype=float).reshape(-1, PROFILE_POSITIONS)
    lows = continuous["low"].to_numpy(dtype=float).reshape(-1, PROFILE_POSITIONS)
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, PROFILE_POSITIONS)
    profiles, valid, quality = compute_close_location_profiles(highs, lows, closes)
    return (
        base_work,
        profiles,
        valid,
        {
            "invalid_required_amount_rows": quality["invalid_required_hlc_rows"],
            "nonpositive_total_amount_rows": quality[
                "nonfinite_or_out_of_range_profile_rows"
            ],
            **quality,
        },
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    benchmark: c97.base.AmountProfileBenchmark,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    base_work, profiles, valid, source_quality = extract_partition_profiles(
        raw, base_frame, symbol=symbol
    )
    if base_work.empty:
        return empty_output_frame(), {
            "base_rows": 0,
            "eligible_rows": 0,
            **source_quality,
            "insufficient_leave_one_out_peer_rows": 0,
            "constant_own_profile_rows": 0,
            "constant_market_profile_rows": 0,
            "nonfinite_correlation_rows": 0,
            "endpoint_canonicalized_rows": 0,
            "range_violation_rows": 0,
        }
    sums, counts = c97.base._benchmark_for_dates(benchmark, base_work["trade_date"])
    values, eligible, correlation_quality = c97.compute_profile_correlations(
        profiles, valid, sums, counts
    )
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare_leave_one_out_market_close_location",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        **source_quality,
        **correlation_quality,
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign099_feature_library"
        / OUTPUT_RUN_ID
    )


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    del spec
    report = bindings.validate_record(DEFAULT_PROTOCOL, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign099FeatureError("Campaign099 repository binding failed")
    return {
        "campaign099_protocol": {
            "path": str(DEFAULT_PROTOCOL),
            "sha256": PROTOCOL_SHA256,
            "binding_count": int(report["binding_count"]),
            "all_bindings_passed": True,
        },
        "complete_definition_count": FULL_DEFINITION_COUNT,
        "complete_definition_order_sha256": FULL_DEFINITION_ORDER_SHA256,
        "numeric_comparator_count": COMPARISON_COUNT,
        "numeric_comparator_order_sha256": COMPARISON_ORDER_SHA256,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    }


def validate_external_chain(spec: dict[str, Any], data_root: Path) -> tuple[Any, ...]:
    del spec
    return c97.validate_external_chain({}, data_root)


def _calendar_dates(spec: dict[str, Any]) -> pd.DatetimeIndex:
    return c97._calendar_dates(spec)


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if require_fingerprint_constants:
        raise Campaign099FeatureError(
            "Campaign099 publication must be frozen additively before reuse"
        )
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    required_counters = (
        "invalid_required_hlc_rows",
        "nonfinite_or_out_of_range_profile_rows",
        "zero_range_state_count",
        "endpoint_canonicalized_state_count",
        "insufficient_leave_one_out_peer_rows",
        "constant_own_profile_rows",
        "constant_market_profile_rows",
        "nonfinite_correlation_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    common_semantics = bool(
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("raw_manifest_sha256") == c97.base.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == c97.base.JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("factor_formula") == FACTOR_FORMULA
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and all(
            isinstance(quality.get(name), int) and quality.get(name) >= 0
            for name in required_counters
        )
        and benchmark.get("rows")
        == benchmark.get("trade_dates", -1) * PROFILE_POSITIONS
        and benchmark.get("profile_positions_per_date") == PROFILE_POSITIONS
        and benchmark.get("processed_symbol_count") == 5_396
        and benchmark.get("valid_stock_count_minimum", 0)
        >= MINIMUM_LEAVE_ONE_OUT_PEERS + 1
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("minimum_leave_one_out_peers") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and manifest.get("comparison_factor_values_read") is False
    )
    transient_engine_envelope = bool(
        manifest.get("kind")
        == "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_or_amount_read") is False
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("leave_one_out_equal_weight_market") is True
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and all(
            name not in manifest
            for name in (
                "zero_range_state",
                "source_high_low_read",
                "source_open_read",
                "source_volume_read",
                "source_amount_read",
                "historical_daily_price_fields_read",
                "historical_forward_returns_read",
                "candidate49_ledgers_changed",
                "provider_request_issued",
            )
        )
    )
    finalized_campaign099_envelope = bool(
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign099_feature_snapshot"
        and manifest.get("zero_range_state") == 0.0
        and manifest.get("source_high_low_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_open_read") is False
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
        and all(
            name not in manifest
            for name in (
                "source_volume_or_amount_read",
                "source_open_high_low_read",
                "leave_one_out_equal_weight_market",
            )
        )
    )
    if not common_semantics or not (
        transient_engine_envelope or finalized_campaign099_envelope
    ):
        raise Campaign099FeatureError("Campaign099 snapshot semantics changed")


def _finalize_engine_manifest(path: Path) -> None:
    manifest = c97.base.research.load_json_record(path)
    if (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign099_feature_snapshot"
    ):
        return
    if (
        manifest.get("kind")
        != "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    ):
        raise Campaign099FeatureError("cannot finalize unexpected Campaign099 manifest")
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    manifest["kind"] = "a_share_three_day_walkforward_campaign099_feature_snapshot"
    manifest["source_high_low_read"] = True
    manifest["source_close_read"] = True
    manifest["source_open_read"] = False
    manifest["source_volume_read"] = False
    manifest["source_amount_read"] = False
    manifest["continuous_session_positions"] = PROFILE_POSITIONS
    manifest["leave_one_out_equal_weight_market_close_location_profile"] = True
    manifest["zero_range_state"] = 0.0
    manifest["benchmark_semantics"] = (
        "same-date aligned float64 sum and integer count of complete signed "
        "own-bar close-location profiles in deterministic symbol order"
    )
    manifest["support_predicate"] = (
        "all 240 HLC tuples finite positive ordered, exact zero ranges retained as "
        "neutral zero, at least 50 leave-one-out peers, and nonconstant stock and "
        "peer-mean profiles"
    )
    quality["invalid_required_hlc_rows"] = int(
        quality.get("invalid_required_amount_rows", -1)
    )
    quality["nonfinite_or_out_of_range_profile_rows"] = int(
        quality.get("nonpositive_total_amount_rows", -1)
    )
    benchmark["source_fields_read"] = list(RAW_COLUMNS)
    benchmark["fresh_pass_invalid_required_hlc_rows"] = int(
        benchmark.get("fresh_pass_invalid_required_amount_rows", -1)
    )
    benchmark["fresh_pass_nonfinite_or_out_of_range_profile_rows"] = int(
        benchmark.get("fresh_pass_nonpositive_total_amount_rows", -1)
    )
    manifest["quality"] = quality
    manifest["market_benchmark"] = benchmark
    manifest["historical_daily_price_fields_read"] = []
    manifest["historical_forward_returns_read"] = False
    manifest["candidate49_historical_backfill_performed"] = False
    manifest["candidate49_ledgers_changed"] = False
    manifest["provider_request_issued"] = False
    manifest["prospective_candidate_created"] = False
    manifest["current_scoring_selection_sizing_or_orders_performed"] = False
    for key in (
        "source_open_high_low_read",
        "source_volume_or_amount_read",
        "leave_one_out_equal_weight_market",
    ):
        manifest.pop(key, None)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
    c97.base.foundation.atomic_write_json(manifest, path)


def _activate_engine() -> None:
    c97._ORIGINAL_ACTIVATE_ENGINE()
    c97.base.engine._calendar_dates = _calendar_dates


@contextmanager
def _campaign099_binding() -> Iterable[None]:
    names = {
        "IntradayMarketAmountProfileSynchronizationError": Campaign099FeatureError,
        "DEFAULT_PREREGISTRATION": DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "PREREGISTRATION_SHA256": PROTOCOL_SHA256,
        "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
        "DEFAULT_TERMINAL_RECORD": REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_099_research_record.json",
        "CANDIDATE_MANIFEST_SHA256": "",
        "CANDIDATE_DATASET_SHA256": "",
        "EXPECTED_ELIGIBLE_ROWS": -1,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "RAW_COLUMNS": RAW_COLUMNS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "BENCHMARK_FILENAME": BENCHMARK_FILENAME,
        "PROFILE_POSITIONS": PROFILE_POSITIONS,
        "MINIMUM_LEAVE_ONE_OUT_PEERS": MINIMUM_LEAVE_ONE_OUT_PEERS,
        "load_preregistration": load_protocol,
        "validate_repository_chain": validate_repository_chain,
        "validate_external_chain": validate_external_chain,
        "extract_partition_profiles": extract_partition_profiles,
        "compute_partition_frame": compute_partition_frame,
        "empty_output_frame": empty_output_frame,
        "output_root": output_root,
        "_validate_snapshot_manifest": _validate_snapshot_manifest,
        "_finalize_engine_manifest": _finalize_engine_manifest,
        "_activate_engine": _activate_engine,
        "load_terminal_record_if_present": lambda: None,
    }
    old = {name: getattr(c97.base, name, None) for name in names}
    for name, value in names.items():
        setattr(c97.base, name, value)
    try:
        yield
    finally:
        for name, value in old.items():
            setattr(c97.base, name, value)


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    load_protocol()
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign099FeatureError(
            "freeze Campaign099 implementation before source rows"
        )
    with _campaign099_binding():
        return c97.base.build_snapshot(data_root=data_root, workers=workers)


def verify_snapshot_files(manifest_path: Path, *, workers: int) -> dict[str, int]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
    return c97.base.verify_snapshot_files(manifest, manifest_path, workers)


def status(data_root: Path) -> dict[str, Any]:
    root = output_root(data_root.expanduser().resolve())
    manifest = root / "snapshot_manifest.json"
    return {
        "output_root": str(root),
        "published": manifest.is_file(),
        "manifest_sha256": _sha256(manifest) if manifest.is_file() else None,
        "partial_root_exists": (root.parent / f".{OUTPUT_RUN_ID}.partial").exists(),
        "protocol_sha256": PROTOCOL_SHA256,
        "formula": FACTOR_FORMULA,
        "support_predicate_gate_frozen": True,
        "comparison_values_read_by_feature_build": False,
        "daily_price_or_forward_return_read_by_feature_build": False,
    }


def main() -> int:
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
        payload: Any = {
            "manifest": str(
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
