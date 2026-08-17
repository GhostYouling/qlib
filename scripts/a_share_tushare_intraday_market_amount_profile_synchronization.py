#!/usr/bin/env python3
"""Build and no-return audit market amount-profile synchronization.

The candidate reads only immutable Tushare minute identity and CNY amount
fields.  It normalizes each stock-day's exact 240-position continuous-session
amount profile, builds an equal-weight same-date market-profile accumulator,
removes the candidate stock, and correlates the two aligned profiles.  Coverage
and capacity are evaluated before any terminal comparison values are loaded.
This module never reads daily prices or forward returns.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import json
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_market_idiosyncratic_share as engine  # noqa: E402
import a_share_tushare_intraday_opening_auction_amount_share as previous  # noqa: E402


foundation = engine.foundation
research = engine.research
_ENGINE_BINDING_NAMES = (
    "DEFAULT_PREREGISTRATION",
    "PREREGISTRATION_SHA256",
    "DEFAULT_TERMINAL_RECORD",
    "CANDIDATE_MANIFEST_SHA256",
    "CANDIDATE_DATASET_SHA256",
    "EXPECTED_ELIGIBLE_ROWS",
    "OUTPUT_RUN_ID",
    "FACTOR_NAME",
    "FACTOR_FORMULA",
    "COMPARISON_FACTORS",
    "COMPARISON_DIRECTIONS",
    "RAW_COLUMNS",
    "OUTPUT_COLUMNS",
    "BENCHMARK_FILENAME",
    "RETURN_POSITIONS",
    "MINIMUM_LEAVE_ONE_OUT_PEERS",
    "load_preregistration",
    "validate_repository_chain",
    "validate_external_chain",
    "load_terminal_record_if_present",
    "_build_market_benchmark",
    "_process_symbol",
    "_validate_snapshot_manifest",
    "output_root",
)
_ORIGINAL_ENGINE_BINDING = {
    name: getattr(engine, name) for name in _ENGINE_BINDING_NAMES
}
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_market_amount_profile_synchronization_"
        "no_return_preregistration.json"
    )
)
PREREGISTRATION_SHA256 = (
    "f560442de1a344ddcfee4ec42e14bfaa8e1abf9f1015506f011fee27121e6845"
)
DEFAULT_MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_market_amount_profile_synchronization_"
        "mechanism_overlap_reaudit_20260725.json"
    )
)
MECHANISM_AUDIT_SHA256 = (
    "24127b8326f29175a88a74ecb5c21cb508b3fc9bb5a68ee5f7e003f29b84d17f"
)
DEFAULT_DIAGNOSTIC_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_market_amount_profile_synchronization_"
        "diagnostic_preregistration.json"
    )
)
DIAGNOSTIC_PREREGISTRATION_SHA256 = (
    "279c6c248aaa517d36db00ac39a5336742bf2404b99888c311f398bca8ebefb5"
)
NO_RETURN_AUDIT_SHA256 = (
    "516dd4e88b31790a30c5477a7a6a4a05591a2fdb48f4a43fa4f31044245c3ca3"
)
DIAGNOSTIC_PURPOSE = (
    "single_preregistered_intraday_market_amount_profile_synchronization_"
    "three_session_diagnostic"
)
CONSUMPTION_FILENAME = (
    "intraday_market_amount_profile_synchronization_240m_" "historical_consumption.json"
)
DEFAULT_CURRENT_STATUS = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260723.json"
)
CURRENT_STATUS_SHA256 = (
    "08c3a5b2a1039cd46b9be4715bd666d516cc8d4273d03c5b56ddf06969b115c9"
)
DEFAULT_TERMINAL_RECORD = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_market_amount_profile_synchronization_"
        "research_record.json"
    )
)
TERMINAL_RECORD_SHA256 = (
    "75a41875b5133258d483c470d44f1fdd1cdd030573e03ce66c33c22d926874ed"
)
DIAGNOSTIC_SHA256 = "154fae15db6775fc1f9ae6cc853eee11fb54559e032f4c29a5e89f7057d439a1"
STABILITY_AUDIT_SHA256 = (
    "a58ac6bcd186d65dbb810ad892bf4ce0048dda719356834e2fe8f25725f8abfe"
)
TOPK_AUDIT_SHA256 = "f3a46baf5302fb6cb4c1d03e45f3a609f5a6e8290893779e26941f376e4a5d71"
CONSUMPTION_MARKER_SHA256 = (
    "a67862b618171518c5d835e6e9fde38af3a3393becc094c32cd094d0cf3adfad"
)
PREVIOUS_TERMINAL_RECORD_SHA256 = previous.TERMINAL_RECORD_SHA256
PREVIOUS_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
PREVIOUS_DATASET_SHA256 = previous.CANDIDATE_DATASET_SHA256
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_market_amount_profile_synchronization_v1"
FACTOR_NAME = "intraday_market_amount_profile_synchronization_240m"
FACTOR_FORMULA = (
    "corr(amount_i/sum(amount_i), "
    "leave_one_out_equal_weight_mean_j(amount_j/sum(amount_j))) "
    "across exact aligned 09:31-15:00 positions"
)
COMPARISON_FACTORS = (*previous.COMPARISON_FACTORS, previous.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*previous.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
BENCHMARK_COLUMNS = (
    "trade_date",
    "profile_position",
    "normalized_profile_sum",
    "valid_stock_count",
)
BENCHMARK_FILENAME = "market_amount_profile_benchmark_240m.parquet"
SOURCE_MINUTE_CODE_SET = engine.SOURCE_MINUTE_CODE_SET
CONTINUOUS_MINUTE_CODES = engine.CONTINUOUS_MINUTE_CODES
PROFILE_POSITIONS = 240
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
ENDPOINT_TOLERANCE = 1e-12
NUMERICAL_CONSTANT_SS_TOLERANCE = np.finfo(np.float64).eps

# Bound after the first deterministic no-return build published the snapshot.
CANDIDATE_MANIFEST_SHA256 = (
    "40f9700a919cc22f30bd928133fb20bc6af3476a7952020d180f712d97f063f5"
)
CANDIDATE_DATASET_SHA256 = (
    "26d82a495393cee45293d0ca00c444f88b2e25900d2ccc92fc0be5329fdf63a8"
)
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_INVALID_REQUIRED_AMOUNT_ROWS = 0
EXPECTED_NONPOSITIVE_TOTAL_AMOUNT_ROWS = 0
EXPECTED_INSUFFICIENT_PEER_ROWS = 0
EXPECTED_CONSTANT_OWN_PROFILE_ROWS = 0
EXPECTED_CONSTANT_MARKET_PROFILE_ROWS = 0


class IntradayMarketAmountProfileSynchronizationError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


@dataclass(frozen=True)
class AmountProfileBenchmark:
    """Dense same-date aligned normalized-profile sums and counts."""

    dates: pd.DatetimeIndex
    profile_sums: np.ndarray
    valid_stock_counts: np.ndarray
    date_to_index: dict[pd.Timestamp, int]
    frame_sha256: str


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and enforce the protocol frozen before candidate values."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "amount-profile protocol")
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_synchronization_"
            "no_return_preregistration"
        ),
    )
    current = spec.get("current_research_state") or {}
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("bar_grid") or {}
    validity = candidate.get("validity") or {}
    output = spec.get("derived_snapshot") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = chain.get("mechanism_overlap_reaudit") or {}
    predecessor = chain.get("prior_terminal_record") or {}
    prior_manifest = chain.get("opening_auction_amount_share_comparison_manifest") or {}
    forbidden = {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "any_daily_price",
        "any_forward_return",
    }
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256") == CURRENT_STATUS_SHA256
        and current.get("status")
        == (
            "aggregation_blocked_after_intraday_opening_auction_amount_share_"
            "terminal_rejection_zero_dual_gate_factors"
        )
        and current.get("terminal_mechanism_count_before_this_candidate") == 47
        and current.get("topk_qualified_factor_count") == 0
        and current.get("dual_gate_qualified_factor_count") == 0
        and current.get("aggregation_allowed") is False
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and predecessor.get("sha256") == PREVIOUS_TERMINAL_RECORD_SHA256
        and prior_manifest.get("sha256") == PREVIOUS_MANIFEST_SHA256
        and prior_manifest.get("dataset_sha256") == PREVIOUS_DATASET_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("diagnostic_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and set(candidate.get("source_fields_forbidden") or ()) == forbidden
        and grid.get("continuous_rows") == PROFILE_POSITIONS
        and grid.get("09_30_included") is False
        and grid.get("source_rows_merged") is False
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_240_amount_values_finite_and_nonnegative") is True
        and validity.get("strictly_positive_continuous_session_amount") is True
        and validity.get("minimum_leave_one_out_peers_at_every_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and validity.get("constant_own_profile_policy") == "missing"
        and validity.get("constant_leave_one_out_market_profile_policy") == "missing"
        and validity.get("allowed_closed_interval") == [-1, 1]
        and validity.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and output.get("output_run_id") == OUTPUT_RUN_ID
        and output.get("market_benchmark_artifact") == BENCHMARK_FILENAME
        and output.get("provider_request_allowed") is False
        and output.get("forward_return_fields_read") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("holding_period_sessions") == 3
        and tuple(item.get("name") for item in comparisons) == COMPARISON_FACTORS
        and tuple(item.get("score_direction") for item in comparisons)
        == COMPARISON_DIRECTIONS
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("all_twenty_three_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("daily_price_fields_read_before_registration") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "amount-profile synchronization protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate the append-only state and immediate terminal predecessor."""

    evidence: dict[str, Any] = {}
    for name in (
        "mechanism_overlap_reaudit",
        "prior_no_return_protocol",
        "prior_terminal_record",
    ):
        link = spec["source_chain"][name]
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}
    _require_file(
        DEFAULT_CURRENT_STATUS,
        CURRENT_STATUS_SHA256,
        "authoritative three-day research state",
    )
    state = research.load_three_day_iteration_status()
    summary = state.get("post_frontier_summary") or {}
    terminal = list(state.get("post_frontier_terminal_mechanisms") or [])
    decision = state.get("decision") or {}
    predecessor_state = (
        state.get("status")
        == (
            "aggregation_blocked_after_intraday_opening_auction_amount_share_"
            "terminal_rejection_zero_dual_gate_factors"
        )
        and summary.get("terminal_mechanism_count") == 47
        and len(terminal) == 47
        and terminal[-1].get("mechanism")
        == "tushare_intraday_opening_auction_amount_share_241m"
        and (terminal[-1].get("record") or {}).get("sha256")
        == PREVIOUS_TERMINAL_RECORD_SHA256
    )
    terminal_state = (
        state.get("status")
        == (
            "aggregation_blocked_after_intraday_market_amount_profile_"
            "synchronization_terminal_rejection_zero_dual_gate_factors"
        )
        and summary.get("terminal_mechanism_count") == 48
        and len(terminal) == 48
        and terminal[-2].get("mechanism")
        == "tushare_intraday_opening_auction_amount_share_241m"
        and terminal[-1].get("mechanism")
        == "tushare_intraday_market_amount_profile_synchronization_240m"
        and (terminal[-1].get("record") or {}).get("sha256") == TERMINAL_RECORD_SHA256
    )
    if not (
        (predecessor_state or terminal_state)
        and summary.get("admitted_factor_count") == 0
        and summary.get("aggregation_candidate_count") == 0
        and decision.get("aggregation_allowed") is False
        and decision.get("current_scoring_allowed") is False
        and decision.get("selection_allowed") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "authoritative three-day state changed after preregistration"
        )
    if previous.load_terminal_record_if_present() is None:
        raise IntradayMarketAmountProfileSynchronizationError(
            "opening-auction amount-share terminal record is required"
        )
    evidence["current_research_state"] = {
        "path": str(DEFAULT_CURRENT_STATUS.resolve()),
        "sha256": CURRENT_STATUS_SHA256,
        "terminal_mechanism_count": int(summary["terminal_mechanism_count"]),
        "preregistered_predecessor_binding_preserved": True,
    }
    context = spec.get("point_in_time_context") or {}
    for name in ("source_universe", "holding_universe", "calendar"):
        link = context.get(name) or {}
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}
    quality = context.get("quarterly_quality") or {}
    for path_key, hash_key in (
        ("path", "sha256"),
        ("manifest_path", "manifest_sha256"),
    ):
        path = _repository_path(str(quality[path_key]))
        expected = str(quality[hash_key])
        _require_file(path, expected, path_key.replace("_", " "))
        evidence[f"quarterly_quality_{path_key}"] = {
            "path": str(path),
            "sha256": expected,
        }
    return evidence


