#!/usr/bin/env python3
"""Build and audit Campaign048 two-sided wick absorption balance."""

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
    import scripts.a_share_three_day_walkforward_campaign044_features as campaign044
    import scripts.a_share_three_day_walkforward_campaign045_features as campaign045
    import scripts.a_share_three_day_walkforward_campaign046_features as campaign046
    import scripts.a_share_three_day_walkforward_campaign047_features_v2 as campaign047_reference
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign044_features as campaign044
    import a_share_three_day_walkforward_campaign045_features as campaign045
    import a_share_three_day_walkforward_campaign046_features as campaign046
    import a_share_three_day_walkforward_campaign047_features_v2 as campaign047_reference


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign047_features_v2.py"
BASE_FEATURE_RUNNER_SHA256 = "18b5a403024aafca3db2ca7a33d1209cd7a4140f6ccaf91c84276fc9b6b58e98"
FACTOR_NAME = "intraday_two_sided_wick_absorption_balance_240m"
FACTOR_FORMULA = (
    "Across exactly 240 bars at 09:31-11:30 and 13:01-15:00, define "
    "lower wick l_i=log(min(open_i,close_i)/low_i) and upper wick "
    "u_i=log(high_i/max(open_i,close_i)). Pool L=sum(l_i) and U=sum(u_i) "
    "and return 2*min(L,U)/(L+U)."
)
MECHANISM_AUDIT_SHA256 = "a876b4cb47083cceebc2fdc443784f8039ac3bfbc6014287528eaa50c61c489f"
PROTOCOL_SHA256 = "8adef382963cadcf7e19635ec1cc40e152f0a5f3feddfb1c673303de4687f1ab"
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

TERMINAL_LIBRARY_COUNT = 66
COMPARISON_COUNT = 71
INHERITED_COMPARISON_COUNT = 70
INHERITED_COMPARISON_ORDER_SHA256 = "d40b78fbe34941dec83c61f6ddeaed928b7c2e1c641096b893e52f7d272e3b94"
COMPARISON_ORDER_SHA256 = "271fb3b58605799788a3b966ab9b19f2348cd5533ffd18b140363ba497061c64"
SELECTED_BAR_COUNT = 240
MINIMUM_POSITIVE_RANGE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign048_feature_library_v1"
)
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_feature_implementation_freeze_20260801.json"
DEFAULT_SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_snapshot_publication_binding_20260801.json"
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_048/no_return"
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")
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
C47_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign047_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign047_feature_library_v1/snapshot_manifest.json"
)
C47_SNAPSHOT_SHA256 = "5d692215083bd5db0ef44c49364c16a845112167f85d219b581a04fab57ac4d7"
C47_DATASET_SHA256 = "bbbf064183ea1a989e4f66734550e600f9afd59ecdc8268e6bb267207903433b"
C47_FACTOR_NAME = "intraday_body_next_microgap_reversal_238p"


