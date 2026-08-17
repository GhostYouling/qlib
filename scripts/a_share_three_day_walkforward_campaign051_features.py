#!/usr/bin/env python3
"""Build and audit Campaign051 close-range occupancy entropy."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign050_features_v8 as previous_entry
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign050_features_v8 as previous_entry


REPO_ROOT = Path(__file__).resolve().parents[1]
previous = previous_entry.runner
FACTOR_NAME = "intraday_close_range_occupancy_entropy_10b"
FACTOR_FORMULA = (
    "Across the 240 selected closes, let x_i=log(close_i), x_min=min(x), "
    "x_max=max(x), and z_i=(x_i-x_min)/(x_max-x_min). Assign "
    "b_i=min(floor(10*z_i),9), let p_j=count(b_i=j)/240 for j=0..9, and "
    "return -sum_{j:p_j>0}(p_j*log(p_j))/log(10)."
)
MECHANISM_AUDIT_SHA256 = (
    "e5ba77a9678c574822031ddb9b5b54ae32eb56aa412702fee716537c3a6eb939"
)
PROTOCOL_SHA256 = "16636bb5196a362ca55b21696d88bc78b92d7ce10fbf70d252575f47b31c9e40"
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

TERMINAL_LIBRARY_COUNT = 66
COMPARISON_COUNT = 74
INHERITED_COMPARISON_COUNT = 73
INHERITED_COMPARISON_ORDER_SHA256 = (
    "eae7db172c0e54a47f5ea41570cb585dceb6f70cb25ee0088064908aed118a3c"
)
COMPARISON_ORDER_SHA256 = (
    "08639819d24bbb65f1181a31edd788dfc5ac4a6ee56312f600861612d2dec573"
)
SELECTED_BAR_COUNT = 240
BIN_COUNT = 10
ENDPOINT_TOLERANCE = 1e-12
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign051_feature_library_v1"
)
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_no_return_preregistration_v2.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_feature_implementation_freeze_20260801.json"
)
DEFAULT_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_snapshot_publication_binding_20260801.json"
)
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_051/no_return"
)
DEFAULT_DATA_ROOT = previous.DEFAULT_DATA_ROOT
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = previous.BASE_COLUMNS
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
C50_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign050_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign050_feature_library_v1/snapshot_manifest.json"
)
C50_SNAPSHOT_SHA256 = (
    "8e95728fd9e1ba3d3ab820dbf5d92812bd18f9076ee901ee80cd76cf989300ef"
)
C50_DATASET_SHA256 = (
    "d758c059ff6fb602106c240c369d5d3db60eb245ec7cccf23d5a32b9f69dec8a"
)
C50_FACTOR_NAME = "intraday_half_session_extreme_shock_reversal_completion_2h"

_generated = previous._generated
_engine_globals = previous._engine_globals
market = previous.market
campaign044 = previous.campaign044
campaign045 = previous.campaign045
campaign046 = previous.campaign046
campaign047_reference = previous.campaign047_reference
campaign048_reference = previous.campaign048_reference


class Campaign051FeatureError(RuntimeError):
    """Fail-closed Campaign051 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [(str(item["name"]), str(item["score_direction"])) for item in comparisons],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign051_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign051FeatureError("Campaign051 implementation freeze is not bound")
    if _sha256(DEFAULT_IMPLEMENTATION_FREEZE) != IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign051FeatureError("Campaign051 implementation freeze changed")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign051_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign051_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign051FeatureError("Campaign051 implementation freeze semantics changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every Campaign051 preregistration binding and exact semantic."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign051FeatureError("Campaign051 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign051FeatureError("Campaign051 protocol has a failed binding")
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    inherited_spec = previous.load_protocol()
    inherited_uniqueness = inherited_spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]
    comparisons = copy.deepcopy(inherited_uniqueness.get("comparison_factors") or [])
    comparisons.append(copy.deepcopy(uniqueness.get("final_comparison_factor") or {}))
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    source = delta.get("source_chain") or {}
    if not (
        delta.get("version") == 2
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign051_no_return_preregistration"
        and delta.get("status")
        == "frozen_before_campaign051_minute_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("bin_count") == BIN_COUNT
        and candidate.get("selected_grid")
        == ["09:31-11:30", "13:01-15:00"]
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get("order_invariant") is True
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "alternate_field_bin_boundary_window_transform_direction_scale_board_year_cost_regime_fit_combination_or_model_search"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign050_comparison_factor_count")
        == INHERITED_COMPARISON_COUNT
        and uniqueness.get("inherited_campaign050_comparison_factor_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and len({str(item.get("name") or "") for item in comparisons})
        == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_74_must_pass") is True
        and comparisons[-1]
        == {"name": C50_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id")
        == "wf051_intraday_close_range_occupancy_entropy_10b_single_higher"
        and finite.get("kind") == "single_factor"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("development_interval") == ["2019-01-01", "2023-12-31"]
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("candidate49_ledgers_changed") is False
        and boundary.get("second_prospective_candidate_created") is False
    ):
        raise Campaign051FeatureError("Campaign051 protocol semantics changed")
    spec = copy.deepcopy(inherited_spec)
    spec.update(
        {
            "kind": delta["kind"],
            "status": delta["status"],
            "frozen_at": delta["frozen_at"],
            "purpose": delta["purpose"],
            "source_chain": copy.deepcopy(source),
            "candidates": [
                {
                    "name": FACTOR_NAME,
                    "direction": "higher",
                    "formula": FACTOR_FORMULA,
                    "source_fields_allowed": list(RAW_COLUMNS),
                    "source_fields_used_by_formula": list(RAW_COLUMNS),
                    "selected_bar_count": SELECTED_BAR_COUNT,
                    "bin_count": BIN_COUNT,
                    "valid_range": [LOWER_BOUND, UPPER_BOUND],
                }
            ],
            "ordered_no_return_gates": {
                "coverage_and_capacity_before_comparison_values": copy.deepcopy(
                    coverage
                ),
                "uniqueness_after_coverage_only": {
                    **copy.deepcopy(uniqueness),
                    "comparison_factors": comparisons,
                },
            },
            "finite_post_admissibility_search": {
                "candidate_factor_count": 1,
                "development_trial_count": 1,
                "trial": {
                    "trial_id": finite["trial_id"],
                    "factor": FACTOR_NAME,
                    "direction": "higher",
                    "transform": "none",
                    "threshold": "none",
                    "filter": "none",
                    "combination": "none",
                },
                "development_interval": {
                    "start": "2019-01-01",
                    "end": "2023-12-31",
                    "folds": copy.deepcopy(
                        inherited_spec["finite_post_admissibility_search"][
                            "development_interval"
                        ]["folds"]
                    ),
                    "purge_local_signal_sessions": 3,
                },
            },
        }
    )
    return spec


def compute_factor_values(
    *, closes: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen ten-bin normalized log-close occupancy entropy."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign051FeatureError("Campaign051 close shape is invalid")
    rows = len(closes)
    finite_close = np.isfinite(closes).all(axis=1)
    positive_close = (closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_closes = np.log(closes)
        low = np.min(log_closes, axis=1)
        high = np.max(log_closes, axis=1)
        span = high - low
        locations = (log_closes - low[:, None]) / span[:, None]
    span_valid = np.isfinite(span) & (span > 0.0)
    low_fix = (locations < 0.0) & (locations >= -ENDPOINT_TOLERANCE)
    high_fix = (locations > 1.0) & (locations <= 1.0 + ENDPOINT_TOLERANCE)
    canonical = np.where(low_fix, 0.0, locations)
    canonical = np.where(high_fix, 1.0, canonical)
    location_finite = np.isfinite(canonical).all(axis=1)
    location_in_range = ((canonical >= 0.0) & (canonical <= 1.0)).all(axis=1)
    safe_locations = np.where(
        location_finite[:, None] & location_in_range[:, None], canonical, 0.0
    )
    with np.errstate(invalid="ignore"):
        bin_index = np.floor(BIN_COUNT * safe_locations).astype(np.int64)
    bin_index = np.where(bin_index == BIN_COUNT, BIN_COUNT - 1, bin_index)
    bin_valid = ((bin_index >= 0) & (bin_index < BIN_COUNT)).all(axis=1)
    counts = np.stack(
        [(bin_index == index).sum(axis=1) for index in range(BIN_COUNT)], axis=1
    )
    probabilities = counts.astype(float) / float(SELECTED_BAR_COUNT)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        terms = np.where(probabilities > 0.0, probabilities * np.log(probabilities), 0.0)
        raw_score = -np.sum(terms, axis=1) / np.log(float(BIN_COUNT))
    low_score_fix = (raw_score < LOWER_BOUND) & (
        raw_score >= LOWER_BOUND - ENDPOINT_TOLERANCE
    )
    high_score_fix = (raw_score > UPPER_BOUND) & (
        raw_score <= UPPER_BOUND + ENDPOINT_TOLERANCE
    )
    score = np.where(low_score_fix, LOWER_BOUND, raw_score)
    score = np.where(high_score_fix, UPPER_BOUND, score)
    score_finite = np.isfinite(score)
    score_in_range = (score >= LOWER_BOUND) & (score <= UPPER_BOUND)
    eligible = (
        finite_close
        & positive_close
        & span_valid
        & location_finite
        & location_in_range
        & bin_valid
        & score_finite
        & score_in_range
    )
    sorted_log = np.sort(log_closes, axis=1)
    repeated_positions = (np.diff(sorted_log, axis=1) == 0.0).sum(axis=1)
    endpoint_rows = (low_fix | high_fix).any(axis=1) | low_score_fix | high_score_fix
    quality = {
        "base_rows": int(rows),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__nonfinite_close_rows": int((~finite_close).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_close & ~positive_close).sum()
        ),
        f"{FACTOR_NAME}__zero_log_close_range_rows": int(
            (finite_close & positive_close & ~span_valid).sum()
        ),
        f"{FACTOR_NAME}__exact_repeated_close_positions": int(
            repeated_positions[finite_close & positive_close].sum()
        ),
        f"{FACTOR_NAME}__empty_bin_positions": int(
            (counts[finite_close & positive_close & span_valid] == 0).sum()
        ),
        f"{FACTOR_NAME}__invalid_location_or_bin_rows": int(
            (
                finite_close
                & positive_close
                & span_valid
                & ~(location_finite & location_in_range & bin_valid)
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & endpoint_rows).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": int(
            (
                finite_close
                & positive_close
                & span_valid
                & location_finite
                & location_in_range
                & bin_valid
                & (~score_finite | ~score_in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, score, np.nan)},
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
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign051FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign051FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if (
        base_work["trade_date"].isna().any()
        or (not base_work.empty and set(base_work["symbol"].unique()) != {symbol.upper()})
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign051FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign051FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign051FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign051FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign051FeatureError(f"source and joint-base dates changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign051FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, SELECTED_BAR_COUNT)
    values, eligible, quality = compute_factor_values(closes=closes)
    frame = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: values[FACTOR_NAME],
            f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
        }
    )
    return frame.loc[:, OUTPUT_COLUMNS], quality


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = "a_share_three_day_walkforward_campaign051_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {
            key: value
            for key, value in (manifest.get("protocol_evidence") or {}).items()
            if not key.startswith("campaign050_")
            and not key.startswith("campaign051_")
        }
        evidence["campaign051_mechanism_overlap_audit_sha256"] = (
            MECHANISM_AUDIT_SHA256
        )
        evidence["campaign051_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign051_implementation_freeze_sha256"] = (
            IMPLEMENTATION_FREEZE_SHA256
        )
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign051_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign051_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign051_no_return_preregistration_sha256")
        == PROTOCOL_SHA256
        and evidence.get("campaign051_implementation_freeze_sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and isinstance(manifest.get("rows"), int)
        and manifest["rows"] > 0
        and manifest.get("partitions") == len(files)
        and quality.get("base_rows") == manifest.get("rows")
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible_rows
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
    ):
        raise Campaign051FeatureError("Campaign051 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign051FeatureError("Campaign051 snapshot fingerprint is not bound")


def _install_engine_globals() -> None:
    values = {
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
        "RAW_COLUMNS": RAW_COLUMNS,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_NAMES": FACTOR_NAMES,
        "FACTOR_DIRECTIONS": FACTOR_DIRECTIONS,
        "FACTOR_RANGES": FACTOR_RANGES,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "FACTOR_FORMULAS": FACTOR_FORMULAS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
        "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
        "NO_RETURN_AUDIT_SHA256": NO_RETURN_AUDIT_SHA256,
        "load_protocol": load_protocol,
        "compute_factor_values": compute_factor_values,
        "compute_partition_frame": compute_partition_frame,
        "_validate_snapshot_manifest": _validate_snapshot_manifest,
        "output_root": output_root,
    }
    _generated.update(values)
    _engine_globals.update(values)


_install_engine_globals()
empty_output_frame = _generated["empty_output_frame"]
verify_snapshot_files = _generated["verify_snapshot_files"]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    _install_engine_globals()
    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original = publication_foundation.atomic_write_json

    def write_with_truth(value: dict[str, Any], path: Path) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign051_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value.update(
                {
                    "source_open_high_low_read": False,
                    "source_close_read": True,
                    "source_volume_read": False,
                    "source_amount_read": False,
                }
            )
        original(value, path)

    publication_foundation.atomic_write_json = write_with_truth
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original


def _load_candidate_frame(
    manifest_path: Path, manifest: dict[str, Any]
) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    _load_implementation_freeze()
    if not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and SNAPSHOT_PUBLICATION_BINDING_SHA256
    ):
        raise Campaign051FeatureError(
            "bind Campaign051 snapshot and publication record before audit"
        )
    if _sha256(DEFAULT_SNAPSHOT_BINDING) != SNAPSHOT_PUBLICATION_BINDING_SHA256:
        raise Campaign051FeatureError("Campaign051 snapshot publication binding changed")
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    _install_engine_globals()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign051FeatureError("Campaign051 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign051_no_return_audit.json"))
    if existing:
        if (
            len(existing) != 1
            or not NO_RETURN_AUDIT_SHA256
            or _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256
        ):
            raise Campaign051FeatureError(
                "existing Campaign051 audit is ambiguous or unbound"
            )
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, candidate49, comparison_engine = campaign044._context()
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate, eligible_keys, spec, FACTOR_NAME
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        catalog, source_verifications = campaign044._build_source_catalog(
            data_root=data_root, workers=workers, verify_files=True
        )
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            aligned = campaign044._load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(
                    comparison_engine._aligned_comparison_result(
                        candidate_keys=keys,
                        candidate_values=values,
                        comparison_values=aligned.pop(factor),
                        comparison=factor,
                        direction=directions[factor],
                        gate=gate,
                    )
                )
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign051FeatureError("complete 66-factor catalog changed")
        _, candidate49_path, candidate49_manifest = engine._comparison_chain(data_root)
        candidate49_verification = candidate49.verify_snapshot_files(
            candidate49_manifest, candidate49_path, workers
        )
        candidate49_values = engine._load_filtered_comparison_values_explicit(
            candidate49_manifest, [candidate49.FACTOR_NAME], keys
        )[candidate49.FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=candidate49_values,
                comparison=candidate49.FACTOR_NAME,
                direction="higher",
                gate=gate,
            )
        )
        del candidate49_values
        extra_verifications: dict[str, Any] = {}
        base = previous._base
        sources = [
            (
                "campaign044",
                base.C44_SNAPSHOT_PATH,
                base.C44_SNAPSHOT_SHA256,
                None,
                base.C44_FACTOR_NAME,
                campaign044,
            ),
            (
                "campaign045",
                base.C45_SNAPSHOT_PATH,
                base.C45_SNAPSHOT_SHA256,
                base.C45_DATASET_SHA256,
                base.C45_FACTOR_NAME,
                campaign045,
            ),
            (
                "campaign046",
                base.C46_SNAPSHOT_PATH,
                base.C46_SNAPSHOT_SHA256,
                base.C46_DATASET_SHA256,
                base.C46_FACTOR_NAME,
                campaign046,
            ),
            (
                "campaign047",
                base.C47_SNAPSHOT_PATH,
                base.C47_SNAPSHOT_SHA256,
                base.C47_DATASET_SHA256,
                base.C47_FACTOR_NAME,
                campaign047_reference,
            ),
            (
                "campaign048",
                base.C48_SNAPSHOT_PATH,
                base.C48_SNAPSHOT_SHA256,
                base.C48_DATASET_SHA256,
                base.C48_FACTOR_NAME,
                campaign048_reference,
            ),
            (
                "campaign049",
                previous.C49_SNAPSHOT_PATH,
                previous.C49_SNAPSHOT_SHA256,
                previous.C49_DATASET_SHA256,
                previous.C49_FACTOR_NAME,
                previous._base,
            ),
            (
                "campaign050",
                C50_SNAPSHOT_PATH,
                C50_SNAPSHOT_SHA256,
                C50_DATASET_SHA256,
                C50_FACTOR_NAME,
                previous,
            ),
        ]
        for label, source_path, expected_sha, expected_dataset, factor, module in sources:
            if _sha256(source_path) != expected_sha:
                raise Campaign051FeatureError(f"{label} snapshot manifest changed")
            source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
            if (
                expected_dataset is not None
                and source_manifest.get("dataset_sha256") != expected_dataset
            ):
                raise Campaign051FeatureError(f"{label} snapshot dataset changed")
            extra_verifications[label] = module.verify_snapshot_files(
                source_manifest, source_path, workers
            )
            comparison_values = engine._load_filtered_comparison_values_explicit(
                source_manifest, [factor], keys
            )[factor]
            comparisons.append(
                comparison_engine._aligned_comparison_result(
                    candidate_keys=keys,
                    candidate_values=values,
                    comparison_values=comparison_values,
                    comparison=factor,
                    direction="higher",
                    gate=gate,
                )
            )
            del comparison_values
            gc.collect()
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = (
            observed_order == expected_order
            and len(comparisons) == COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order
            == expected_order,
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            **{
                f"{key}_snapshot_file_verification": value
                for key, value in extra_verifications.items()
            },
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(
                observed_correlations
            )
            if observed_correlations
            else None,
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
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
    research = prior.research
    run_id = f"{research._timestamp()}_campaign051_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign051_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration"
        if admitted
        else "completed_zero_admissible_factors_stop_before_historical_returns",
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_publication_binding": {
            "path": str(DEFAULT_SNAPSHOT_BINDING.resolve()),
            "sha256": SNAPSHOT_PUBLICATION_BINDING_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign051 walk-forward catalog before reading 2019-2023 returns"
        if admitted
        else "record the no-return rejection and design a genuinely new campaign",
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_fields_read": [],
        "minute_close_fields_read": ["close"],
        "minute_volume_amount_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    _install_engine_globals()
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign051_no_return_audit.json")
    )
    result = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "implementation_freeze_sha256_bound": bool(IMPLEMENTATION_FREEZE_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
        "second_prospective_candidate_created": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "build", "no-return-audit"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--workers", type=int, default=4)
        if name in {"status", "no-return-audit"}:
            command.add_argument(
                "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
            )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root, args.experiment_root)
    elif args.command == "build":
        payload = {
            "manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))
        }
    else:
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