def _validate_previous_manifest(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], Path]:
    link = spec["source_chain"]["opening_auction_amount_share_comparison_manifest"]
    path = (data_root / str(link["path_below_data_root"])).resolve()
    _require_file(path, PREVIOUS_MANIFEST_SHA256, "opening-auction manifest")
    manifest = research.load_json_record(
        path,
        kind="a_share_tushare_intraday_opening_auction_amount_share_snapshot",
    )
    previous._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    if manifest.get("dataset_sha256") != PREVIOUS_DATASET_SHA256:
        raise IntradayMarketAmountProfileSynchronizationError(
            "opening-auction comparison dataset changed"
        )
    return manifest, path


def validate_external_chain(spec: dict[str, Any], data_root: Path) -> tuple[Any, ...]:
    with _original_engine_binding():
        chain = previous.validate_external_chain(
            previous.load_preregistration(),
            data_root,
        )
    prior_manifest, prior_path = _validate_previous_manifest(spec, data_root)
    return (*chain, prior_manifest, prior_path)


@contextmanager
def _original_engine_binding() -> Iterable[None]:
    """Restore candidate 46 while traversing candidate 47's source chain."""

    active = {name: getattr(engine, name) for name in _ENGINE_BINDING_NAMES}
    for name, value in _ORIGINAL_ENGINE_BINDING.items():
        setattr(engine, name, value)
    try:
        yield
    finally:
        for name, value in active.items():
            setattr(engine, name, value)