class Campaign048FeatureError(RuntimeError):
    """Fail-closed Campaign048 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise Campaign048FeatureError("frozen Campaign047 feature orchestration changed")

_spec = importlib.util.spec_from_file_location(
    "a_share_three_day_walkforward_campaign048_inherited_engine",
    BASE_FEATURE_RUNNER,
)
if _spec is None or _spec.loader is None:
    raise Campaign048FeatureError("Campaign047 inherited engine could not load")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
_generated = _base._generated
_engine_globals = _base._engine_globals
DEFAULT_DATA_ROOT = _base.DEFAULT_DATA_ROOT
BASE_COLUMNS = _base.BASE_COLUMNS
market = _base.market
C44_SNAPSHOT_PATH = _base.C44_SNAPSHOT_PATH
C44_SNAPSHOT_SHA256 = _base.C44_SNAPSHOT_SHA256
C44_FACTOR_NAME = _base.C44_FACTOR_NAME
C45_SNAPSHOT_PATH = _base.C45_SNAPSHOT_PATH
C45_SNAPSHOT_SHA256 = _base.C45_SNAPSHOT_SHA256
C45_DATASET_SHA256 = _base.C45_DATASET_SHA256
C45_FACTOR_NAME = _base.C45_FACTOR_NAME
C46_SNAPSHOT_PATH = _base.C46_SNAPSHOT_PATH
C46_SNAPSHOT_SHA256 = _base.C46_SNAPSHOT_SHA256
C46_DATASET_SHA256 = _base.C46_DATASET_SHA256
C46_FACTOR_NAME = _base.C46_FACTOR_NAME


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [(str(item["name"]), str(item["score_direction"])) for item in comparisons],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign048FeatureError("Campaign048 implementation freeze is not bound")
    if _sha256(DEFAULT_IMPLEMENTATION_FREEZE) != IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign048FeatureError("Campaign048 implementation freeze changed")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind") == "a_share_three_day_walkforward_campaign048_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign048_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign048FeatureError("Campaign048 implementation freeze semantics changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every Campaign048 preregistration binding and exact semantic."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign048FeatureError("Campaign048 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign048FeatureError("Campaign048 protocol has a failed binding")
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    source = delta.get("source_chain") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind") == "a_share_three_day_walkforward_campaign048_no_return_preregistration"
        and delta.get("status") == "frozen_before_campaign048_minute_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256") == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("selected_grid") == ["09:31-11:30", "13:01-15:00"]
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get("minimum_positive_range_bars") == MINIMUM_POSITIVE_RANGE_BARS
        and candidate.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == {"lower": 0.0, "lower_inclusive": True, "upper": 1.0, "upper_inclusive": True}
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get("alternate_field_window_transform_direction_scale_board_year_cost_regime_fit_combination_or_model_search") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign047_comparison_factor_count") == INHERITED_COMPARISON_COUNT
        and uniqueness.get("inherited_campaign047_comparison_factor_order_sha256") == INHERITED_COMPARISON_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and len({str(item.get("name") or "") for item in comparisons}) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_71_must_pass") is True
        and comparisons[-1] == {"name": C47_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id") == "wf048_intraday_two_sided_wick_absorption_balance_240m_single_higher"
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
        and boundary.get("candidate50_activation_created") is False
    ):
        raise Campaign048FeatureError("Campaign048 protocol semantics changed")
    spec = copy.deepcopy(campaign047_reference.load_protocol())
    spec.update({
        "kind": delta["kind"],
        "status": delta["status"],
        "frozen_at": delta["frozen_at"],
        "purpose": delta["purpose"],
        "source_chain": copy.deepcopy(source),
        "candidates": [{
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "source_fields_allowed": list(RAW_COLUMNS),
            "source_fields_used_by_formula": list(RAW_COLUMNS),
            "selected_bar_count": SELECTED_BAR_COUNT,
            "minimum_positive_range_bars": MINIMUM_POSITIVE_RANGE_BARS,
            "valid_range": [LOWER_BOUND, UPPER_BOUND],
        }],
        "ordered_no_return_gates": {
            "coverage_and_capacity_before_comparison_values": copy.deepcopy(coverage),
            "uniqueness_after_coverage_only": copy.deepcopy(uniqueness),
        },
        "finite_post_admissibility_search": {
            "candidate_factor_count": 1,
            "development_trial_count": 1,
            "trial": {"trial_id": finite["trial_id"], "factor": FACTOR_NAME, "direction": "higher", "transform": "none", "threshold": "none", "filter": "none", "combination": "none"},
            "development_interval": {
                "start": "2019-01-01",
                "end": "2023-12-31",
                "folds": copy.deepcopy(campaign047_reference.load_protocol()["finite_post_admissibility_search"]["development_interval"]["folds"]),
                "purge_local_signal_sessions": 3,
            },
        },
    })
    return spec


def compute_factor_values(
    *, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen two-sided upper/lower wick balance."""

    arrays = [np.asarray(value, dtype=float) for value in (opens, highs, lows, closes)]
    opens, highs, lows, closes = arrays
    expected = (len(closes), SELECTED_BAR_COUNT)
    if any(value.ndim != 2 or value.shape != expected for value in arrays):
        raise Campaign048FeatureError("Campaign048 OHLC shape is invalid")
    finite_each = [np.isfinite(value).all(axis=1) for value in arrays]
    positive_each = [(value > 0.0).all(axis=1) for value in arrays]
    finite = np.logical_and.reduce(finite_each)
    positive = np.logical_and.reduce(positive_each)
    lower_body = np.minimum(opens, closes)
    upper_body = np.maximum(opens, closes)
    ordered = ((lows <= lower_body) & (lower_body <= upper_body) & (upper_body <= highs)).all(axis=1)
    required_valid = finite & positive & ordered
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_ranges = np.log(highs / lows)
        lower_wicks = np.log(lower_body / lows)
        upper_wicks = np.log(highs / upper_body)
        lower_sum = np.sum(lower_wicks, axis=1)
        upper_sum = np.sum(upper_wicks, axis=1)
        denominator = lower_sum + upper_sum
        raw_values = np.divide(
            2.0 * np.minimum(lower_sum, upper_sum),
            denominator,
            out=np.full(len(closes), np.nan, dtype=float),
            where=denominator > 0.0,
        )
    finite_components = (
        np.isfinite(log_ranges).all(axis=1)
        & np.isfinite(lower_wicks).all(axis=1)
        & np.isfinite(upper_wicks).all(axis=1)
        & np.isfinite(lower_sum)
        & np.isfinite(upper_sum)
        & np.isfinite(denominator)
    )
    positive_range_count = (log_ranges > 0.0).sum(axis=1)
    support = positive_range_count >= MINIMUM_POSITIVE_RANGE_BARS
    low_fix = (raw_values < LOWER_BOUND) & (raw_values >= LOWER_BOUND - ENDPOINT_TOLERANCE)
    high_fix = (raw_values > UPPER_BOUND) & (raw_values <= UPPER_BOUND + ENDPOINT_TOLERANCE)
    values = np.where(low_fix, LOWER_BOUND, raw_values)
    values = np.where(high_fix, UPPER_BOUND, values)
    finite_score = np.isfinite(values)
    in_range = (values >= LOWER_BOUND) & (values <= UPPER_BOUND)
    eligible = required_valid & finite_components & support & (denominator > 0.0) & finite_score & in_range
    quality = {
        "base_rows": int(len(closes)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__nonfinite_open_rows": int((~finite_each[0]).sum()),
        f"{FACTOR_NAME}__nonfinite_high_rows": int((~finite_each[1]).sum()),
        f"{FACTOR_NAME}__nonfinite_low_rows": int((~finite_each[2]).sum()),
        f"{FACTOR_NAME}__nonfinite_close_rows": int((~finite_each[3]).sum()),
        f"{FACTOR_NAME}__nonpositive_ohlc_rows": int((finite & ~positive).sum()),
        f"{FACTOR_NAME}__invalid_ohlc_order_rows": int((finite & positive & ~ordered).sum()),
        f"{FACTOR_NAME}__below_minimum_positive_range_rows": int((required_valid & finite_components & ~support).sum()),
        f"{FACTOR_NAME}__exact_zero_lower_wick_positions": int((lower_wicks == 0.0).sum()),
        f"{FACTOR_NAME}__exact_zero_upper_wick_positions": int((upper_wicks == 0.0).sum()),
        f"{FACTOR_NAME}__zero_wick_denominator_rows": int((required_valid & finite_components & support & ~(denominator > 0.0)).sum()),
        f"{FACTOR_NAME}__invalid_wick_component_rows": int((required_valid & ~finite_components).sum()),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int((eligible & (low_fix | high_fix)).sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int((required_valid & finite_components & support & (denominator > 0.0) & (~finite_score | ~in_range)).sum()),
    }
    return ({FACTOR_NAME: np.where(eligible, values, np.nan)}, {FACTOR_NAME: eligible}, quality)


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign048FeatureError(f"unexpected raw columns for {symbol}: {tuple(raw.columns)}")
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign048FeatureError(f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}")
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(base_work["trade_date"], errors="coerce").dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    if base_work["trade_date"].isna().any() or set(base_work["symbol"].unique()) != {symbol.upper()} or base_work.duplicated(["trade_date", "symbol"]).any():
        raise Campaign048FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("open", "high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if work["datetime"].isna().any() or set(work["symbol"].unique()) != {symbol.upper()} or set(work["provider"].unique()) != {"tushare"} or work.duplicated(["datetime"]).any():
        raise Campaign048FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign048FeatureError(f"every source stock-day must retain 241 rows for {symbol}")
    source_codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign048FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign048FeatureError(f"source and joint-base dates changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "open", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(continuous["minute_code"], categories=market.CONTINUOUS_MINUTE_CODES, ordered=True)
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign048FeatureError(f"continuous minute grid changed for {symbol}")
    matrices = {column: continuous[column].to_numpy(dtype=float).reshape(-1, SELECTED_BAR_COUNT) for column in ("open", "high", "low", "close")}
    values, eligible, quality = compute_factor_values(
        opens=matrices["open"], highs=matrices["high"], lows=matrices["low"], closes=matrices["close"]
    )
    frame = pd.DataFrame({
        "trade_date": base_work["trade_date"],
        "symbol": symbol.upper(),
        "provider": "tushare",
        FACTOR_NAME: values[FACTOR_NAME],
        f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
    })
    return frame.loc[:, OUTPUT_COLUMNS], quality


def _validate_snapshot_manifest(manifest: dict[str, Any], *, require_fingerprint_constants: bool) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = "a_share_three_day_walkforward_campaign048_feature_snapshot"
        manifest["source_open_high_low_read"] = True
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {key: value for key, value in (manifest.get("protocol_evidence") or {}).items() if not key.startswith("campaign047_") and not key.startswith("campaign048_")}
        evidence["campaign048_mechanism_overlap_audit_sha256"] = MECHANISM_AUDIT_SHA256
        evidence["campaign048_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign048_implementation_freeze_sha256"] = IMPLEMENTATION_FREEZE_SHA256
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign048_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign048_mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign048_no_return_preregistration_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign048_implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and isinstance(manifest.get("rows"), int) and manifest["rows"] > 0
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
        raise Campaign048FeatureError("Campaign048 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256 and SNAPSHOT_DATASET_SHA256 and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign048FeatureError("Campaign048 snapshot fingerprint is not bound")


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
    }
    _generated.update(values)
    _engine_globals.update(values)


_install_engine_globals()
empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
verify_snapshot_files = _generated["verify_snapshot_files"]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    _install_engine_globals()
    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original = publication_foundation.atomic_write_json

    def write_with_truth(value: dict[str, Any], path: Path) -> None:
        if value.get("kind") == "a_share_three_day_walkforward_campaign048_feature_snapshot" and value.get("output_run_id") == OUTPUT_RUN_ID:
            value = dict(value)
            value.update({"source_open_high_low_read": True, "source_close_read": True, "source_volume_read": False, "source_amount_read": False})
        original(value, path)

    publication_foundation.atomic_write_json = write_with_truth
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original


def _load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def run_no_return_audit(*, data_root: Path, experiment_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256 or not SNAPSHOT_PUBLICATION_BINDING_SHA256:
        raise Campaign048FeatureError("bind Campaign048 snapshot and publication record before audit")
    if _sha256(DEFAULT_SNAPSHOT_BINDING) != SNAPSHOT_PUBLICATION_BINDING_SHA256:
        raise Campaign048FeatureError("Campaign048 snapshot publication binding changed")
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    _install_engine_globals()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign048FeatureError("Campaign048 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign048_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256 or _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign048FeatureError("existing Campaign048 audit is ambiguous or unbound")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, candidate49, comparison_engine = campaign044._context()
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(candidate, eligible_keys, spec, FACTOR_NAME)
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {str(item["name"]): str(item["score_direction"]) for item in gate["comparison_factors"]}
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        catalog, source_verifications = campaign044._build_source_catalog(data_root=data_root, workers=workers, verify_files=True)
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            aligned = campaign044._load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(comparison_engine._aligned_comparison_result(candidate_keys=keys, candidate_values=values, comparison_values=aligned.pop(factor), comparison=factor, direction=directions[factor], gate=gate))
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign048FeatureError("complete 66-factor catalog changed")
        _, candidate49_path, candidate49_manifest = engine._comparison_chain(data_root)
        candidate49_verification = candidate49.verify_snapshot_files(candidate49_manifest, candidate49_path, workers)
        candidate49_values = engine._load_filtered_comparison_values_explicit(candidate49_manifest, [candidate49.FACTOR_NAME], keys)[candidate49.FACTOR_NAME]
        comparisons.append(comparison_engine._aligned_comparison_result(candidate_keys=keys, candidate_values=values, comparison_values=candidate49_values, comparison=candidate49.FACTOR_NAME, direction="higher", gate=gate))
        del candidate49_values
        extra_verifications: dict[str, Any] = {}
        for label, path, expected_sha, expected_dataset, factor, module in (
            ("campaign044", C44_SNAPSHOT_PATH, C44_SNAPSHOT_SHA256, None, C44_FACTOR_NAME, campaign044),
            ("campaign045", C45_SNAPSHOT_PATH, C45_SNAPSHOT_SHA256, C45_DATASET_SHA256, C45_FACTOR_NAME, campaign045),
            ("campaign046", C46_SNAPSHOT_PATH, C46_SNAPSHOT_SHA256, C46_DATASET_SHA256, C46_FACTOR_NAME, campaign046),
            ("campaign047", C47_SNAPSHOT_PATH, C47_SNAPSHOT_SHA256, C47_DATASET_SHA256, C47_FACTOR_NAME, campaign047_reference),
        ):
            if _sha256(path) != expected_sha:
                raise Campaign048FeatureError(f"{label} snapshot manifest changed")
            source_manifest = json.loads(path.read_text(encoding="utf-8"))
            if expected_dataset is not None and source_manifest.get("dataset_sha256") != expected_dataset:
                raise Campaign048FeatureError(f"{label} snapshot dataset changed")
            extra_verifications[label] = module.verify_snapshot_files(source_manifest, path, workers)
            comparison_values = engine._load_filtered_comparison_values_explicit(source_manifest, [factor], keys)[factor]
            comparisons.append(comparison_engine._aligned_comparison_result(candidate_keys=keys, candidate_values=values, comparison_values=comparison_values, comparison=factor, direction="higher", gate=gate))
            del comparison_values
            gc.collect()
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [float(item["absolute_median_daily_rank_correlation"]) for item in comparisons if item["absolute_median_daily_rank_correlation"] is not None]
        passed = observed_order == expected_order and len(comparisons) == COMPARISON_COUNT and all(item["gate_passed"] for item in comparisons)
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order == expected_order,
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            **{f"{key}_snapshot_file_verification": value for key, value in extra_verifications.items()},
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(observed_correlations) if observed_correlations else None,
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {"comparison_values_loaded_after_coverage_pass": False, "comparisons": [], "all_required_comparisons_passed": False, "failure_reason": "coverage_gate_failed"}
    admitted = bool(coverage["gate_passed_before_comparison_values"] and uniqueness["all_required_comparisons_passed"])
    research = prior.research
    run_id = f"{research._timestamp()}_campaign048_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration" if admitted else "completed_zero_admissible_factors_stop_before_historical_returns",
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {"path": str(DEFAULT_PROTOCOL.resolve()), "sha256": PROTOCOL_SHA256},
        "candidate_snapshot": {"path": str(manifest_path), "sha256": SNAPSHOT_MANIFEST_SHA256, "dataset_sha256": SNAPSHOT_DATASET_SHA256},
        "snapshot_publication_binding": {"path": str(DEFAULT_SNAPSHOT_BINDING.resolve()), "sha256": SNAPSHOT_PUBLICATION_BINDING_SHA256},
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign048 walk-forward catalog before reading 2019-2023 returns" if admitted else "record the no-return rejection and design a genuinely new campaign",
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_close_fields_read": ["open", "high", "low", "close"],
        "minute_volume_or_amount_fields_read": [],
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
    audits = sorted(experiment_root.expanduser().resolve().glob("*_campaign048_no_return_audit.json"))
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
            command.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root, args.experiment_root)
    elif args.command == "build":
        payload = {"manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    else:
        payload = {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers))}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
