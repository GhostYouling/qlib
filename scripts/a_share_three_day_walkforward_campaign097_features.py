#!/usr/bin/env python3
"""Build Campaign097's frozen leave-one-out market range-profile snapshot."""

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
from scripts import a_share_three_day_walkforward_campaign096_features_v2 as c96
from scripts import (
    a_share_tushare_intraday_market_amount_profile_synchronization as base,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_features.py"
)
PROTOCOL_SHA256 = "a36a7b4e6153c66c5fa5825ebf20a2a30d6764e040be6e84e4202e66413b1d56"
MECHANISM_AUDIT_SHA256 = (
    "8e2c212dc6cafaac351be506642fdc131ea713dd81bf888bb33ded83582c4fab"
)
CURRENT_STATE_SHA256 = (
    "4e7f7bb5678b5f81c133c8e5bf256c2a369a2734ac3fa2d2995f5629b83c1a56"
)
NUMERIC_POLICY_SHA256 = (
    "00ff7f93fcbdf09f8c75f81f1c1bc9e247d32a3088f50967316cc9f9a3bae9c5"
)
FACTOR_NAME = "intraday_market_range_profile_synchronization_240m"
C96_FACTOR = "intraday_intrabar_close_location_total_variation_238p"
FACTOR_FORMULA = (
    "normalize q_i=log(high_i/low_i) over the exact 240 standard bars, "
    "construct the same-date leave-one-out mean of complete normalized range "
    "profiles, and return the equal-clock-weight population Pearson correlation"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
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
NUMERICAL_CONSTANT_SS_TOLERANCE = np.finfo(np.float64).eps
FULL_DEFINITION_COUNT = 128
FULL_DEFINITION_ORDER_SHA256 = (
    "9380287d8339113cb01fa99670c77078f9be82b7463c06c1e7debb92b1add48b"
)
COMPARISON_COUNT = 125
COMPARISON_ORDER_SHA256 = (
    "50a737e640cac8e063aab8be0b483a6d9be87d0e5ddd1e1395e625ab371a4cae"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign097_feature_library_v1"
)
BENCHMARK_FILENAME = "market_range_profile_benchmark_240m.parquet"
LEGACY_EXTERNAL_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_tushare_intraday_market_amount_profile_synchronization_no_return_preregistration.json"
)
LEGACY_EXTERNAL_PROTOCOL_SHA256 = (
    "f560442de1a344ddcfee4ec42e14bfaa8e1abf9f1015506f011fee27121e6845"
)