def extract_partition_profiles(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    """Extract normalized 240-position profiles without price or outcome data."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = engine._normalized_base(base, symbol)
    if base_work.empty:
        return (
            base_work,
            np.empty((0, PROFILE_POSITIONS)),
            np.empty(0, dtype=bool),
            {
                "invalid_required_amount_rows": 0,
                "nonpositive_total_amount_rows": 0,
            },
        )
    symbol = symbol.upper()
    if raw.empty:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"raw source is empty for nonempty base partition {symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"raw identity or timestamp violation for {symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise IntradayMarketAmountProfileSynchronizationError(
            f"every source stock-day must retain the exact 241-row grid for {symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise IntradayMarketAmountProfileSynchronizationError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"joint-clean base dates do not match raw dates for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    amounts = (
        continuous["amount"]
        .to_numpy(dtype=float)
        .reshape(
            -1,
            PROFILE_POSITIONS,
        )
    )
    required_valid = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    totals = np.where(required_valid[:, None], amounts, 0.0).sum(axis=1)
    positive_total = required_valid & np.isfinite(totals) & (totals > 0.0)
    profiles = np.full_like(amounts, np.nan, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(
            amounts,
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
            "invalid_required_amount_rows": int((~required_valid).sum()),
            "nonpositive_total_amount_rows": int(
                (required_valid & ~positive_total).sum()
            ),
        },
    )


def _read_verified_profiles(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    return extract_partition_profiles(
        raw,
        base,
        symbol=str(joint_record["symbol"]),
    )


def _symbol_market_contribution(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[str, np.ndarray, np.ndarray, dict[str, int]]:
    symbol = str(pairs[0][1]["symbol"])
    date_parts: list[np.ndarray] = []
    profile_parts: list[np.ndarray] = []
    quality: Counter[str] = Counter()
    for raw_record, joint_record in sorted(
        pairs,
        key=lambda pair: int(pair[1]["year"]),
    ):
        base, profiles, _, observed = _read_verified_profiles(
            raw_record,
            joint_record,
        )
        date_parts.append(
            pd.to_datetime(base["trade_date"]).to_numpy(dtype="datetime64[ns]")
        )
        profile_parts.append(profiles)
        quality.update(observed)
    dates = (
        np.concatenate(date_parts)
        if date_parts
        else np.empty(0, dtype="datetime64[ns]")
    )
    profiles = (
        np.concatenate(profile_parts, axis=0)
        if profile_parts
        else np.empty((0, PROFILE_POSITIONS))
    )
    if pd.Index(dates).duplicated().any():
        raise IntradayMarketAmountProfileSynchronizationError(
            f"duplicate market-contribution date for {symbol}"
        )
    return symbol, dates, profiles, dict(quality)


def _atomic_write_accumulator(
    path: Path,
    *,
    dates: pd.DatetimeIndex,
    profile_sums: np.ndarray,
    valid_counts: np.ndarray,
    processed_symbols: set[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.npz")
    np.savez_compressed(
        temporary,
        schema_version=np.array([1], dtype=np.int16),
        protocol_sha256=np.array([PREREGISTRATION_SHA256]),
        raw_manifest_sha256=np.array([RAW_MANIFEST_SHA256]),
        joint_manifest_sha256=np.array([JOINT_MANIFEST_SHA256]),
        dates=dates.to_numpy(dtype="datetime64[ns]"),
        profile_sums=profile_sums,
        valid_counts=valid_counts,
        processed_symbols=np.array(sorted(processed_symbols), dtype="U16"),
    )
    temporary.replace(path)


def _load_or_create_accumulator(
    path: Path,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray, set[str]]:
    shape = (len(dates), PROFILE_POSITIONS)
    if not path.is_file():
        return np.zeros(shape, dtype=np.float64), np.zeros(shape, dtype=np.int32), set()
    try:
        with np.load(path, allow_pickle=False) as state:
            observed_dates = state["dates"].astype("datetime64[ns]")
            profile_sums = state["profile_sums"].astype(np.float64, copy=True)
            valid_counts = state["valid_counts"].astype(np.int32, copy=True)
            processed = {str(value) for value in state["processed_symbols"].tolist()}
            valid = (
                state["schema_version"].tolist() == [1]
                and state["protocol_sha256"].tolist() == [PREREGISTRATION_SHA256]
                and state["raw_manifest_sha256"].tolist() == [RAW_MANIFEST_SHA256]
                and state["joint_manifest_sha256"].tolist() == [JOINT_MANIFEST_SHA256]
                and np.array_equal(
                    observed_dates,
                    dates.to_numpy(dtype="datetime64[ns]"),
                )
                and profile_sums.shape == shape
                and valid_counts.shape == shape
                and np.isfinite(profile_sums).all()
                and (valid_counts >= 0).all()
            )
    except (OSError, ValueError, KeyError) as exc:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"market-profile accumulator is unreadable: {path}"
        ) from exc
    if not valid:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"market-profile accumulator changed: {path}"
        )
    return profile_sums, valid_counts, processed


def _build_market_benchmark(
    *,
    pairs_by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    dates: pd.DatetimeIndex,
    partial_root: Path,
    final_root: Path,
    workers: int,
) -> tuple[AmountProfileBenchmark, dict[str, Any]]:
    accumulator_path = partial_root / ".metadata/market_profile_accumulator.npz"
    profile_sums, valid_counts, processed = _load_or_create_accumulator(
        accumulator_path,
        dates,
    )
    if unexpected := processed - set(pairs_by_symbol):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"market-profile accumulator contains unknown symbols: {sorted(unexpected)}"
        )
    date_to_index = {pd.Timestamp(value): index for index, value in enumerate(dates)}
    symbols = [symbol for symbol in sorted(pairs_by_symbol) if symbol not in processed]
    quality: Counter[str] = Counter()
    batch_size = max(8, workers * 8)
    print(
        f"building amount-profile accumulator for {len(pairs_by_symbol):,} symbols; "
        f"resumed={len(processed):,}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(0, len(symbols), batch_size):
            batch = symbols[offset : offset + batch_size]
            results = list(
                pool.map(
                    _symbol_market_contribution,
                    [pairs_by_symbol[symbol] for symbol in batch],
                )
            )
            for symbol, contribution_dates, profiles, observed in results:
                try:
                    indices = np.fromiter(
                        (
                            date_to_index[pd.Timestamp(value).normalize()]
                            for value in contribution_dates
                        ),
                        dtype=np.int64,
                        count=len(contribution_dates),
                    )
                except KeyError as exc:
                    raise IntradayMarketAmountProfileSynchronizationError(
                        "market-profile contribution date is outside the frozen "
                        f"calendar: {exc}"
                    ) from exc
                valid_rows = np.isfinite(profiles).all(axis=1)
                if valid_rows.any():
                    profile_sums[indices[valid_rows], :] += profiles[valid_rows, :]
                    valid_counts[indices[valid_rows], :] += 1
                processed.add(symbol)
                quality.update(observed)
            del results
            gc.collect()
            if (offset // batch_size + 1) % 5 == 0 or offset + batch_size >= len(
                symbols
            ):
                _atomic_write_accumulator(
                    accumulator_path,
                    dates=dates,
                    profile_sums=profile_sums,
                    valid_counts=valid_counts,
                    processed_symbols=processed,
                )
                print(
                    f"market-profile progress symbols={len(processed):,}/"
                    f"{len(pairs_by_symbol):,}",
                    flush=True,
                )
    if processed != set(pairs_by_symbol):
        raise IntradayMarketAmountProfileSynchronizationError(
            "market-profile accumulator did not consume every source symbol"
        )
    nonempty = valid_counts.max(axis=1) > 0
    if not nonempty.any() or not np.equal(valid_counts, valid_counts[:, :1]).all():
        raise IntradayMarketAmountProfileSynchronizationError(
            "market-profile accumulator counts are invalid"
        )
    active_dates = dates[nonempty]
    active_sums = profile_sums[nonempty, :]
    active_counts = valid_counts[nonempty, :]
    frame = pd.DataFrame(
        {
            "trade_date": np.repeat(active_dates.to_numpy(), PROFILE_POSITIONS),
            "profile_position": np.tile(
                np.arange(PROFILE_POSITIONS, dtype=np.int16),
                len(active_dates),
            ),
            "normalized_profile_sum": active_sums.reshape(-1),
            "valid_stock_count": active_counts.reshape(-1),
        }
    ).loc[:, BENCHMARK_COLUMNS]
    benchmark_path = partial_root / BENCHMARK_FILENAME
    foundation.atomic_write_frame(frame, benchmark_path)
    frame_sha256 = foundation.frame_digest(frame)
    benchmark = AmountProfileBenchmark(
        dates=active_dates,
        profile_sums=active_sums,
        valid_stock_counts=active_counts,
        date_to_index={
            pd.Timestamp(value).normalize(): index
            for index, value in enumerate(active_dates)
        },
        frame_sha256=frame_sha256,
    )
    per_date_counts = active_counts[:, 0]
    evidence = {
        "path": str(final_root / BENCHMARK_FILENAME),
        "rows": int(len(frame)),
        "trade_dates": int(len(active_dates)),
        "profile_positions_per_date": PROFILE_POSITIONS,
        "output_byte_sha256": foundation.file_digest(benchmark_path),
        "output_frame_sha256": frame_sha256,
        "valid_stock_count_minimum": int(per_date_counts.min()),
        "valid_stock_count_p05": float(np.quantile(per_date_counts, 0.05)),
        "valid_stock_count_median": float(np.median(per_date_counts)),
        "valid_stock_count_maximum": int(per_date_counts.max()),
        "fresh_pass_invalid_required_amount_rows": int(
            quality["invalid_required_amount_rows"]
        ),
        "fresh_pass_nonpositive_total_amount_rows": int(
            quality["nonpositive_total_amount_rows"]
        ),
        "processed_symbol_count": int(len(processed)),
        "source_fields_read": list(RAW_COLUMNS),
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    return benchmark, evidence


def _benchmark_for_dates(
    benchmark: AmountProfileBenchmark,
    dates: Sequence[pd.Timestamp],
) -> tuple[np.ndarray, np.ndarray]:
    try:
        indices = np.fromiter(
            (
                benchmark.date_to_index[pd.Timestamp(value).normalize()]
                for value in dates
            ),
            dtype=np.int64,
            count=len(dates),
        )
    except KeyError as exc:
        raise IntradayMarketAmountProfileSynchronizationError(
            f"candidate date is missing from market-profile benchmark: {exc}"
        ) from exc
    return (
        benchmark.profile_sums[indices],
        benchmark.valid_stock_counts[indices],
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    benchmark: AmountProfileBenchmark,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the frozen leave-one-out amount-profile synchronization."""

    base_work, profiles, valid, source_quality = extract_partition_profiles(
        raw,
        base,
        symbol=symbol,
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
    sums, counts = _benchmark_for_dates(benchmark, base_work["trade_date"])
    own = np.where(np.isfinite(profiles), profiles, 0.0)
    own_count = valid[:, None].astype(np.int32)
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        peer_profiles = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        own_observations = np.isfinite(profiles).sum(axis=1, keepdims=True)
        own_means = np.divide(
            np.where(np.isfinite(profiles), profiles, 0.0).sum(
                axis=1,
                keepdims=True,
            ),
            own_observations,
            out=np.full((len(profiles), 1), np.nan),
            where=own_observations > 0,
        )
        market_observations = np.isfinite(peer_profiles).sum(
            axis=1,
            keepdims=True,
        )
        market_means = np.divide(
            np.where(np.isfinite(peer_profiles), peer_profiles, 0.0).sum(
                axis=1,
                keepdims=True,
            ),
            market_observations,
            out=np.full((len(peer_profiles), 1), np.nan),
            where=market_observations > 0,
        )
        own_centered = profiles - own_means
        market_centered = peer_profiles - market_means
        own_ss = np.nansum(own_centered * own_centered, axis=1)
        market_ss = np.nansum(market_centered * market_centered, axis=1)
        covariance = np.nansum(own_centered * market_centered, axis=1)
        denominator = np.sqrt(own_ss * market_ss)
        values = covariance / denominator
    constant_own = valid & (own_ss <= NUMERICAL_CONSTANT_SS_TOLERANCE)
    constant_market = (
        valid & sufficient & (market_ss <= NUMERICAL_CONSTANT_SS_TOLERANCE)
    )
    finite = np.isfinite(values)
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = valid & sufficient & finite & (low_near | high_near)
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = valid & sufficient & ~constant_own & ~constant_market & finite & in_range
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        **source_quality,
        "insufficient_leave_one_out_peer_rows": int((valid & ~sufficient).sum()),
        "constant_own_profile_rows": int(constant_own.sum()),
        "constant_market_profile_rows": int(constant_market.sum()),
        "nonfinite_correlation_rows": int(
            (valid & sufficient & ~constant_own & ~constant_market & ~finite).sum()
        ),
        "endpoint_canonicalized_rows": int(canonicalized.sum()),
        "range_violation_rows": int(
            (
                valid
                & sufficient
                & ~constant_own
                & ~constant_market
                & finite
                & ~in_range
            ).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / (
            "derived/a_share/rich/tushare/"
            "minute_intraday_market_amount_profile_synchronization"
        )
        / OUTPUT_RUN_ID
    )


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: Any,
    benchmark: AmountProfileBenchmark,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind")
        == (
            "a_share_tushare_intraday_market_amount_profile_synchronization_"
            "partition"
        )
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("market_benchmark_frame_sha256") == benchmark.frame_sha256
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
        raise IntradayMarketAmountProfileSynchronizationError(
            f"completed candidate checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise IntradayMarketAmountProfileSynchronizationError(
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
    benchmark: AmountProfileBenchmark,
    partial_root: Path,
    final_root: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = foundation.partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths, benchmark)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayMarketAmountProfileSynchronizationError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    output, quality = compute_partition_frame(
        raw,
        base,
        benchmark,
        symbol=str(joint_record["symbol"]),
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": (
            "a_share_tushare_intraday_market_amount_profile_synchronization_partition"
        ),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "market_benchmark_frame_sha256": benchmark.frame_sha256,
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
        "minute_amount_fields_read": ["amount"],
        "minute_price_or_volume_fields_read": [],
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
    benchmark: AmountProfileBenchmark,
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
            benchmark=benchmark,
            partial_root=partial_root,
            final_root=final_root,
        )
        records.append(record)
        eligible_dates.update(dates)
        resumed += int(was_resumed)
    return records, eligible_dates, resumed


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    """Validate the immutable candidate snapshot after publication."""

    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    counter_names = (
        "invalid_required_amount_rows",
        "nonpositive_total_amount_rows",
        "insufficient_leave_one_out_peer_rows",
        "constant_own_profile_rows",
        "constant_market_profile_rows",
        "nonfinite_correlation_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    transient_engine_manifest = (
        not require_fingerprint_constants
        and manifest.get("kind")
        == "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    )
    if not (
        (
            manifest.get("kind")
            == (
                "a_share_tushare_intraday_market_amount_profile_"
                "synchronization_snapshot"
            )
            or transient_engine_manifest
        )
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
            for name in counter_names
        )
        and benchmark.get("rows")
        == benchmark.get("trade_dates", -1) * PROFILE_POSITIONS
        and benchmark.get("profile_positions_per_date") == PROFILE_POSITIONS
        and benchmark.get("processed_symbol_count") == 5_396
        and benchmark.get("valid_stock_count_minimum", 0)
        >= MINIMUM_LEAVE_ONE_OUT_PEERS + 1
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and (
            manifest.get("leave_one_out_equal_weight_market_profile") is True
            or (
                transient_engine_manifest
                and manifest.get("leave_one_out_equal_weight_market") is True
            )
        )
        and manifest.get("minimum_leave_one_out_peers") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "amount-profile synchronization snapshot identity is rejected"
        )
    if require_fingerprint_constants and not (
        CANDIDATE_MANIFEST_SHA256
        and CANDIDATE_DATASET_SHA256
        and EXPECTED_ELIGIBLE_ROWS >= 0
        and manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_amount_rows")
        == EXPECTED_INVALID_REQUIRED_AMOUNT_ROWS
        and quality.get("nonpositive_total_amount_rows")
        == EXPECTED_NONPOSITIVE_TOTAL_AMOUNT_ROWS
        and quality.get("insufficient_leave_one_out_peer_rows")
        == EXPECTED_INSUFFICIENT_PEER_ROWS
        and quality.get("constant_own_profile_rows")
        == EXPECTED_CONSTANT_OWN_PROFILE_ROWS
        and quality.get("constant_market_profile_rows")
        == EXPECTED_CONSTANT_MARKET_PROFILE_ROWS
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate fingerprint and aggregate constants are not bound"
        )


def load_terminal_record_if_present() -> dict[str, Any] | None:
    """Validate and return the immutable terminal record when it exists."""

    if not DEFAULT_TERMINAL_RECORD.exists():
        return None
    _require_file(
        DEFAULT_TERMINAL_RECORD,
        TERMINAL_RECORD_SHA256,
        "amount-profile synchronization terminal record",
    )
    record = research.load_json_record(
        DEFAULT_TERMINAL_RECORD,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_"
            "synchronization_research_record"
        ),
    )
    artifacts = record.get("historical_artifacts") or {}
    result = record.get("return_results") or {}
    decision = record.get("decision") or {}
    expected_artifacts = {
        "diagnostic": DIAGNOSTIC_SHA256,
        "stability_audit": STABILITY_AUDIT_SHA256,
        "topk_viability_audit": TOPK_AUDIT_SHA256,
        "single_use_consumption_marker": CONSUMPTION_MARKER_SHA256,
    }
    for name, expected in expected_artifacts.items():
        link = artifacts.get(name) or {}
        path = _repository_path(str(link.get("path", "")))
        _require_file(path, expected, name.replace("_", " "))
        if link.get("sha256") != expected:
            raise IntradayMarketAmountProfileSynchronizationError(
                f"terminal record has the wrong {name} fingerprint"
            )
    if not (
        record.get("status")
        == "terminal_rejected_at_association_stability_and_executable_topk_gates"
        and (record.get("factor") or {}).get("name") == FACTOR_NAME
        and (record.get("source_chain") or {})
        .get("candidate_manifest", {})
        .get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (record.get("ordered_protocol") or {})
        .get("no_return_audit", {})
        .get("sha256")
        == NO_RETURN_AUDIT_SHA256
        and (record.get("ordered_protocol") or {})
        .get("diagnostic_preregistration", {})
        .get("sha256")
        == DIAGNOSTIC_PREREGISTRATION_SHA256
        and result.get("cohorts") == 539
        and result.get("mean_rank_ic") == -0.011744812824529938
        and result.get("association_stability_gate_passed") is False
        and result.get("execution_aware_top3_net_cumulative_return")
        == -0.536413733053481
        and result.get("pilot_net_cumulative_return_at_ten_bp_each_side")
        == -0.1317638058590641
        and result.get("pilot_maximum_daily_amount_participation")
        == 0.0004074745219262403
        and result.get("topk_viability_gate_passed") is False
        and result.get("dual_gate_passed") is False
        and decision.get("terminally_reject_exact_factor_direction") is True
        and decision.get("aggregation_candidate_added") is False
        and decision.get("aggregation_allowed") is False
        and decision.get("current_scoring_allowed") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "amount-profile synchronization terminal record no longer matches "
            "its frozen result"
        )
    return record


