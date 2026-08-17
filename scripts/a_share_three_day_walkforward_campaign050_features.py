#!/usr/bin/env python3
"""Build and audit Campaign050 half-session extreme-shock reversal completion."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign049_features.py"
BASE_FEATURE_RUNNER_SHA256 = "981378510744bb53bb5353d1bf99ca9850b4f10c49bd8500d38d29994bdeff83"
FACTOR_NAME = "intraday_half_session_extreme_shock_reversal_completion_2h"
FACTOR_FORMULA = (
    "Within each independent 120-close half-session form 119 adjacent log "
    "returns. Choose the earliest index k attaining the maximum absolute "
    "return, let s be that return, and let R=log(last_close_in_half/"
    "close_immediately_after_s). Define h=-2*s*R/(s^2+R^2). Return the "
    "arithmetic mean of the morning and afternoon h values."
)
MECHANISM_AUDIT_SHA256 = "26679fc013e1606857f5c8b608c132058b6be410d3b04854435022af7986c33a"
PROTOCOL_SHA256 = "32c3e889e736e050fb0326f2bceb6ddd820ae7a0b9c5f6bac09c90a5afebb10e"
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

TERMINAL_LIBRARY_COUNT = 66
COMPARISON_COUNT = 73
INHERITED_COMPARISON_COUNT = 72
INHERITED_COMPARISON_ORDER_SHA256 = "6bbe43d7f1077d0f76af53149ab40d048e4e4e299bab73b1562be54e974083f5"
COMPARISON_ORDER_SHA256 = "eae7db172c0e54a47f5ea41570cb585dceb6f70cb25ee0088064908aed118a3c"
SELECTED_BAR_COUNT = 240
CLOSES_PER_HALF = 120
RETURNS_PER_HALF = 119
SELECTED_EXTREME_COUNT = 2
ENDPOINT_TOLERANCE = 1e-12
LOWER_BOUND = -1.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign050_feature_library_v1"
)
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_feature_implementation_freeze_20260801.json"
DEFAULT_SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_snapshot_publication_binding_20260801.json"
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_050/no_return"
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
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
C49_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign049_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign049_feature_library_v1/snapshot_manifest.json"
)
C49_SNAPSHOT_SHA256 = "6c27933f232926f33d750f624fc6ad32c394c2e97922043502e997275c1ace1d"
C49_DATASET_SHA256 = "c60c1f245e2bbfdd12acdcfdd8417799684fcda09caf4472270d870ba911164c"
C49_FACTOR_NAME = "intraday_morning_afternoon_amount_profile_similarity_120b"


class Campaign050FeatureError(RuntimeError):
    """Fail-closed Campaign050 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise Campaign050FeatureError("frozen Campaign049 feature orchestration changed")

_spec = importlib.util.spec_from_file_location(
    "a_share_three_day_walkforward_campaign050_inherited_engine",
    BASE_FEATURE_RUNNER,
)
if _spec is None or _spec.loader is None:
    raise Campaign050FeatureError("Campaign049 inherited engine could not load")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
