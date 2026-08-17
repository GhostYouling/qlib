#!/usr/bin/env python3
"""Build and audit the one no-return feature mechanism for Campaign008.

The exact formula is frozen before this module may open an external minute
partition. It reads only datetime, symbol, provider, close, and volume.
Coverage/capacity is evaluated before any comparison values. No daily price,
forward return, provider credential, or provider request enters this module.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign007_features as prior  # noqa: E402


executor = prior.base
engine = prior.engine
foundation = prior.foundation
research = prior.research
candidate49 = prior.candidate49
market = prior.market
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_008_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_008"
    / "no_return"
)
MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_008_mechanism_overlap_audit.json"
)
MECHANISM_AUDIT_SHA256 = (
    "259d3055898961287bea478946fa1653deade16b9b9927da9fc8b7a5d3d87246"
)

# Bind these in sequence only after each immutable artifact exists.
PROTOCOL_SHA256 = (
    "1c209a1611d822531efe178793c80e5a8f68f5752ae5a0dfa890585e62dfcf56"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "09d4f82ec350ff8c16106c7ebc007d791f626589d33cd3e09cd4d0725893aaab"
)
SNAPSHOT_DATASET_SHA256 = (
    "825b9a68890a6975b0866a99ce5b798968b82d80f226c8fdadbffba3472b40dc"
)
NO_RETURN_AUDIT_SHA256 = (
    "af4013e0d439174ab6bb0c08d26bdf4bed71b6bd668eea25c834ec5ff0f5e937"
)

SOURCE_RUN_ID = market.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_walkforward_campaign008_feature_library_v1"
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "volume")
BASE_COLUMNS = ("trade_date", "symbol")
FACTOR_NAME = "intraday_post_shock_share_volume_replenishment_236p"
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}
FACTOR_FORMULA = (
    "PearsonCorr(abs(log(close_t/close_t-1)), "
    "log(volume_t+1/volume_t)) over retained within-half "
    "one-minute post-shock response pairs"
)
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_SYMBOLS = 5_396
MAXIMUM_PAIRS = 236
MINIMUM_RETAINED_PAIRS = 120
ENDPOINT_TOLERANCE = 1e-12

C7_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign007_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign007_feature_library_v1/snapshot_manifest.json"
)
C7_SNAPSHOT_SHA256 = (
    "d76fee2c03a38673eb4ce3a20ad0dba35f509c67a86201e50a410cadbdde6033"
)
C7_DATASET_SHA256 = (
    "3eeee40583146024e7b9b8e867daa2e17043c6dc5a72ce3d3e8d525602bb8931"
)
C7_FACTOR_NAMES = ("intraday_share_volume_transaction_price_coupling_238p",)
C7_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C7_FACTOR_NAMES[0],
    f"{C7_FACTOR_NAMES[0]}_eligible",
)


class Campaign008FeatureError(RuntimeError):
    """Fail-closed Campaign008 feature or no-return audit error."""


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise Campaign008FeatureError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, "
            f"got {observed}"
        )


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign008_feature_library"
        / OUTPUT_RUN_ID
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


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign008 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign008FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign008 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign008 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign008 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign008_no_return_preregistration",
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
    mechanism = (spec.get("source_chain") or {}).get(
        "mechanism_overlap_audit"
    ) or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign008_candidate_or_comparison_values_or_returns"
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidates[0].get("maximum_possible_pairs") == MAXIMUM_PAIRS
        and candidates[0].get("minimum_retained_pairs")
        == MINIMUM_RETAINED_PAIRS
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts")
        == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 31
        and str(comparisons[-1].get("name") or "") == C7_FACTOR_NAMES[0]
        and boundary.get("minute_close_field_read_before_admissibility") is True
        and boundary.get("minute_amount_field_read_before_admissibility") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign008FeatureError(
            "Campaign008 no-return protocol semantics changed"
        )
    return spec


def compute_factor_values(
    *,
    closes: np.ndarray,
    volumes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen post-shock share-volume replenishment."""

    if (
        closes.ndim != 2
        or closes.shape[1] != 240
        or volumes.shape != closes.shape
    ):
        raise Campaign008FeatureError(
            "Campaign008 aligned array shapes are invalid"
        )
    close_valid = (
        np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    )
    volume_valid = (
        np.isfinite(volumes).all(axis=1) & (volumes >= 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        log_closes = np.log(closes)
    shocks = np.abs(
        np.concatenate(
            [
                log_closes[:, 1:119] - log_closes[:, 0:118],
                log_closes[:, 121:239] - log_closes[:, 120:238],
            ],
            axis=1,
        )
    )
    current_volumes = np.concatenate(
        [volumes[:, 1:119], volumes[:, 121:239]],
        axis=1,
    )
    next_volumes = np.concatenate(
        [volumes[:, 2:120], volumes[:, 122:240]],
        axis=1,
    )
    one_sided_zero_pairs = (current_volumes == 0.0) != (next_volumes == 0.0)
    one_sided_zero = one_sided_zero_pairs.any(axis=1)
    retained = (current_volumes > 0.0) & (next_volumes > 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        volume_growth = np.log(next_volumes) - np.log(current_volumes)
    pair_count = retained.sum(axis=1)
    x = np.where(retained, shocks, 0.0)
    y = np.where(retained, volume_growth, 0.0)
    n = pair_count.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        sum_x = x.sum(axis=1)
        sum_y = y.sum(axis=1)
        sum_x2 = np.square(x).sum(axis=1)
        sum_y2 = np.square(y).sum(axis=1)
        sum_xy = (x * y).sum(axis=1)
        centered_x2 = sum_x2 - np.square(sum_x) / n
        centered_y2 = sum_y2 - np.square(sum_y) / n
        centered_xy = sum_xy - sum_x * sum_y / n
        values = centered_xy / np.sqrt(centered_x2 * centered_y2)
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = (
        close_valid
        & volume_valid
        & ~one_sided_zero
        & (pair_count >= MINIMUM_RETAINED_PAIRS)
        & (centered_x2 > 0.0)
        & (centered_y2 > 0.0)
        & finite
        & in_range
    )
    valid_inputs = close_valid & volume_valid
    sufficiently_observed = (
        valid_inputs
        & ~one_sided_zero
        & (pair_count >= MINIMUM_RETAINED_PAIRS)
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~close_valid).sum()),
        "invalid_required_volume_rows": int((close_valid & ~volume_valid).sum()),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__one_sided_zero_response_rows": int(
            (valid_inputs & one_sided_zero).sum()
        ),
        f"{FACTOR_NAME}__fewer_than_120_pairs_rows": int(
            (
                valid_inputs
                & ~one_sided_zero
                & (pair_count < MINIMUM_RETAINED_PAIRS)
            ).sum()
        ),
        f"{FACTOR_NAME}__constant_absolute_shock_rows": int(
            (sufficiently_observed & (centered_x2 <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__constant_volume_growth_rows": int(
            (sufficiently_observed & (centered_y2 <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                sufficiently_observed
                & (centered_x2 > 0.0)
                & (centered_y2 > 0.0)
                & (~finite | ~in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute the frozen feature."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign008FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign008FeatureError(
            f"unexpected joint-base columns for {symbol}: "
            f"{tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"],
        errors="coerce",
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign008FeatureError(
            f"joint-base identity changed for {symbol}"
        )
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["volume"] = pd.to_numeric(work["volume"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign008FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    source_counts = work.groupby(
        "trade_date",
        sort=True,
        observed=True,
    ).size()
    if not source_counts.eq(241).all():
        raise Campaign008FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby(
        "trade_date",
        sort=True,
        observed=True,
    )["minute_code"].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign008FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(
        pd.Index(source_counts.index)
    ).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(
        expected_dates
    ):
        raise Campaign008FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close", "volume"],
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
        raise Campaign008FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 240)
    volumes = continuous["volume"].to_numpy(dtype=float).reshape(-1, 240)
    values, eligible, quality = compute_factor_values(
        closes=closes,
        volumes=volumes,
    )
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "tushare",
                FACTOR_NAME: values[FACTOR_NAME],
                f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
            }
        ).loc[:, OUTPUT_COLUMNS],
        quality,
    )


def _configure_engine() -> None:
    """Point reusable checkpoint mechanics at the Campaign008 contract."""

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
    expected_kinds = (
        {"a_share_three_day_walkforward_campaign008_feature_snapshot"}
        if require_fingerprint_constants
        else {
            "a_share_three_day_walkforward_campaign006_feature_snapshot",
            "a_share_three_day_walkforward_campaign008_feature_snapshot",
        }
    )
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") in expected_kinds
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
        and isinstance(eligible.get(FACTOR_NAME), int)
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_volume_read") is True
        and (
            manifest.get("source_close_read") is True
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, True}
        )
        and (
            manifest.get("source_amount_read") is False
            if require_fingerprint_constants
            else manifest.get("source_amount_read") in {None, False}
        )
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign008FeatureError("Campaign008 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign008FeatureError(
            "Campaign008 snapshot fingerprint constants are not bound"
        )


def _bind_executor() -> None:
    """Bind the frozen Campaign006 checkpoint executor to Campaign008 state."""

    executor.DEFAULT_PROTOCOL = DEFAULT_PROTOCOL
    executor.DEFAULT_DATA_ROOT = DEFAULT_DATA_ROOT
    executor.DEFAULT_EXPERIMENT_ROOT = DEFAULT_EXPERIMENT_ROOT
    executor.MECHANISM_AUDIT = MECHANISM_AUDIT
    executor.MECHANISM_AUDIT_SHA256 = MECHANISM_AUDIT_SHA256
    executor.PROTOCOL_SHA256 = PROTOCOL_SHA256
    executor.SNAPSHOT_MANIFEST_SHA256 = SNAPSHOT_MANIFEST_SHA256
    executor.SNAPSHOT_DATASET_SHA256 = SNAPSHOT_DATASET_SHA256
    executor.NO_RETURN_AUDIT_SHA256 = NO_RETURN_AUDIT_SHA256
    executor.OUTPUT_RUN_ID = OUTPUT_RUN_ID
    executor.RAW_COLUMNS = RAW_COLUMNS
    executor.BASE_COLUMNS = BASE_COLUMNS
    executor.FACTOR_NAME = FACTOR_NAME
    executor.FACTOR_NAMES = FACTOR_NAMES
    executor.FACTOR_DIRECTIONS = FACTOR_DIRECTIONS
    executor.FACTOR_RANGES = FACTOR_RANGES
    executor.FACTOR_FORMULA = FACTOR_FORMULA
    executor.FACTOR_FORMULAS = FACTOR_FORMULAS
    executor.OUTPUT_COLUMNS = OUTPUT_COLUMNS
    executor.output_root = output_root
    executor.empty_output_frame = empty_output_frame
    executor.load_protocol = load_protocol
    executor.compute_partition_frame = compute_partition_frame
    executor._configure_engine = _configure_engine
    executor._validate_snapshot_manifest = _validate_snapshot_manifest
    _configure_engine()


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build the Campaign008 factor without comparisons or returns."""

    _bind_executor()
    original_atomic_write_json = foundation.atomic_write_json

    def campaign008_atomic_write_json(
        value: dict[str, Any],
        path: Path,
    ) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign006_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value["kind"] = (
                "a_share_three_day_walkforward_campaign008_feature_snapshot"
            )
            value["source_close_read"] = True
            value["source_amount_read"] = False
            value["protocol_evidence"] = {
                "campaign008_mechanism_overlap_audit_sha256": (
                    MECHANISM_AUDIT_SHA256
                ),
                "campaign008_no_return_preregistration_sha256": (
                    PROTOCOL_SHA256
                ),
                "candidate49_no_return_protocol_sha256": (
                    candidate49.PREREGISTRATION_SHA256
                ),
            }
        original_atomic_write_json(value, path)

    foundation.atomic_write_json = campaign008_atomic_write_json
    try:
        return executor.build_snapshot(data_root=data_root, workers=workers)
    finally:
        foundation.atomic_write_json = original_atomic_write_json


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, Any]:
    _bind_executor()
    return executor.verify_snapshot_files(manifest, manifest_path, workers)


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before all 31 frozen uniqueness comparisons."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign008FeatureError(
            "bind the Campaign008 snapshot fingerprints before audit"
        )
    _bind_executor()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        SNAPSHOT_MANIFEST_SHA256,
        "Campaign008 snapshot manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign008_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign008FeatureError(
                "existing Campaign008 audit is ambiguous or not bound"
            )
        _require_file(
            existing[0],
            NO_RETURN_AUDIT_SHA256,
            "Campaign008 audit",
        )
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign008 no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate = engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
        )
        c4_manifest, c4_verification = executor._verify_prior_snapshot(
            path=executor.C4_SNAPSHOT_PATH,
            manifest_sha256=executor.C4_SNAPSHOT_SHA256,
            dataset_sha256=executor.C4_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign004_feature_snapshot",
            factor_names=executor.C4_FACTOR_NAMES,
            output_columns=executor.C4_OUTPUT_COLUMNS,
            workers=workers,
        )
        c5_manifest, c5_verification = executor._verify_prior_snapshot(
            path=executor.C5_SNAPSHOT_PATH,
            manifest_sha256=executor.C5_SNAPSHOT_SHA256,
            dataset_sha256=executor.C5_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign005_feature_snapshot",
            factor_names=executor.C5_FACTOR_NAMES,
            output_columns=executor.C5_OUTPUT_COLUMNS,
            workers=workers,
        )
        c6_manifest, c6_verification = executor._verify_prior_snapshot(
            path=prior.C6_SNAPSHOT_PATH,
            manifest_sha256=prior.C6_SNAPSHOT_SHA256,
            dataset_sha256=prior.C6_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign006_feature_snapshot",
            factor_names=prior.C6_FACTOR_NAMES,
            output_columns=prior.C6_OUTPUT_COLUMNS,
            workers=workers,
        )
        c7_manifest, c7_verification = executor._verify_prior_snapshot(
            path=C7_SNAPSHOT_PATH,
            manifest_sha256=C7_SNAPSHOT_SHA256,
            dataset_sha256=C7_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign007_feature_snapshot",
            factor_names=C7_FACTOR_NAMES,
            output_columns=C7_OUTPUT_COLUMNS,
            workers=workers,
        )
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        keys, values = engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        comparisons, frozen_verifications = (
            engine._uniqueness_against_frozen_library(
                candidate_keys=keys,
                candidate_values=values,
                chain=chain,
                candidate49_manifest_path=candidate49_manifest_path,
                candidate49_manifest=candidate49_manifest,
                gate=gate,
                workers=workers,
                frozen_verifications=None,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c4_manifest,
                factors=executor.C4_FACTOR_NAMES,
                gate=gate,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c5_manifest,
                factors=(executor.C5_COMPARISON_FACTOR,),
                gate=gate,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c6_manifest,
                factors=prior.C6_FACTOR_NAMES,
                gate=gate,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c7_manifest,
                factors=C7_FACTOR_NAMES,
                gate=gate,
            )
        )
        observed = [
            item["absolute_median_daily_rank_correlation"]
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            len(comparisons) == 31
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "pre_campaign004_comparison_count": 25,
            "campaign004_terminal_comparison_count": 3,
            "campaign005_terminal_comparison_count": 1,
            "campaign006_terminal_comparison_count": 1,
            "campaign007_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,
            "campaign004_snapshot_file_verification": c4_verification,
            "campaign005_snapshot_file_verification": c5_verification,
            "campaign006_snapshot_file_verification": c6_verification,
            "campaign007_snapshot_file_verification": c7_verification,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_comparisons_passed": passed,
        }
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    run_id = f"{research._timestamp()}_campaign008_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign008_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
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
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign008 walk-forward catalog "
            "before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_close_read": True,
        "minute_amount_read": False,
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
    manifest_path = output_root(
        data_root.expanduser().resolve()
    ) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign008_no_return_audit.json"
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
        "minute_close_read_by_status": True,
        "minute_amount_read_by_status": False,
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = foundation.file_digest(
            manifest_path
        )
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = foundation.file_digest(
            audits[-1]
        )
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Build and no-return audit Campaign008 feature mechanism."
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