def _activate_engine() -> None:
    """Bind the proven cross-sectional engine to this frozen mechanism."""

    engine.DEFAULT_PREREGISTRATION = DEFAULT_PREREGISTRATION
    engine.PREREGISTRATION_SHA256 = PREREGISTRATION_SHA256
    engine.DEFAULT_TERMINAL_RECORD = DEFAULT_TERMINAL_RECORD
    engine.CANDIDATE_MANIFEST_SHA256 = CANDIDATE_MANIFEST_SHA256
    engine.CANDIDATE_DATASET_SHA256 = CANDIDATE_DATASET_SHA256
    engine.EXPECTED_ELIGIBLE_ROWS = EXPECTED_ELIGIBLE_ROWS
    engine.OUTPUT_RUN_ID = OUTPUT_RUN_ID
    engine.FACTOR_NAME = FACTOR_NAME
    engine.FACTOR_FORMULA = FACTOR_FORMULA
    engine.COMPARISON_FACTORS = COMPARISON_FACTORS
    engine.COMPARISON_DIRECTIONS = COMPARISON_DIRECTIONS
    engine.RAW_COLUMNS = RAW_COLUMNS
    engine.OUTPUT_COLUMNS = OUTPUT_COLUMNS
    engine.BENCHMARK_FILENAME = BENCHMARK_FILENAME
    engine.RETURN_POSITIONS = PROFILE_POSITIONS
    engine.MINIMUM_LEAVE_ONE_OUT_PEERS = MINIMUM_LEAVE_ONE_OUT_PEERS
    engine.load_preregistration = load_preregistration
    engine.validate_repository_chain = validate_repository_chain
    engine.validate_external_chain = validate_external_chain
    engine.load_terminal_record_if_present = load_terminal_record_if_present
    engine._build_market_benchmark = _build_market_benchmark
    engine._process_symbol = _process_symbol
    engine._validate_snapshot_manifest = _validate_snapshot_manifest
    engine.output_root = output_root


