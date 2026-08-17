#!/usr/bin/env python3
"""Build and audit the three no-return feature mechanisms for Campaign005.

The exact formulas are frozen in the Campaign005 mechanism-overlap record
before this module may open the immutable joint-clean minute snapshot.  The
builder reads only datetime, symbol, provider, close, and amount.  The ordered
audit applies coverage/capacity before loading any comparison value, then
compares each passer with the 25 pre-Campaign004 minute factors, all three
terminal Campaign004 factors, and earlier Campaign005 passers.

This module deliberately reuses the hash-bound partition/checkpoint and
comparison machinery from Campaign004.  It replaces the campaign-specific
configuration in memory only; the frozen Campaign004 source file is never
modified.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign004_features as engine  # noqa: E402


foundation = engine.foundation
research = engine.research
candidate49 = engine.candidate49
market = engine.market
comparison_engine = engine.comparison_engine
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_005_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_005"
    / "no_return"
)
MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_005_mechanism_overlap_audit.json"
)
MECHANISM_AUDIT_SHA256 = (
    "c378541156f8e68a2d73bafe44f99f7d1b3fc7ca06c1cf72c093d07a93f7907e"
)

# Bound only after the corresponding artifact exists.  Formula-only unit tests
# are allowed while these remain empty because they read no historical value.
PROTOCOL_SHA256 = (
    "01b0c48e2a3e1b0741dee62d4e9d4858e202410ea266a00faa1b5d5ccc21ffa3"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "7f48bd252d381f85deb416ed282b6f62aacee0ca492c37c99fdb901d2e241675"
)
SNAPSHOT_DATASET_SHA256 = (
    "5c7f9e7e534cc4e4678c7ea746c69f5809dcc6415d9a652b93ff63899413fd75"
)
NO_RETURN_AUDIT_SHA256 = "7a6ae6e1667aeb7a7060550c722431f0e8b88ff6e18bc00c2f3478dc2646b2b1"

SOURCE_RUN_ID = market.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_walkforward_campaign005_feature_library_v1"
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
BASE_COLUMNS = ("trade_date", "symbol")
FACTOR_NAMES = (
    "intraday_zero_return_amount_intensity_238m",
    "intraday_lunch_repricing_persistence_119m",
    "intraday_directional_price_impact_asymmetry_238m",
)
ZERO_RETURN_FACTOR, LUNCH_FACTOR, IMPACT_FACTOR = FACTOR_NAMES
FACTOR_DIRECTIONS = {name: "higher" for name in FACTOR_NAMES}
FACTOR_RANGES = {
    ZERO_RETURN_FACTOR: (-math.inf, math.log(238)),
    LUNCH_FACTOR: (-1.0, 1.0),
    IMPACT_FACTOR: (-1.0, 1.0),
}
FACTOR_FORMULAS = {
    ZERO_RETURN_FACTOR: (
        "log((sum(A_t for r_t=0)/N_zero) / "
        "(sum(A_t for all 238 within-half transitions)/238))"
    ),
    LUNCH_FACTOR: (
        "sign(log(close_13:01/close_11:30)) * "
        "log(close_15:00/close_13:01) / "
        "sum(abs(adjacent log-close returns from 13:01 through 15:00))"
    ),
    IMPACT_FACTOR: (
        "(I_up-I_down)/(I_up+I_down), where "
        "I_up=sum(r_t for r_t>0)/sum(A_t for r_t>0) and "
        "I_down=sum(-r_t for r_t<0)/sum(A_t for r_t<0) over 238 "
        "within-half destination-amount pairs"
    ),
}
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    ZERO_RETURN_FACTOR,
    f"{ZERO_RETURN_FACTOR}_eligible",
    LUNCH_FACTOR,
    f"{LUNCH_FACTOR}_eligible",
    IMPACT_FACTOR,
    f"{IMPACT_FACTOR}_eligible",
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_SYMBOLS = 5_396
TRANSITION_COUNT = 238
ENDPOINT_TOLERANCE = 1e-12
ZERO_RETURN_UPPER = math.log(TRANSITION_COUNT)

C4_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign004_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign004_feature_library_v1/snapshot_manifest.json"
)
C4_SNAPSHOT_SHA256 = (
    "8eefc381d006997f1dcd95edcd9be4db8485e0c4954d6166d94f1981ae3b57fe"
)
C4_DATASET_SHA256 = (
    "1359e755e669c7b949b26b2086d1c1328ec0cdf53b45ce7e67d117a274c7fc8a"
)
C4_FACTOR_NAMES = (
    "intraday_market_neutral_late_residual_drift_238m",
    "intraday_negative_return_absorption_rate_236p",
    "intraday_signed_path_efficiency_239m",
)
C4_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C4_FACTOR_NAMES[0],
    f"{C4_FACTOR_NAMES[0]}_eligible",
    C4_FACTOR_NAMES[1],
    f"{C4_FACTOR_NAMES[1]}_eligible",
    C4_FACTOR_NAMES[2],
    f"{C4_FACTOR_NAMES[2]}_eligible",
)


class Campaign005FeatureError(RuntimeError):
    """Fail-closed Campaign005 feature or no-return audit error."""


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise Campaign005FeatureError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign005_feature_library"
        / OUTPUT_RUN_ID
    )


def empty_output_frame() -> pd.DataFrame:
    columns: dict[str, pd.Series] = {
        "trade_date": pd.Series(dtype="datetime64[ns]"),
        "symbol": pd.Series(dtype="string"),
        "provider": pd.Series(dtype="string"),
    }
    for name in FACTOR_NAMES:
        columns[name] = pd.Series(dtype="float64")
        columns[f"{name}_eligible"] = pd.Series(dtype="bool")
    return pd.DataFrame(columns).loc[:, OUTPUT_COLUMNS]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign005 historical value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign005FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign005 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign005 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign005 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign005_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
    names = tuple(str(item.get("name") or "") for item in candidates)
    formulas = {
        str(item.get("name") or ""): str(item.get("formula") or "")
        for item in candidates
    }
    directions = {
        str(item.get("name") or ""): str(item.get("direction") or "")
        for item in candidates
    }
    audit = spec.get("ordered_no_return_gates") or {}
    coverage = audit.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = audit.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get("mechanism_overlap_audit") or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign005_candidate_or_comparison_values_or_returns"
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and all(
            tuple(item.get("source_fields_allowed") or ()) == RAW_COLUMNS
            for item in candidates
        )
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 28
        and [str(item.get("name") or "") for item in comparisons[-3:]]
        == list(C4_FACTOR_NAMES)
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign005FeatureError("Campaign005 no-return protocol semantics changed")
    return spec


def _canonicalize_unit_interval(
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    adjusted = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    in_range = (adjusted >= -1.0) & (adjusted <= 1.0)
    return adjusted, canonicalized, in_range


def compute_factor_values(
    *,
    closes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the three frozen Campaign005 mechanisms from aligned arrays."""

    if (
        closes.ndim != 2
        or closes.shape[1] != 240
        or amounts.shape != closes.shape
    ):
        raise Campaign005FeatureError("Campaign005 aligned array shapes are invalid")
    close_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    amount_valid = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_closes = np.log(closes)
    morning_returns = log_closes[:, 1:120] - log_closes[:, :119]
    afternoon_returns = log_closes[:, 121:240] - log_closes[:, 120:239]
    within_returns = np.concatenate(
        [morning_returns, afternoon_returns],
        axis=1,
    )
    destination_amounts = np.concatenate(
        [amounts[:, 1:120], amounts[:, 121:240]],
        axis=1,
    )
    returns_valid = np.isfinite(within_returns).all(axis=1)

    zero_mask = np.concatenate(
        [
            closes[:, 1:120] == closes[:, :119],
            closes[:, 121:240] == closes[:, 120:239],
        ],
        axis=1,
    )
    zero_count = zero_mask.sum(axis=1)
    zero_amount = np.sum(np.where(zero_mask, destination_amounts, 0.0), axis=1)
    total_transition_amount = np.sum(destination_amounts, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        zero_ratio = (
            (zero_amount / zero_count)
            / (total_transition_amount / TRANSITION_COUNT)
        )
        zero_values = np.log(zero_ratio)
    zero_high_near = (
        (zero_values > ZERO_RETURN_UPPER)
        & (zero_values <= ZERO_RETURN_UPPER + ENDPOINT_TOLERANCE)
    )
    zero_values = np.where(zero_high_near, ZERO_RETURN_UPPER, zero_values)
    zero_finite = np.isfinite(zero_values)
    zero_in_range = zero_values <= ZERO_RETURN_UPPER
    zero_eligible = (
        close_valid
        & amount_valid
        & returns_valid
        & (zero_count > 0)
        & (zero_amount > 0.0)
        & (total_transition_amount > 0.0)
        & zero_finite
        & zero_in_range
    )

    lunch_return = log_closes[:, 120] - log_closes[:, 119]
    afternoon_displacement = log_closes[:, 239] - log_closes[:, 120]
    afternoon_variation = np.sum(np.abs(afternoon_returns), axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        lunch_values = (
            np.sign(lunch_return)
            * afternoon_displacement
            / afternoon_variation
        )
    lunch_values, lunch_canonicalized, lunch_in_range = (
        _canonicalize_unit_interval(lunch_values)
    )
    lunch_finite = np.isfinite(lunch_values)
    lunch_eligible = (
        close_valid
        & np.isfinite(lunch_return)
        & (lunch_return != 0.0)
        & (afternoon_variation > 0.0)
        & lunch_finite
        & lunch_in_range
    )

    positive = within_returns > 0.0
    negative = within_returns < 0.0
    up_amount = np.sum(np.where(positive, destination_amounts, 0.0), axis=1)
    down_amount = np.sum(np.where(negative, destination_amounts, 0.0), axis=1)
    up_magnitude = np.sum(np.where(positive, within_returns, 0.0), axis=1)
    down_magnitude = np.sum(np.where(negative, -within_returns, 0.0), axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        up_impact = up_magnitude / up_amount
        down_impact = down_magnitude / down_amount
        impact_values = (up_impact - down_impact) / (up_impact + down_impact)
    impact_values, impact_canonicalized, impact_in_range = (
        _canonicalize_unit_interval(impact_values)
    )
    impact_finite = np.isfinite(impact_values)
    impact_eligible = (
        close_valid
        & amount_valid
        & returns_valid
        & (up_amount > 0.0)
        & (down_amount > 0.0)
        & (up_magnitude > 0.0)
        & (down_magnitude > 0.0)
        & ((up_impact + down_impact) > 0.0)
        & impact_finite
        & impact_in_range
    )

    values = {
        ZERO_RETURN_FACTOR: np.where(zero_eligible, zero_values, np.nan),
        LUNCH_FACTOR: np.where(lunch_eligible, lunch_values, np.nan),
        IMPACT_FACTOR: np.where(impact_eligible, impact_values, np.nan),
    }
    eligible = {
        ZERO_RETURN_FACTOR: zero_eligible,
        LUNCH_FACTOR: lunch_eligible,
        IMPACT_FACTOR: impact_eligible,
    }
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~close_valid).sum()),
        "invalid_required_amount_rows": int((close_valid & ~amount_valid).sum()),
        f"{ZERO_RETURN_FACTOR}__eligible_rows": int(zero_eligible.sum()),
        f"{ZERO_RETURN_FACTOR}__zero_count_rows": int(
            (close_valid & amount_valid & returns_valid & (zero_count == 0)).sum()
        ),
        f"{ZERO_RETURN_FACTOR}__zero_activity_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & (zero_count > 0)
                & (zero_amount <= 0.0)
            ).sum()
        ),
        f"{ZERO_RETURN_FACTOR}__zero_total_amount_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & (total_transition_amount <= 0.0)
            ).sum()
        ),
        f"{ZERO_RETURN_FACTOR}__upper_endpoint_canonicalized_rows": int(
            (zero_high_near & zero_eligible).sum()
        ),
        f"{ZERO_RETURN_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & (zero_count > 0)
                & (zero_amount > 0.0)
                & (total_transition_amount > 0.0)
                & (~zero_finite | ~zero_in_range)
            ).sum()
        ),
        f"{LUNCH_FACTOR}__eligible_rows": int(lunch_eligible.sum()),
        f"{LUNCH_FACTOR}__zero_lunch_repricing_rows": int(
            (close_valid & (lunch_return == 0.0)).sum()
        ),
        f"{LUNCH_FACTOR}__zero_afternoon_path_rows": int(
            (
                close_valid
                & (lunch_return != 0.0)
                & (afternoon_variation <= 0.0)
            ).sum()
        ),
        f"{LUNCH_FACTOR}__endpoint_canonicalized_rows": int(
            (lunch_canonicalized & lunch_eligible).sum()
        ),
        f"{LUNCH_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & (lunch_return != 0.0)
                & (afternoon_variation > 0.0)
                & (~lunch_finite | ~lunch_in_range)
            ).sum()
        ),
        f"{IMPACT_FACTOR}__eligible_rows": int(impact_eligible.sum()),
        f"{IMPACT_FACTOR}__missing_positive_side_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & ((up_amount <= 0.0) | (up_magnitude <= 0.0))
            ).sum()
        ),
        f"{IMPACT_FACTOR}__missing_negative_side_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & ((down_amount <= 0.0) | (down_magnitude <= 0.0))
            ).sum()
        ),
        f"{IMPACT_FACTOR}__endpoint_canonicalized_rows": int(
            (impact_canonicalized & impact_eligible).sum()
        ),
        f"{IMPACT_FACTOR}__range_or_nonfinite_rows": int(
            (
                close_valid
                & amount_valid
                & returns_valid
                & (up_amount > 0.0)
                & (down_amount > 0.0)
                & (up_magnitude > 0.0)
                & (down_magnitude > 0.0)
                & (~impact_finite | ~impact_in_range)
            ).sum()
        ),
    }
    return values, eligible, quality


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute the frozen feature library."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign005FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, _, _ = market.extract_partition_returns(
        raw.loc[:, market.RAW_COLUMNS],
        base,
        symbol=symbol,
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign005FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"],
        kind="stable",
    )
    if len(continuous) != len(base_work) * 240:
        raise Campaign005FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 240)
    amounts = continuous["amount"].to_numpy(dtype=float).reshape(-1, 240)
    values, eligible, quality = compute_factor_values(
        closes=closes,
        amounts=amounts,
    )
    output: dict[str, Any] = {
        "trade_date": base_work["trade_date"],
        "symbol": symbol.upper(),
        "provider": "tushare",
    }
    for name in FACTOR_NAMES:
        output[name] = values[name]
        output[f"{name}_eligible"] = eligible[name]
    return pd.DataFrame(output).loc[:, OUTPUT_COLUMNS], quality