_generated = _base._generated
_engine_globals = _base._engine_globals
DEFAULT_DATA_ROOT = _base.DEFAULT_DATA_ROOT
BASE_COLUMNS = _base.BASE_COLUMNS
market = _base.market
campaign044 = _base.campaign044
campaign045 = _base.campaign045
campaign046 = _base.campaign046
campaign047_reference = _base.campaign047_reference
campaign048_reference = _base.campaign048_reference


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
        / "derived/a_share/rich/tushare/minute_walkforward_campaign050_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign050FeatureError("Campaign050 implementation freeze is not bound")
    if _sha256(DEFAULT_IMPLEMENTATION_FREEZE) != IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign050FeatureError("Campaign050 implementation freeze changed")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind") == "a_share_three_day_walkforward_campaign050_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign050_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign050FeatureError("Campaign050 implementation freeze semantics changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every Campaign050 preregistration binding and exact semantic."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign050FeatureError("Campaign050 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign050FeatureError("Campaign050 protocol has a failed binding")
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    inherited_spec = _base.load_protocol()
    inherited_uniqueness = inherited_spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]
    comparisons = copy.deepcopy(inherited_uniqueness.get("comparison_factors") or [])
    comparisons.append(copy.deepcopy(uniqueness.get("final_comparison_factor") or {}))
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    source = delta.get("source_chain") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind") == "a_share_three_day_walkforward_campaign050_no_return_preregistration"
        and delta.get("status") == "frozen_before_campaign050_minute_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256") == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("closes_per_half") == CLOSES_PER_HALF
        and candidate.get("returns_per_half") == RETURNS_PER_HALF
        and candidate.get("selected_extreme_count") == SELECTED_EXTREME_COUNT
        and candidate.get("selected_grid") == ["09:31-11:30", "13:01-15:00"]
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get("absolute_shock_tie_rule") == "Choose the earliest index attaining the maximum absolute log return separately within each half-session."
        and candidate.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == {"lower": -1.0, "lower_inclusive": True, "upper": 1.0, "upper_inclusive": True}
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get("alternate_field_tie_window_transform_direction_scale_board_year_cost_regime_fit_combination_or_model_search") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign049_comparison_factor_count") == INHERITED_COMPARISON_COUNT
        and uniqueness.get("inherited_campaign049_comparison_factor_order_sha256") == INHERITED_COMPARISON_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and len({str(item.get("name") or "") for item in comparisons}) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_73_must_pass") is True
        and comparisons[-1] == {"name": C49_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id") == "wf050_intraday_half_session_extreme_shock_reversal_completion_2h_single_higher"
        and finite.get("kind") == "single_factor"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("development_interval") == ["2019-01-01", "2023-12-31"]
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition") is True
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("candidate49_ledgers_changed") is False
        and boundary.get("candidate50_prospective_activation_created") is False
    ):
        raise Campaign050FeatureError("Campaign050 protocol semantics changed")
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
                    "closes_per_half": CLOSES_PER_HALF,
                    "returns_per_half": RETURNS_PER_HALF,
                    "selected_extreme_count": SELECTED_EXTREME_COUNT,
                    "valid_range": [LOWER_BOUND, UPPER_BOUND],
                }
            ],
            "ordered_no_return_gates": {
                "coverage_and_capacity_before_comparison_values": copy.deepcopy(coverage),
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


def _half_scores(half_closes: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    half_closes = np.asarray(half_closes, dtype=float)
    if half_closes.ndim != 2 or half_closes.shape[1] != CLOSES_PER_HALF:
        raise Campaign050FeatureError("Campaign050 half-close shape is invalid")
    finite = np.isfinite(half_closes).all(axis=1)
    positive = (half_closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_closes = np.log(half_closes)
        returns = np.diff(log_closes, axis=1)
    return_finite = np.isfinite(returns).all(axis=1)
    safe_abs = np.where(np.isfinite(returns), np.abs(returns), -np.inf)
    selected_index = np.argmax(safe_abs, axis=1)
    selected = np.take_along_axis(returns, selected_index[:, None], axis=1)[:, 0]
    selected_close = np.take_along_axis(
        log_closes, (selected_index + 1)[:, None], axis=1
    )[:, 0]
    terminal_retracement = log_closes[:, -1] - selected_close
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denominator = selected * selected + terminal_retracement * terminal_retracement
        raw = -2.0 * selected * terminal_retracement / denominator
    nonzero_support = np.max(np.where(np.isfinite(returns), np.abs(returns), 0.0), axis=1) > 0.0
    components_finite = (
        return_finite
        & np.isfinite(selected)
        & np.isfinite(terminal_retracement)
        & np.isfinite(denominator)
        & np.isfinite(raw)
    )
    eligible = finite & positive & nonzero_support & components_finite & (denominator > 0.0)
    return (
        np.where(eligible, raw, np.nan),
        eligible,
        {
            "finite_close": finite,
            "positive_close": positive,
            "return_finite": return_finite,
            "nonzero_support": nonzero_support,
            "selected_index": selected_index,
            "selected_shock": selected,
            "terminal_retracement": terminal_retracement,
            "denominator": denominator,
            "raw_score": raw,
            "zero_return_positions": (returns == 0.0).sum(axis=1),
        },
    )


def compute_factor_values(
    *, closes: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen two-half extreme-shock terminal reversal score."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign050FeatureError("Campaign050 close shape is invalid")
    rows = len(closes)
    morning_values, morning_eligible, morning = _half_scores(
        closes[:, :CLOSES_PER_HALF]
    )
    afternoon_values, afternoon_eligible, afternoon = _half_scores(
        closes[:, CLOSES_PER_HALF:]
    )
    raw_values = 0.5 * (morning_values + afternoon_values)
    low_fix = (raw_values < LOWER_BOUND) & (
        raw_values >= LOWER_BOUND - ENDPOINT_TOLERANCE
    )
    high_fix = (raw_values > UPPER_BOUND) & (
        raw_values <= UPPER_BOUND + ENDPOINT_TOLERANCE
    )
    values = np.where(low_fix, LOWER_BOUND, raw_values)
    values = np.where(high_fix, UPPER_BOUND, values)
    finite_score = np.isfinite(values)
    in_range = (values >= LOWER_BOUND) & (values <= UPPER_BOUND)
    eligible = morning_eligible & afternoon_eligible & finite_score & in_range
    finite_close = np.isfinite(closes).all(axis=1)
    positive_close = (closes > 0.0).all(axis=1)
    required_valid = finite_close & positive_close
    quality = {
        "base_rows": int(rows),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__nonfinite_close_rows": int((~finite_close).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_close & ~positive_close).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_return_positions": int(
            morning["zero_return_positions"].sum()
            + afternoon["zero_return_positions"].sum()
        ),
        f"{FACTOR_NAME}__all_zero_morning_return_rows": int(
            (required_valid & ~morning["nonzero_support"]).sum()
        ),
        f"{FACTOR_NAME}__all_zero_afternoon_return_rows": int(
            (required_valid & ~afternoon["nonzero_support"]).sum()
        ),
        f"{FACTOR_NAME}__selected_morning_final_return_rows": int(
            (required_valid & (morning["selected_index"] == RETURNS_PER_HALF - 1)).sum()
        ),
        f"{FACTOR_NAME}__selected_afternoon_final_return_rows": int(
            (required_valid & (afternoon["selected_index"] == RETURNS_PER_HALF - 1)).sum()
        ),
        f"{FACTOR_NAME}__invalid_return_component_or_denominator_rows": int(
            (
                required_valid
                & morning["nonzero_support"]
                & afternoon["nonzero_support"]
                & ~(morning_eligible & afternoon_eligible)
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & (low_fix | high_fix)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                morning_eligible
                & afternoon_eligible
                & (~finite_score | ~in_range)
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
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign050FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign050FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign050FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
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
        raise Campaign050FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign050FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign050FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign050FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign050FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
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
        manifest["kind"] = "a_share_three_day_walkforward_campaign050_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {
            key: value
            for key, value in (manifest.get("protocol_evidence") or {}).items()
            if not key.startswith("campaign049_")
            and not key.startswith("campaign050_")
        }
        evidence["campaign050_mechanism_overlap_audit_sha256"] = MECHANISM_AUDIT_SHA256
        evidence["campaign050_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign050_implementation_freeze_sha256"] = IMPLEMENTATION_FREEZE_SHA256
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign050_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
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
        and evidence.get("campaign050_mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign050_no_return_preregistration_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign050_implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
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
        and manifest.get("current_scoring_selection_sizing_or_orders_performed") is False
        and manifest.get("prospective_candidate_activation_created") is False
    ):
        raise Campaign050FeatureError("Campaign050 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign050FeatureError("Campaign050 snapshot fingerprint is not bound")


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
            == "a_share_three_day_walkforward_campaign050_feature_snapshot"
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
        raise Campaign050FeatureError(
            "bind Campaign050 snapshot and publication record before audit"
        )
    if _sha256(DEFAULT_SNAPSHOT_BINDING) != SNAPSHOT_PUBLICATION_BINDING_SHA256:
        raise Campaign050FeatureError(
            "Campaign050 snapshot publication binding changed"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    _install_engine_globals()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign050FeatureError("Campaign050 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign050_no_return_audit.json"))
    if existing:
        if (
            len(existing) != 1
            or not NO_RETURN_AUDIT_SHA256
            or _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256
        ):
            raise Campaign050FeatureError(
                "existing Campaign050 audit is ambiguous or unbound"
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
            raise Campaign050FeatureError("complete 66-factor catalog changed")
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
        sources = [
            (
                "campaign044",
                _base.C44_SNAPSHOT_PATH,
                _base.C44_SNAPSHOT_SHA256,
                None,
                _base.C44_FACTOR_NAME,
                campaign044,
            ),
            (
                "campaign045",
                _base.C45_SNAPSHOT_PATH,
                _base.C45_SNAPSHOT_SHA256,
                _base.C45_DATASET_SHA256,
                _base.C45_FACTOR_NAME,
                campaign045,
            ),
            (
                "campaign046",
                _base.C46_SNAPSHOT_PATH,
                _base.C46_SNAPSHOT_SHA256,
                _base.C46_DATASET_SHA256,
                _base.C46_FACTOR_NAME,
                campaign046,
            ),
            (
                "campaign047",
                _base.C47_SNAPSHOT_PATH,
                _base.C47_SNAPSHOT_SHA256,
                _base.C47_DATASET_SHA256,
                _base.C47_FACTOR_NAME,
                campaign047_reference,
            ),
            (
                "campaign048",
                _base.C48_SNAPSHOT_PATH,
                _base.C48_SNAPSHOT_SHA256,
                _base.C48_DATASET_SHA256,
                _base.C48_FACTOR_NAME,
                campaign048_reference,
            ),
            (
                "campaign049",
                C49_SNAPSHOT_PATH,
                C49_SNAPSHOT_SHA256,
                C49_DATASET_SHA256,
                C49_FACTOR_NAME,
                _base,
            ),
        ]
        for label, path, expected_sha, expected_dataset, factor, module in sources:
            if _sha256(path) != expected_sha:
                raise Campaign050FeatureError(f"{label} snapshot manifest changed")
            source_manifest = json.loads(path.read_text(encoding="utf-8"))
            if (
                expected_dataset is not None
                and source_manifest.get("dataset_sha256") != expected_dataset
            ):
                raise Campaign050FeatureError(f"{label} snapshot dataset changed")
            extra_verifications[label] = module.verify_snapshot_files(
                source_manifest, path, workers
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
    run_id = f"{research._timestamp()}_campaign050_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign050_no_return_audit",
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
        "next_action": "freeze the exact one-trial Campaign050 walk-forward catalog before reading 2019-2023 returns"
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
        "candidate50_prospective_activation_created": False,
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
        experiment_root.expanduser().resolve().glob("*_campaign050_no_return_audit.json")
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
        "candidate50_prospective_activation_created": False,
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
            "manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
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