def _finalize_engine_manifest(path: Path) -> None:
    """Replace the generic engine envelope before binding snapshot bytes."""

    manifest = research.load_json_record(path)
    if manifest.get("kind") == (
        "a_share_tushare_intraday_market_amount_profile_synchronization_snapshot"
    ):
        return
    if (
        CANDIDATE_MANIFEST_SHA256
        or manifest.get("kind")
        != "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
        or manifest.get("protocol_sha256") != PREREGISTRATION_SHA256
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "cannot finalize an unexpected generic engine manifest"
        )
    manifest["kind"] = (
        "a_share_tushare_intraday_market_amount_profile_synchronization_snapshot"
    )
    manifest["source_amount_read"] = True
    manifest["source_price_or_volume_read"] = False
    manifest["standalone_09_30_row_excluded_from_formula"] = True
    manifest["continuous_session_positions"] = PROFILE_POSITIONS
    manifest["leave_one_out_equal_weight_market_profile"] = True
    manifest["benchmark_semantics"] = (
        "same_date_aligned_sum_and_count_of_complete_normalized_amount_profiles"
    )
    for key in (
        "source_close_read",
        "source_volume_or_amount_read",
        "source_open_high_low_read",
        "lunch_boundary_excluded_from_formula",
        "leave_one_out_equal_weight_market",
    ):
        manifest.pop(key, None)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
    foundation.atomic_write_json(manifest, path)


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build the two-pass immutable candidate snapshot."""

    _activate_engine()
    path = engine.build_snapshot(data_root=data_root, workers=workers)
    (path.parent / ".metadata/market_profile_accumulator.npz").unlink(missing_ok=True)
    _finalize_engine_manifest(path)
    return path


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, int]:
    return engine.verify_snapshot_files(manifest, manifest_path, workers)


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
        raise IntradayMarketAmountProfileSynchronizationError(
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
        or (values < -1.0).any()
        or (values > 1.0).any()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate frame values or keys are invalid"
        )
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    _activate_engine()
    return engine.coverage_and_capacity(candidate, eligible_keys, spec)


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    chain: tuple[Any, ...],
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    """Evaluate all 23 terminal comparisons serially with bounded memory."""

    print(
        "coverage passed; loading twenty-three terminal comparisons serially",
        flush=True,
    )
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    candidate = candidate_quality[["trade_date", "symbol", FACTOR_NAME]].copy()
    candidate_keys = engine._compact_stock_day_keys(
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
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate quality keys or values changed before uniqueness"
        )
    del candidate, candidate_quality, order
    gc.collect()
    results: list[dict[str, Any]] = []
    verifications: dict[str, Any] = {}

    joint_manifest_path = Path(chain[3])
    base_factors = COMPARISON_FACTORS[:4]
    base_values = engine._load_filtered_comparison_values(
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
            engine._aligned_comparison_result(
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
        raise IntradayMarketAmountProfileSynchronizationError(
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
        print(
            f"serial uniqueness comparison {index}/23: {factor}",
            flush=True,
        )
        verifications[factor] = engine._verify_comparison_snapshot_outputs(
            manifest,
            manifest_path,
            workers,
        )
        values = engine._load_filtered_comparison_values(
            manifest_path.parent / "partitions",
            [factor],
            candidate_keys,
        )[factor]
        results.append(
            engine._aligned_comparison_result(
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
        "all_twenty_three_comparisons_passed": bool(
            len(results) == 23 and all(item["gate_passed"] for item in results)
        ),
    }


def _find_existing_audit(
    experiment_root: Path,
    manifest_sha256: str,
) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_intraday_market_amount_profile_synchronization_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == (
                "a_share_tushare_intraday_market_amount_profile_"
                "synchronization_no_return_audit"
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
    """Run coverage/capacity before loading the 23 comparisons."""

    if not CANDIDATE_MANIFEST_SHA256:
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate snapshot fingerprint must be bound before audit"
        )
    _activate_engine()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    joint = chain[1]
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "amount-profile synchronization manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        load_terminal_record_if_present()
        return existing
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    candidate = load_candidate_frame(manifest_path, manifest)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate_quality, coverage = coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
    )
    del candidate, eligible_keys
    gc.collect()
    uniqueness: dict[str, Any] = {
        "comparison_values_loaded_after_coverage_pass": False,
        "all_twenty_three_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, chain, spec, workers)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_twenty_three_comparisons_passed"]
    )
    status = (
        "passed_no_return_coverage_capacity_and_uniqueness_pending_separate_return_diagnostic_preregistration"
        if passed
        else (
            "terminal_rejected_at_no_return_uniqueness_gate"
            if coverage["gate_passed_before_comparison_values"]
            else "terminal_rejected_at_no_return_coverage_or_capacity_gate"
        )
    )
    audit = {
        "schema_version": 1,
        "kind": (
            "a_share_tushare_intraday_market_amount_profile_"
            "synchronization_no_return_audit"
        ),
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": (
            "ordered_candidate_coverage_capacity_then_twenty_three_terminal_"
            "factor_uniqueness_without_daily_prices_or_forward_returns"
        ),
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "dataset_sha256": str(manifest["dataset_sha256"]),
            "rows": int(manifest["rows"]),
            "eligible_rows": int(manifest["eligible_rows"]),
        },
        "source_chain": {
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "joint_dataset_sha256": str(joint["dataset_sha256"]),
            "opening_auction_amount_share_manifest_sha256": (PREVIOUS_MANIFEST_SHA256),
            "repository_evidence": repository_evidence,
            "snapshot_file_verification": verification,
        },
        "candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
        },
        "coverage_and_capacity": coverage,
        "uniqueness": uniqueness,
        "decision": {
            "all_no_return_gates_passed": passed,
            "separate_return_diagnostic_preregistration_allowed": passed,
            "return_diagnostic_authorized_without_separate_preregistration": False,
            "aggregation_allowed": False,
            "current_scoring_allowed": False,
            "selection_allowed": False,
            "sizing_or_orders_allowed": False,
            "level2_intake_justified": False,
        },
        "source_fields_loaded": list(RAW_COLUMNS),
        "minute_amount_fields_loaded": ["amount"],
        "minute_price_or_volume_fields_loaded": [],
        "comparison_fields_loaded": (
            list(COMPARISON_FACTORS)
            if uniqueness["comparison_values_loaded_after_coverage_pass"]
            else []
        ),
        "daily_price_fields_loaded": [],
        "forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "investment_advice": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = experiment_root / (
        f"{run_id}_intraday_market_amount_profile_synchronization_"
        "no_return_audit.json"
    )
    foundation.atomic_write_json(audit, path)
    return path


def load_diagnostic_preregistration(
    path: Path = DEFAULT_DIAGNOSTIC_PREREGISTRATION,
) -> dict[str, Any]:
    """Load the protocol frozen before the first forward-return read."""

    path = path.expanduser().resolve()
    _require_file(
        path,
        DIAGNOSTIC_PREREGISTRATION_SHA256,
        "amount-profile diagnostic protocol",
    )
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_synchronization_"
            "diagnostic_preregistration"
        ),
    )
    factor = spec.get("factor") or {}
    evidence = spec.get("no_return_evidence") or {}
    snapshot = evidence.get("candidate_snapshot") or {}
    audit = evidence.get("ordered_audit") or {}
    coverage = evidence.get("coverage_and_capacity") or {}
    uniqueness = evidence.get("uniqueness") or {}
    comparison_medians = uniqueness.get("comparison_medians") or {}
    holding = spec.get("holding_protocol") or {}
    gates = spec.get("diagnostic_gates") or {}
    decision = spec.get("post_diagnostic_decision") or {}
    boundary = spec.get("research_boundary") or {}
    quality_expectations = {
        "invalid_required_amount_rows": EXPECTED_INVALID_REQUIRED_AMOUNT_ROWS,
        "nonpositive_total_amount_rows": EXPECTED_NONPOSITIVE_TOTAL_AMOUNT_ROWS,
        "insufficient_leave_one_out_peer_rows": EXPECTED_INSUFFICIENT_PEER_ROWS,
        "constant_own_profile_rows": EXPECTED_CONSTANT_OWN_PROFILE_ROWS,
        "constant_market_profile_rows": EXPECTED_CONSTANT_MARKET_PROFILE_ROWS,
        "nonfinite_correlation_rows": 0,
        "endpoint_canonicalized_rows": 0,
        "range_violation_rows": 0,
    }
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == (
            "frozen_after_no_return_coverage_capacity_and_uniqueness_pass_"
            "before_first_forward_return_read"
        )
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and factor.get("formula") == FACTOR_FORMULA
        and factor.get("factor_values_observed_before_no_return_preregistration")
        is False
        and factor.get(
            "forward_returns_observed_before_this_diagnostic_preregistration"
        )
        is False
        and (evidence.get("protocol") or {}).get("sha256") == PREREGISTRATION_SHA256
        and snapshot.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and snapshot.get("partitions") == 33_015
        and snapshot.get("rows") == 7_724_498
        and snapshot.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and all(
            snapshot.get(name) == value for name, value in quality_expectations.items()
        )
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("forward_return_fields_read") is False
        and coverage.get("quality_listing_eligible_rows") == 1_331_759
        and coverage.get("candidate_eligible_rows_after_quality_and_listing")
        == 1_330_171
        and coverage.get("median_coverage") == 0.9994517542211769
        and coverage.get("p05_coverage") == 0.9956886515772271
        and coverage.get("p05_eligible_names") == 138
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 540
        and coverage.get("observed_calendar_years")
        == [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        and coverage.get("gate_passed") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("maximum_observed_absolute_median_daily_rank_correlation")
        == 0.5667050400934569
        and tuple(comparison_medians) == COMPARISON_FACTORS
        and uniqueness.get("all_twenty_three_comparisons_passed") is True
        and holding.get("universe") == "buyable_main_chinext"
        and holding.get("minimum_listing_sessions") == research.MIN_LISTING_SESSIONS
        and holding.get("development_start") == "2019-01-01"
        and holding.get("development_end") == "2025-12-31"
        and holding.get("holding_period_trading_days") == 3
        and holding.get("non_overlapping_cohorts") is True
        and holding.get("topk") == 3
        and holding.get("open_cost") == 0.00012
        and holding.get("close_cost") == 0.00062
        and gates.get("minimum_non_overlapping_cohorts") == 200
        and gates.get("minimum_observed_calendar_years") == 5
        and decision.get("same_history_combination_return_evaluation_allowed") is False
        and decision.get("current_scoring_selection_sizing_or_orders_allowed") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
        and boundary.get("training_or_model_fitting_performed") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "amount-profile diagnostic protocol no longer matches its frozen "
            "definition"
        )
    return spec


def validate_diagnostic_source_chain(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any]]:
    """Reproduce all immutable no-return evidence before daily prices."""

    no_return = spec["no_return_evidence"]
    protocol_path = _repository_path(str(no_return["protocol"]["path"]))
    _require_file(protocol_path, PREREGISTRATION_SHA256, "no-return protocol")
    snapshot_link = no_return["candidate_snapshot"]
    manifest_path = (data_root / str(snapshot_link["path_below_data_root"])).resolve()
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "amount-profile candidate manifest",
    )
    manifest = research.load_json_record(
        manifest_path,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_" "synchronization_snapshot"
        ),
    )
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    if not (
        manifest.get("status")
        == (
            "candidate_feature_complete_pending_ordered_no_return_"
            "coverage_capacity_and_uniqueness"
        )
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("dataset_sha256") == snapshot_link.get("dataset_sha256")
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_amount_rows") == 0
        and quality.get("nonpositive_total_amount_rows") == 0
        and quality.get("insufficient_leave_one_out_peer_rows") == 0
        and quality.get("constant_own_profile_rows") == 0
        and quality.get("constant_market_profile_rows") == 0
        and quality.get("nonfinite_correlation_rows") == 0
        and quality.get("endpoint_canonicalized_rows") == 0
        and quality.get("range_violation_rows") == 0
        and benchmark.get("output_byte_sha256")
        == snapshot_link.get("market_benchmark_output_byte_sha256")
        and benchmark.get("output_frame_sha256")
        == snapshot_link.get("market_benchmark_output_frame_sha256")
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_amount_read") is True
        and manifest.get("source_price_or_volume_read") is False
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("leave_one_out_equal_weight_market_profile") is True
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate snapshot conflicts with the diagnostic preregistration"
        )
    audit_link = no_return["ordered_audit"]
    audit_path = _repository_path(str(audit_link["path"]))
    _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "ordered no-return audit")
    audit = research.load_json_record(
        audit_path,
        kind=(
            "a_share_tushare_intraday_market_amount_profile_"
            "synchronization_no_return_audit"
        ),
    )
    if not (
        audit.get("status") == audit_link.get("status")
        and (audit.get("candidate_snapshot") or {}).get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (audit.get("coverage_and_capacity") or {}).get(
            "gate_passed_before_comparison_values"
        )
        is True
        and (audit.get("uniqueness") or {}).get("all_twenty_three_comparisons_passed")
        is True
        and (audit.get("decision") or {}).get(
            "separate_return_diagnostic_preregistration_allowed"
        )
        is True
        and audit.get("daily_price_fields_loaded") == []
        and audit.get("forward_return_fields_read") is False
    ):
        raise IntradayMarketAmountProfileSynchronizationError(
            "ordered no-return audit does not authorize the frozen diagnostic"
        )
    repository_evidence = validate_repository_chain(load_preregistration())
    for name, link in (
        ("accepted_daily_price_basis", spec["accepted_daily_price_basis"]),
        ("quarterly_quality", spec["quarterly_quality"]),
    ):
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {"path": str(path), "sha256": expected}
    quarterly_quality = spec["quarterly_quality"]
    quality_manifest_path = _repository_path(str(quarterly_quality["manifest_path"]))
    _require_file(
        quality_manifest_path,
        str(quarterly_quality["manifest_sha256"]),
        "quarterly quality manifest",
    )
    repository_evidence["quarterly_quality_manifest"] = {
        "path": str(quality_manifest_path),
        "sha256": str(quarterly_quality["manifest_sha256"]),
    }
    for name, link in spec["execution_policies"].items():
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {"path": str(path), "sha256": expected}
    return manifest, audit, manifest_path, audit_path, repository_evidence


def require_diagnostic_unconsumed(experiment_root: Path) -> None:
    """Reject a second read of this candidate's historical returns."""

    marker = experiment_root / CONSUMPTION_FILENAME
    if marker.exists():
        raise IntradayMarketAmountProfileSynchronizationError(
            "amount-profile historical diagnostic is already consumed: " f"{marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise IntradayMarketAmountProfileSynchronizationError(
                f"amount-profile historical diagnostic already exists: {path}"
            )