class Campaign097FeatureError(RuntimeError):
    """Raised when a frozen Campaign097 source or semantic invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c96.reconstruct_complete_definitions()]
    if len(items) != 127 or items[-1]["name"] == C96_FACTOR:
        raise Campaign097FeatureError("Campaign096 inherited definition tail changed")
    items.append({"name": C96_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign097FeatureError("Campaign097 complete definition order changed")
    return items


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c96.reconstruct_comparisons()]
    if len(items) != 124 or items[-1]["name"] == C96_FACTOR:
        raise Campaign097FeatureError("Campaign096 inherited comparison tail changed")
    items.append({"name": C96_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign097FeatureError("Campaign097 numeric comparison order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the exact v41-bound protocol without reading minute values."""

    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign097FeatureError(f"Campaign097 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign097FeatureError("Campaign097 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    source = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    support = gates.get("support_predicate_before_source_rows") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    complete = reconstruct_complete_definitions()
    comparisons = reconstruct_comparisons()
    if not (
        spec.get("protocol_revision") == 2
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign097_minute_source_benchmark_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_and_support_predicate_audit") or {}).get(
            "sha256"
        )
        == MECHANISM_AUDIT_SHA256
        and (source.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (source.get("numeric_comparator_policy_v41") or {}).get("sha256")
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
        and uniqueness.get("all_125_numeric_comparators_must_pass") is True
        and len(complete) == FULL_DEFINITION_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf097_intraday_market_range_profile_synchronization_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and finite.get("purge_local_signal_sessions_before_each_partition_boundary")
        == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition") is True
        and boundary.get("candidate_source_rows_read_before_freeze") is False
        and boundary.get("market_benchmark_values_read_before_freeze") is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign097FeatureError("Campaign097 protocol semantics changed")
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


def extract_partition_profiles(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    """Extract complete normalized log-range profiles on the fixed 240 grid."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign097FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = base.engine._normalized_base(base_frame, symbol)
    if base_work.empty:
        return (
            base_work,
            np.empty((0, PROFILE_POSITIONS), dtype=float),
            np.empty(0, dtype=bool),
            {"invalid_required_amount_rows": 0, "nonpositive_total_amount_rows": 0},
        )
    normalized_symbol = symbol.upper()
    if raw.empty:
        raise Campaign097FeatureError(
            f"raw source is empty for nonempty base partition {normalized_symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {normalized_symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign097FeatureError(
            f"raw identity or timestamp violation for {normalized_symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign097FeatureError(
            f"every source stock-day must retain the exact 241-row grid for {normalized_symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(base.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign097FeatureError(
            f"source minute grid changed for {normalized_symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign097FeatureError(
            f"joint-clean base dates do not match raw dates for {normalized_symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(base.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=base.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    highs = continuous["high"].to_numpy(dtype=float).reshape(-1, PROFILE_POSITIONS)
    lows = continuous["low"].to_numpy(dtype=float).reshape(-1, PROFILE_POSITIONS)
    required_valid = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (lows <= highs).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(highs / lows)
    finite_nonnegative_ranges = np.isfinite(ranges).all(axis=1) & (ranges >= 0.0).all(
        axis=1
    )
    source_valid = required_valid & finite_nonnegative_ranges
    totals = np.where(source_valid[:, None], ranges, 0.0).sum(axis=1)
    positive_total = source_valid & np.isfinite(totals) & (totals > 0.0)
    profiles = np.full_like(ranges, np.nan, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(
            ranges,
            totals[:, None],
            out=profiles,
            where=positive_total[:, None],
        )
    valid = positive_total & np.isfinite(profiles).all(axis=1)
    profiles[~valid, :] = np.nan
    return (
        base_work,
        profiles,
        valid,
        {
            # Compatibility names are retained for the proven two-pass engine.
            "invalid_required_amount_rows": int((~source_valid).sum()),
            "nonpositive_total_amount_rows": int(
                (source_valid & ~positive_total).sum()
            ),
        },
    )


def compute_profile_correlations(
    profiles: np.ndarray,
    valid: np.ndarray,
    profile_sums: np.ndarray,
    valid_counts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute exact leave-one-out peer-profile Pearson correlations."""

    own_profiles = np.asarray(profiles, dtype=float)
    own_valid = np.asarray(valid, dtype=bool)
    sums = np.asarray(profile_sums, dtype=float)
    counts = np.asarray(valid_counts, dtype=np.int64)
    if (
        own_profiles.ndim != 2
        or own_profiles.shape[1] != PROFILE_POSITIONS
        or own_valid.shape != (len(own_profiles),)
        or sums.shape != own_profiles.shape
        or counts.shape != own_profiles.shape
    ):
        raise Campaign097FeatureError(
            "Campaign097 correlation input arrays are invalid"
        )
    own = np.where(np.isfinite(own_profiles), own_profiles, 0.0)
    peer_counts = counts - own_valid[:, None].astype(np.int64)
    peer_sums = sums - np.where(own_valid[:, None], own, 0.0)
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        peer_profiles = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        own_means = np.mean(own_profiles, axis=1, keepdims=True)
        peer_means = np.mean(peer_profiles, axis=1, keepdims=True)
        own_centered = own_profiles - own_means
        peer_centered = peer_profiles - peer_means
        own_ss = np.sum(own_centered * own_centered, axis=1)
        peer_ss = np.sum(peer_centered * peer_centered, axis=1)
        covariance = np.sum(own_centered * peer_centered, axis=1)
        values = covariance / np.sqrt(own_ss * peer_ss)
    constant_own = own_valid & (
        ~np.isfinite(own_ss) | (own_ss <= NUMERICAL_CONSTANT_SS_TOLERANCE)
    )
    constant_market = (
        own_valid
        & sufficient
        & (~np.isfinite(peer_ss) | (peer_ss <= NUMERICAL_CONSTANT_SS_TOLERANCE))
    )
    finite = np.isfinite(values)
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = own_valid & sufficient & finite & (low_near | high_near)
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = (
        own_valid & sufficient & ~constant_own & ~constant_market & finite & in_range
    )
    return (
        np.where(eligible, values, np.nan),
        eligible,
        {
            "insufficient_leave_one_out_peer_rows": int(
                (own_valid & ~sufficient).sum()
            ),
            "constant_own_profile_rows": int(constant_own.sum()),
            "constant_market_profile_rows": int(constant_market.sum()),
            "nonfinite_correlation_rows": int(
                (
                    own_valid & sufficient & ~constant_own & ~constant_market & ~finite
                ).sum()
            ),
            "endpoint_canonicalized_rows": int(canonicalized.sum()),
            "range_violation_rows": int(
                (
                    own_valid
                    & sufficient
                    & ~constant_own
                    & ~constant_market
                    & finite
                    & ~in_range
                ).sum()
            ),
        },
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    benchmark: base.AmountProfileBenchmark,
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
    sums, counts = base._benchmark_for_dates(benchmark, base_work["trade_date"])
    values, eligible, correlation_quality = compute_profile_correlations(
        profiles, valid, sums, counts
    )
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare_leave_one_out_market_range",
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
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign097_feature_library"
        / OUTPUT_RUN_ID
    )


_ORIGINAL_VALIDATE_EXTERNAL_CHAIN = base.validate_external_chain
_ORIGINAL_ACTIVATE_ENGINE = base._activate_engine


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    report = bindings.validate_record(DEFAULT_PROTOCOL, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign097FeatureError("Campaign097 repository binding failed")
    return {
        "campaign097_protocol": {
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
    # Reuse only the immutable raw/joint source verification of the historical
    # two-pass engine. Its old factor protocol and result are never reused.
    if (
        not LEGACY_EXTERNAL_PROTOCOL.is_file()
        or _sha256(LEGACY_EXTERNAL_PROTOCOL) != LEGACY_EXTERNAL_PROTOCOL_SHA256
    ):
        raise Campaign097FeatureError("legacy external source protocol changed")
    old_spec = json.loads(LEGACY_EXTERNAL_PROTOCOL.read_text(encoding="utf-8"))
    with base._original_engine_binding():
        return _ORIGINAL_VALIDATE_EXTERNAL_CHAIN(old_spec, data_root)


def _calendar_dates(spec: dict[str, Any]) -> pd.DatetimeIndex:
    link = (spec.get("source_chain") or {}).get("accepted_local_calendar") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _sha256(path) != str(link.get("sha256") or ""):
        raise Campaign097FeatureError("Campaign097 calendar binding changed")
    values = pd.to_datetime(
        pd.read_csv(path, header=None, names=["trade_date"])["trade_date"],
        errors="coerce",
    )
    dates = pd.DatetimeIndex(
        values.loc[
            values.between(pd.Timestamp("2019-01-01"), pd.Timestamp("2025-12-31"))
        ]
    ).normalize()
    if dates.hasnans or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise Campaign097FeatureError("Campaign097 frozen local calendar is invalid")
    return dates


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if require_fingerprint_constants:
        raise Campaign097FeatureError(
            "Campaign097 published snapshot must be reused only through its additive binding"
        )
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    compatibility_counters = (
        "invalid_required_amount_rows",
        "nonpositive_total_amount_rows",
        "insufficient_leave_one_out_peer_rows",
        "constant_own_profile_rows",
        "constant_market_profile_rows",
        "nonfinite_correlation_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    if not (
        manifest.get("kind")
        in {
            "a_share_tushare_intraday_market_idiosyncratic_share_snapshot",
            "a_share_three_day_walkforward_campaign097_feature_snapshot",
        }
        and manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("raw_manifest_sha256") == base.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == base.JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("factor_formula") == FACTOR_FORMULA
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and all(
            isinstance(quality.get(name), int) and quality.get(name) >= 0
            for name in compatibility_counters
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
        and manifest.get("forward_return_fields_read") is False
    ):
        raise Campaign097FeatureError("Campaign097 snapshot semantics changed")


def _finalize_engine_manifest(path: Path) -> None:
    manifest = base.research.load_json_record(path)
    if (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign097_feature_snapshot"
    ):
        return
    if (
        manifest.get("kind")
        != "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    ):
        raise Campaign097FeatureError("cannot finalize unexpected Campaign097 manifest")
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    manifest["kind"] = "a_share_three_day_walkforward_campaign097_feature_snapshot"
    manifest["source_high_low_read"] = True
    manifest["source_close_read"] = False
    manifest["source_open_read"] = False
    manifest["source_volume_read"] = False
    manifest["source_amount_read"] = False
    manifest["continuous_session_positions"] = PROFILE_POSITIONS
    manifest["leave_one_out_equal_weight_market_range_profile"] = True
    manifest["benchmark_semantics"] = (
        "same-date aligned float64 sum and integer count of complete normalized "
        "log-high-low range profiles in deterministic symbol order"
    )
    manifest["support_predicate"] = (
        "all 240 high-low pairs finite positive ordered, exact zero ranges retained, "
        "positive total range, at least 50 leave-one-out peers, and nonconstant "
        "stock and peer-mean profiles"
    )
    manifest["invalid_required_range_rows"] = int(
        quality.get("invalid_required_amount_rows", -1)
    )
    manifest["nonpositive_total_range_rows"] = int(
        quality.get("nonpositive_total_amount_rows", -1)
    )
    benchmark["source_fields_read"] = list(RAW_COLUMNS)
    benchmark["fresh_pass_invalid_required_range_rows"] = int(
        benchmark.pop("fresh_pass_invalid_required_amount_rows", -1)
    )
    benchmark["fresh_pass_nonpositive_total_range_rows"] = int(
        benchmark.pop("fresh_pass_nonpositive_total_amount_rows", -1)
    )
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
    base.foundation.atomic_write_json(manifest, path)


def _activate_engine() -> None:
    _ORIGINAL_ACTIVATE_ENGINE()
    base.engine._calendar_dates = _calendar_dates


@contextmanager
def _campaign097_binding() -> Iterable[None]:
    names = {
        "IntradayMarketAmountProfileSynchronizationError": Campaign097FeatureError,
        "DEFAULT_PREREGISTRATION": DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "PREREGISTRATION_SHA256": PROTOCOL_SHA256,
        "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
        "DEFAULT_TERMINAL_RECORD": REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_097_research_record.json",
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
    old = {name: getattr(base, name, None) for name in names}
    for name, value in names.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in old.items():
            setattr(base, name, value)


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    load_protocol()
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097FeatureError(
            "freeze Campaign097 implementation before source rows"
        )
    with _campaign097_binding():
        return base.build_snapshot(data_root=data_root, workers=workers)


def verify_snapshot_files(manifest_path: Path, *, workers: int) -> dict[str, int]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("kind")
        != "a_share_three_day_walkforward_campaign097_feature_snapshot"
    ):
        raise Campaign097FeatureError("unexpected Campaign097 snapshot kind")
    return base.verify_snapshot_files(manifest, manifest_path, workers)


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