def _configure_engine() -> None:
    """Point the reusable Campaign004 mechanics at the Campaign005 contract."""

    engine.DEFAULT_PROTOCOL = DEFAULT_PROTOCOL
    engine.DEFAULT_EXPERIMENT_ROOT = DEFAULT_EXPERIMENT_ROOT
    engine.PROTOCOL_SHA256 = PROTOCOL_SHA256
    engine.SNAPSHOT_MANIFEST_SHA256 = SNAPSHOT_MANIFEST_SHA256
    engine.SNAPSHOT_DATASET_SHA256 = SNAPSHOT_DATASET_SHA256
    engine.NO_RETURN_AUDIT_SHA256 = NO_RETURN_AUDIT_SHA256
    engine.OUTPUT_RUN_ID = OUTPUT_RUN_ID
    engine.RAW_COLUMNS = RAW_COLUMNS
    engine.BASE_COLUMNS = BASE_COLUMNS
    engine.FACTOR_NAMES = FACTOR_NAMES
    engine.FACTOR_DIRECTIONS = FACTOR_DIRECTIONS
    engine.FACTOR_RANGES = FACTOR_RANGES
    engine.FACTOR_FORMULAS = FACTOR_FORMULAS
    engine.OUTPUT_COLUMNS = OUTPUT_COLUMNS
    engine.EXPECTED_PARTITIONS = EXPECTED_PARTITIONS
    engine.EXPECTED_ROWS = EXPECTED_ROWS
    engine.EXPECTED_SYMBOLS = EXPECTED_SYMBOLS
    engine.output_root = output_root
    engine.empty_output_frame = empty_output_frame
    engine.load_protocol = load_protocol
    engine.compute_partition_frame = compute_partition_frame


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    eligible = manifest.get("factor_eligible_rows") or {}
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign005_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and manifest.get("raw_manifest_sha256") == market.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == market.JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_names") == list(FACTOR_NAMES)
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and all(isinstance(eligible.get(name), int) for name in FACTOR_NAMES)
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_or_volume_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign005FeatureError("Campaign005 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign005FeatureError(
            "Campaign005 snapshot fingerprint constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all three features without comparison values or returns."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    _configure_engine()
    data_root = data_root.expanduser().resolve()
    load_protocol()
    final_root = output_root(data_root)
    final_manifest = final_root / "snapshot_manifest.json"
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists():
        if not final_manifest.is_file() or not SNAPSHOT_MANIFEST_SHA256:
            raise Campaign005FeatureError(
                "published Campaign005 snapshot exists but is not fingerprint-bound"
            )
        _require_file(
            final_manifest,
            SNAPSHOT_MANIFEST_SHA256,
            "Campaign005 snapshot manifest",
        )
        _validate_snapshot_manifest(
            research.load_json_record(final_manifest),
            require_fingerprint_constants=True,
        )
        return final_manifest
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise Campaign005FeatureError("external data root has less than 10 GiB free")

    candidate49_spec = candidate49.load_preregistration()
    chain = candidate49.validate_external_chain(candidate49_spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    _, joint_by_key, by_symbol = market._partition_maps(raw, joint)
    if len(joint_by_key) != EXPECTED_PARTITIONS or len(by_symbol) != EXPECTED_SYMBOLS:
        raise Campaign005FeatureError("Campaign005 source partition map changed")
    lock_path = data_root / ".a_share_walkforward_campaign005_features.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {EXPECTED_PARTITIONS:,} Campaign005 partitions across "
            f"{EXPECTED_SYMBOLS:,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    engine._process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
                    benchmark=None,
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
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"Campaign005 progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{len(joint_by_key):,} resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != EXPECTED_PARTITIONS:
            raise Campaign005FeatureError(
                "not every source partition produced a Campaign005 checkpoint"
            )
        _require_file(
            Path(raw_manifest_path),
            market.RAW_MANIFEST_SHA256,
            "raw minute manifest",
        )
        _require_file(
            Path(joint_manifest_path),
            market.JOINT_MANIFEST_SHA256,
            "joint-clean manifest",
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = engine._aggregate_quality(all_records)
        factor_eligible_rows = {
            name: int(
                sum(
                    int((record.get("factor_eligible_rows") or {}).get(name, 0))
                    for record in all_records
                )
            )
            for name in FACTOR_NAMES
        }
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        eligible_names_by_date: dict[str, dict[str, int]] = {
            name: {} for name in FACTOR_NAMES
        }
        for key, value in sorted(eligible_dates.items()):
            name, trade_date = key.split("|", 1)
            eligible_names_by_date[name][trade_date] = int(value)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign005_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
            "protocol_sha256": PROTOCOL_SHA256,
            "mechanism_overlap_audit_path": str(MECHANISM_AUDIT.resolve()),
            "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": market.RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": market.JOINT_MANIFEST_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_names": list(FACTOR_NAMES),
            "factor_directions": FACTOR_DIRECTIONS,
            "factor_formulas": FACTOR_FORMULAS,
            "factor_eligible_rows": factor_eligible_rows,
            "eligible_names_by_date": eligible_names_by_date,
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "quality": quality,
            "source_fields_read": list(RAW_COLUMNS),
            "source_open_high_low_or_volume_read": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "prospective_candidate_activation_created": False,
            "resumed_partitions": resumed,
            "protocol_evidence": {
                "campaign005_mechanism_overlap_audit_sha256": (
                    MECHANISM_AUDIT_SHA256
                ),
                "campaign005_no_return_preregistration_sha256": PROTOCOL_SHA256,
                "candidate49_no_return_protocol_sha256": (
                    candidate49.PREREGISTRATION_SHA256
                ),
            },
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
) -> dict[str, Any]:
    _configure_engine()
    return engine.verify_snapshot_files(manifest, manifest_path, workers)


def _verify_campaign004_snapshot(workers: int) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_file(
        C4_SNAPSHOT_PATH,
        C4_SNAPSHOT_SHA256,
        "Campaign004 feature snapshot",
    )
    manifest = research.load_json_record(C4_SNAPSHOT_PATH)
    records = list(manifest.get("files") or [])
    root = (C4_SNAPSHOT_PATH.parent / "partitions").resolve()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign004_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("dataset_sha256") == C4_DATASET_SHA256
        and tuple(manifest.get("factor_names") or ()) == C4_FACTOR_NAMES
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(records) == EXPECTED_PARTITIONS
    ):
        raise Campaign005FeatureError("Campaign004 comparison snapshot changed")

    def verify(record: dict[str, Any]) -> int:
        path = Path(str(record.get("path") or "")).resolve()
        if path.parent.parent != root:
            raise Campaign005FeatureError(
                f"Campaign004 comparison partition escapes root: {path}"
            )
        _require_file(
            path,
            str(record.get("output_byte_sha256") or ""),
            "Campaign004 comparison partition",
        )
        frame = pd.read_parquet(path, columns=list(C4_OUTPUT_COLUMNS))
        if (
            len(frame) != int(record.get("rows", -1))
            or foundation.frame_digest(frame)
            != str(record.get("output_frame_sha256") or "")
        ):
            raise Campaign005FeatureError(
                f"Campaign004 comparison partition frame changed: {path}"
            )
        return len(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        counts = list(pool.map(verify, records))
    if len(counts) != EXPECTED_PARTITIONS or sum(counts) != EXPECTED_ROWS:
        raise Campaign005FeatureError(
            "Campaign004 comparison snapshot aggregate changed"
        )
    return manifest, {
        "path": str(C4_SNAPSHOT_PATH),
        "sha256": C4_SNAPSHOT_SHA256,
        "dataset_sha256": C4_DATASET_SHA256,
        "verified_partitions": len(counts),
        "verified_rows": sum(counts),
        "all_partition_byte_and_frame_hashes_valid": True,
    }


def _add_campaign004_comparisons(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    manifest: dict[str, Any],
    gate: dict[str, Any],
) -> list[dict[str, Any]]:
    values = engine._load_filtered_comparison_values_explicit(
        manifest,
        C4_FACTOR_NAMES,
        candidate_keys,
    )
    return [
        comparison_engine._aligned_comparison_result(
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            comparison_values=values[factor],
            comparison=factor,
            direction="higher",
            gate=gate,
        )
        for factor in C4_FACTOR_NAMES
    ]


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply ordered coverage then all-28-factor uniqueness gates."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign005FeatureError(
            "bind the Campaign005 snapshot fingerprints before audit"
        )
    _configure_engine()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        SNAPSHOT_MANIFEST_SHA256,
        "Campaign005 snapshot manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign005_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign005FeatureError(
                "existing Campaign005 audit is ambiguous or not fingerprint-bound"
            )
        _require_file(existing[0], NO_RETURN_AUDIT_SHA256, "Campaign005 audit")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign005 no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    coverage_records: dict[str, dict[str, Any]] = {}
    quality_frames: dict[str, pd.DataFrame] = {}
    for index, factor in enumerate(FACTOR_NAMES, start=1):
        print(f"coverage gate {index}/3: {factor}", flush=True)
        candidate = engine.load_factor_frame(manifest_path, manifest, factor)
        quality_frame, coverage = engine.coverage_and_capacity(
            candidate,
            eligible_keys,
            spec,
            factor,
        )
        coverage_records[factor] = coverage
        if coverage["gate_passed_before_comparison_values"]:
            quality_frames[factor] = quality_frame
        del candidate
        gc.collect()
    del eligible_keys
    gc.collect()

    chain: tuple[Any, ...] | None = None
    candidate49_manifest_path: Path | None = None
    candidate49_manifest: dict[str, Any] | None = None
    c4_manifest: dict[str, Any] | None = None
    c4_verification: dict[str, Any] | None = None
    if quality_frames:
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
        )
        c4_manifest, c4_verification = _verify_campaign004_snapshot(workers)
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    uniqueness_records: dict[str, dict[str, Any]] = {}
    prior_passers: list[str] = []
    frozen_verifications: dict[str, Any] | None = None
    for factor in FACTOR_NAMES:
        if factor not in quality_frames:
            uniqueness_records[factor] = {
                "comparison_values_loaded_after_coverage_pass": False,
                "comparisons": [],
                "all_required_comparisons_passed": False,
                "failure_reason": "coverage_gate_failed",
            }
            continue
        assert chain is not None
        assert candidate49_manifest_path is not None
        assert candidate49_manifest is not None
        assert c4_manifest is not None
        print(f"uniqueness gate: {factor}", flush=True)
        keys, values = engine._sorted_candidate_arrays(
            quality_frames[factor],
            factor,
        )
        comparisons, verifications = engine._uniqueness_against_frozen_library(
            candidate_keys=keys,
            candidate_values=values,
            chain=chain,
            candidate49_manifest_path=candidate49_manifest_path,
            candidate49_manifest=candidate49_manifest,
            gate=gate,
            workers=workers,
            frozen_verifications=frozen_verifications,
        )
        if frozen_verifications is None:
            frozen_verifications = dict(verifications)
        comparisons.extend(
            _add_campaign004_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c4_manifest,
                gate=gate,
            )
        )
        for prior_factor in prior_passers:
            prior_keys, prior_values = engine._sorted_candidate_arrays(
                quality_frames[prior_factor],
                prior_factor,
            )
            positions = np.searchsorted(prior_keys, keys)
            matched = (positions < len(prior_keys)) & (
                prior_keys[np.minimum(positions, len(prior_keys) - 1)] == keys
            )
            comparison_values = np.full(len(keys), np.nan, dtype=float)
            comparison_values[matched] = prior_values[positions[matched]]
            comparisons.append(
                comparison_engine._aligned_comparison_result(
                    candidate_keys=keys,
                    candidate_values=values,
                    comparison_values=comparison_values,
                    comparison=prior_factor,
                    direction="higher",
                    gate=gate,
                )
            )
        observed = [
            item["absolute_median_daily_rank_correlation"]
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            len(comparisons) == 28 + len(prior_passers)
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness_records[factor] = {
            "comparison_values_loaded_after_coverage_pass": True,
            "pre_campaign004_comparison_count": 25,
            "campaign004_terminal_comparison_count": 3,
            "prior_campaign005_comparison_count": len(prior_passers),
            "prior_snapshot_file_verification": verifications,
            "campaign004_snapshot_file_verification": c4_verification,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_comparisons_passed": passed,
        }
        if passed:
            prior_passers.append(factor)
        del keys, values
        gc.collect()
    admissible = [
        factor
        for factor in FACTOR_NAMES
        if coverage_records[factor]["gate_passed_before_comparison_values"]
        and uniqueness_records[factor]["all_required_comparisons_passed"]
    ]
    run_id = f"{research._timestamp()}_campaign005_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign005_no_return_audit",
        "status": (
            "completed_with_admissible_factors_pending_walkforward_preregistration"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "mechanism_overlap_audit": {
            "path": str(MECHANISM_AUDIT.resolve()),
            "sha256": MECHANISM_AUDIT_SHA256,
        },
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": coverage_records,
        "uniqueness": uniqueness_records,
        "admissible_factor_names": admissible,
        "admissible_factor_count": len(admissible),
        "failed_factor_names": [
            factor for factor in FACTOR_NAMES if factor not in admissible
        ],
        "next_action": (
            "freeze the exact finite single-and-pair Campaign005 trial catalog "
            "before reading 2019-2023 returns"
            if admissible
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "candidate50_prospective_activation_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign005_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "mechanism_overlap_audit_path": str(MECHANISM_AUDIT.resolve()),
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": bool(PROTOCOL_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = foundation.file_digest(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = foundation.file_digest(audits[-1])
        record = research.load_json_record(audits[-1])
        result["admissible_factor_names"] = record.get("admissible_factor_names")
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Build and no-return audit Campaign005 feature mechanisms."
    )
    subparsers = value.add_subparsers(dest="command", required=True)
    for name in ("build", "audit", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
        command.add_argument(
            "--experiment-root",
            default=str(DEFAULT_EXPERIMENT_ROOT),
        )
        if name in {"build", "audit"}:
            command.add_argument("--workers", type=int, default=4)
    return value


def main() -> int:
    args = parser().parse_args()
    data_root = Path(args.data_root)
    experiment_root = Path(args.experiment_root)
    if args.command == "build":
        result: Any = {
            "status": "snapshot_ready",
            "manifest_path": str(
                build_snapshot(data_root=data_root, workers=int(args.workers))
            ),
            "forward_return_fields_read": False,
        }
    elif args.command == "audit":
        result = {
            "status": "no_return_audit_ready",
            "audit_path": str(
                run_no_return_audit(
                    data_root=data_root,
                    experiment_root=experiment_root,
                    workers=int(args.workers),
                )
            ),
            "forward_return_fields_read": False,
        }
    else:
        result = status(data_root, experiment_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