def attach_ranked_candidate(
    market: pd.DataFrame,
    candidate: pd.DataFrame,
    diagnostic_spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Use the accepted point-in-time ranking path with the bound field."""

    prior_factor_name = foundation.FACTOR_NAME
    foundation.FACTOR_NAME = FACTOR_NAME
    try:
        return foundation.attach_ranked_candidate(
            market,
            candidate,
            diagnostic_spec,
        )
    finally:
        foundation.FACTOR_NAME = prior_factor_name


def run_diagnostic(args: argparse.Namespace) -> Path:
    """Consume the only authorized 2019-2025 three-session diagnostic."""

    data_root = Path(args.data_root).expanduser().resolve()
    provider_uri = Path(args.provider_uri).expanduser().resolve()
    fundamentals_path = Path(args.fundamentals).expanduser().resolve()
    experiment_root = Path(args.experiment_root).expanduser().resolve()
    experiment_root.mkdir(parents=True, exist_ok=True)
    require_diagnostic_unconsumed(experiment_root)
    spec = load_diagnostic_preregistration()
    (
        manifest,
        no_return_audit,
        manifest_path,
        audit_path,
        repository_evidence,
    ) = validate_diagnostic_source_chain(spec, data_root)
    verification = verify_snapshot_files(
        manifest,
        manifest_path,
        int(args.verification_workers),
    )
    candidate = load_candidate_frame(manifest_path, manifest)
    holding = spec["holding_protocol"]
    start = str(holding["development_start"])
    end = str(holding["development_end"])
    if candidate["trade_date"].min() < pd.Timestamp(start) or candidate[
        "trade_date"
    ].max() > pd.Timestamp(end):
        raise IntradayMarketAmountProfileSynchronizationError(
            "candidate feature dates escape the frozen diagnostic window"
        )
    print("loading accepted daily execution and quality context", flush=True)
    price_basis = research.research_price_basis_metadata(provider_uri)
    fundamentals = research.load_fundamentals(fundamentals_path)
    market = research.load_market_execution_data(
        provider_uri,
        start,
        end,
        int(args.batch_size),
    )
    market = research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=int(spec["quarterly_quality"]["maximum_age_days"]),
    )
    del fundamentals
    gc.collect()
    quality_counts = {
        "fundamental_eligible_rows_before_listing_gate": int(
            market["fundamental_quality_eligible"].fillna(False).sum()
        ),
        "eligible_rows_after_listing_gate": int(
            market["quality_eligible"].fillna(False).sum()
        ),
        "fundamental_rows_excluded_by_listing_gate": int(
            (
                market["fundamental_quality_eligible"].fillna(False)
                & ~market["listing_seasoning_eligible"].fillna(False)
            ).sum()
        ),
    }
    market_rows = int(len(market))
    market_start = market["datetime"].min().date().isoformat()
    market_end = market["datetime"].max().date().isoformat()
    ranked, coverage = attach_ranked_candidate(market, candidate, spec)
    del market, candidate
    gc.collect()

    execution_policy = research.load_prospective_execution_policy()
    research.require_prospective_execution_policy_compatibility(
        execution_policy,
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    pilot_policy = research.load_pilot_execution_policy()
    marker_path = experiment_root / CONSUMPTION_FILENAME
    marker = {
        "kind": (
            "a_share_tushare_intraday_market_amount_profile_synchronization_"
            "historical_consumption"
        ),
        "status": "historical_forward_return_read_started",
        "started_at": research._timestamp(),
        "diagnostic_preregistration_path": str(
            DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()
        ),
        "diagnostic_preregistration_sha256": DIAGNOSTIC_PREREGISTRATION_SHA256,
        "candidate_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "no_return_audit_sha256": NO_RETURN_AUDIT_SHA256,
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
    }
    research._atomic_write_text(
        marker_path,
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    print(
        "no-return gates reproduced; beginning the single authorized "
        "forward-return read",
        flush=True,
    )
    forward_returns = research.forward_factor_return_frame(
        ranked,
        int(holding["holding_period_trading_days"]),
    )
    summaries = research.summarize_factor_diagnostics(
        forward_returns,
        [FACTOR_NAME],
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    del forward_returns
    gc.collect()
    summary = (
        summaries[0]
        if summaries
        else research.unavailable_factor_diagnostic_summary(
            FACTOR_NAME,
            int(holding["holding_period_trading_days"]),
        )
    )
    print("simulating normalized and CNY 200,000 execution policies", flush=True)
    summary["execution_aware_topk"] = research.simulate_prospective_execution_topk(
        ranked,
        FACTOR_NAME,
        policy=execution_policy,
    )
    summary["pilot_execution_topk"] = research.simulate_pilot_execution_topk(
        ranked,
        FACTOR_NAME,
        execution_policy=execution_policy,
        pilot_policy=pilot_policy,
    )
    del ranked
    gc.collect()
    run_id = research._timestamp()
    diagnostic = {
        "run_id": run_id,
        "status": "completed",
        "purpose": DIAGNOSTIC_PURPOSE,
        "factor_catalog": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "strategy_timing": {
            "universe": holding["universe"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "listing_gate_applied_before_cross_sectional_ranking": True,
            "holding_period_trading_days": int(holding["holding_period_trading_days"]),
            "rebalancing": "non_overlapping_every_holding_period",
            "signal_time": (
                "full-session market amount-profile synchronization known "
                "after signal-session close"
            ),
            "same_session_trade_allowed": False,
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "diagnostic_topk": int(holding["topk"]),
            "open_cost": float(holding["open_cost"]),
            "close_cost": float(holding["close_cost"]),
            "parameters_read_from_preregistration": True,
        },
        "quality_gate": {
            "source": str(fundamentals_path),
            "sha256": research.file_sha256(fundamentals_path),
            "effective_date": (
                "strictly next local trading session after announcement_date"
            ),
            "quality_state_semantics": spec["quarterly_quality"][
                "quality_state_semantics"
            ],
            "max_quality_age_days": int(spec["quarterly_quality"]["maximum_age_days"]),
            **quality_counts,
        },
        "minute_factor": {
            "provider": "tushare",
            "frequency": "1m",
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": spec["factor"]["formula"],
            "candidate_manifest": {
                "path": str(manifest_path),
                "sha256": CANDIDATE_MANIFEST_SHA256,
                "dataset_sha256": manifest["dataset_sha256"],
                "verification": verification,
            },
            "no_return_audit": {
                "path": str(audit_path),
                "sha256": NO_RETURN_AUDIT_SHA256,
                "status": no_return_audit["status"],
            },
            "coverage": coverage,
            "source_fields_read_for_factor": list(RAW_COLUMNS),
            "source_amount_read_for_factor": True,
            "source_price_or_volume_read_for_factor": False,
            "standalone_09_30_row_excluded": True,
            "continuous_session_profile_positions": PROFILE_POSITIONS,
            "leave_one_out_equal_weight_market_profile": True,
            "daily_prices_substituted_into_minute_rows": False,
            "forward_return_fields_stored_in_feature_source": False,
            "selection_or_promotion_allowed": False,
        },
        "data": {
            "provider_uri": str(provider_uri),
            **price_basis,
            "calendar_start": market_start,
            "calendar_end": market_end,
            "development_start": start,
            "development_end": end,
            "market_rows": market_rows,
            "eligible_rows": quality_counts["eligible_rows_after_listing_gate"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "test_period_used_for_factor_design": False,
        },
        "prospective_execution_policy": {
            "path": str(research.DEFAULT_PROSPECTIVE_EXECUTION_POLICY),
            "sha256": research.PROSPECTIVE_EXECUTION_POLICY_SHA256,
            "frozen_at": execution_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
        },
        "pilot_execution_policy": {
            "path": str(research.DEFAULT_PILOT_EXECUTION_POLICY),
            "sha256": research.PILOT_EXECUTION_POLICY_SHA256,
            "frozen_at": pilot_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
            "initial_capital_cny": 200000.0,
            "buy_lot_size_shares": 100,
            "primary_slippage_rate_each_side": 0.001,
            "maximum_daily_amount_participation": 0.01,
        },
        "preregistration": {
            "path": str(DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()),
            "sha256": DIAGNOSTIC_PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
            "factor_returns_observed_before_registration": False,
            "single_use_marker": str(marker_path),
        },
        "repository_evidence": repository_evidence,
        "ranking_by_development_rank_ic": [summary],
        "post_diagnostic_decision": spec["post_diagnostic_decision"],
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
        "limitations": [
            "This is an exploratory 2019-2025 diagnostic, not a pristine "
            "holdout and not investment advice.",
            "Only the higher direction frozen before this return read was evaluated.",
            "A failure may not be inverted, reformulated, re-windowed, "
            "thresholded, subsetted, reweighted, or retested on this history.",
            "A pass admits only one factor and cannot satisfy the two-factor "
            "aggregation minimum by itself.",
            "The source universe inherits the repository's current-listing "
            "definition and is not survivorship-free.",
            "Daily execution bars cannot reconstruct exact queue priority, "
            "partial fills, or realized market impact.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_diagnostic.json"
    research._atomic_write_text(
        destination,
        json.dumps(
            diagnostic,
            ensure_ascii=False,
            indent=2,
            default=research._json_default,
        )
        + "\n",
    )
    marker.update(
        {
            "status": "historical_diagnostic_completed",
            "completed_at": research._timestamp(),
            "diagnostic_path": str(destination),
            "diagnostic_sha256": research.file_sha256(destination),
        }
    )
    research._atomic_write_text(
        marker_path,
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser(
        "build",
        help="Build the external candidate snapshot",
    )
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--workers", type=int, default=4)
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run ordered coverage/capacity and uniqueness without returns",
    )
    audit_parser.add_argument("--data-root", type=Path, required=True)
    audit_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    audit_parser.add_argument("--workers", type=int, default=8)
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Consume the single preregistered three-session diagnostic",
    )
    diagnose_parser.add_argument("--data-root", type=Path, required=True)
    diagnose_parser.add_argument(
        "--provider-uri",
        type=Path,
        default=REPO_ROOT / "data/qlib/cn_a_share",
    )
    diagnose_parser.add_argument(
        "--fundamentals",
        type=Path,
        default=(REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"),
    )
    diagnose_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    diagnose_parser.add_argument("--batch-size", type=int, default=250)
    diagnose_parser.add_argument("--verification-workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
    elif args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
    else:
        path = run_diagnostic(args)
    print(json.dumps({"status": "ok", "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
