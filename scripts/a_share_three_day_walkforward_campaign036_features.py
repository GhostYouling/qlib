#!/usr/bin/env python3
"""Build and no-return audit Campaign036 range-frontier balance."""

from __future__ import annotations

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
    import scripts.a_share_three_day_walkforward_campaign025_features as campaign025
    import scripts.a_share_three_day_walkforward_campaign035_features as campaign035
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign025_features as campaign025
    import a_share_three_day_walkforward_campaign035_features as campaign035


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign025_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "27f79dbf8e86ae17f71a8cc1e4626b8517d8dde62aa74901a1f9447dd6c0e03d"
)
OLD_FACTOR = "intraday_extreme_arrival_order_240m"
FACTOR_NAME = "intraday_two_sided_range_frontier_balance_238m"
MECHANISM_AUDIT_SHA256 = (
    "6e926816595e4c4f8850004977e827678d0bbd63118dcc4c1c507482e4ceec14"
)
PROTOCOL_SHA256 = (
    "112fd9ad88a25622a77591e46393c340dddbdc2ff0478b9af60979702e0d88e7"
)

# Bind these only after immutable artifacts have been published.
SNAPSHOT_MANIFEST_SHA256 = (
    "5c3b1d3fa07036537acc3d8f99073cbecee03c4d58575950af09f1f80250f4d3"
)
SNAPSHOT_DATASET_SHA256 = (
    "4658449f8db54334c810faeefc63a318316c5d68462b0e4d782318172910bbdb"
)
NO_RETURN_AUDIT_SHA256 = (
    "3a4d3530a5f8ac6bf2f35008d4f0e0b15fb88b039defb5dc599c423e0c273258"
)

COMPARISON_ORDER_SHA256 = (
    "a0a67b8df0e2a9a90627df8b4b8f931fa2ac4439fbefcfd8d83da68e52373fee"
)
INHERITED_COMPARISON_ORDER_SHA256 = (
    "c15a965426251d3c3e0d2bf9dae42cd8e231529cf6620871966513e13a09d4d0"
)
SELECTED_BAR_COUNT = 240
EXPANSION_OPPORTUNITIES = 238
IDENTITY_TOLERANCE = 1e-12
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign036_feature_library_v1"
)
FACTOR_FORMULA = (
    "For each 120-bar half independently and each t=1..119, let "
    "H_prev=max(high_0..high_(t-1)), L_prev=min(low_0..low_(t-1)), "
    "u_t=max(ln(high_t/H_prev),0), and "
    "d_t=max(ln(L_prev/low_t),0). Pool both halves, set U=sum(u_t), "
    "D=sum(d_t), and return "
    "1-abs(U-D)/(U+D)=2*min(U,D)/(U+D)."
)

C35_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign035_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign035_feature_library_v1/snapshot_manifest.json"
)
C35_SNAPSHOT_SHA256 = (
    "33de221a37e0a19d3c1fffba3c8f0e64c20571581a7c72296b1a593c0acc91f4"
)
C35_DATASET_SHA256 = (
    "b557148b91a16dad9f028190723b2485f9eadd231c0aaded6b499d9dc1c68606"
)
C35_FACTOR_NAMES = ("intraday_return_weak_order_entropy_234t",)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign025 high-low feature runner changed")

# Reuse the tested high/low partition, checkpoint, and publication machinery.
# Protocol validation, candidate computation, and the complete comparison audit
# are replaced below.
_source = campaign025._source
for _old, _new in (
    ("Campaign025", "Campaign036"),
    ("campaign025", "campaign036"),
    ("campaign_025", "campaign_036"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "09fa633ffbc90e0edcb9ea4edcaeacd96fc8639577492e2c9e40ed2c90dad62f",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "008d83fcb047601b99a74e6810d58eb26524bb6ebc08add230f4525eb7884904",
        PROTOCOL_SHA256,
    ),
    (
        "4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "e67df10a429b902246450823ea7cb9645e88a8b027ab97965afca6029989b238",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign036_features_generated",
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign025.engine_namespace[_key]
for _suffix in (
    "SNAPSHOT_PATH",
    "SNAPSHOT_SHA256",
    "DATASET_SHA256",
    "FACTOR_NAMES",
    "OUTPUT_COLUMNS",
):
    _key = f"C24_{_suffix}"
    _generated[_key] = campaign025.engine_namespace[_key]
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _generated)

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_036_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_036/no_return"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
BASE_COLUMNS = _generated["BASE_COLUMNS"]
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
market = _generated["market"]
Campaign036FeatureError = _generated["Campaign036FeatureError"]


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    values = [
        (str(item["name"]), str(item["score_direction"]))
        for item in comparisons
    ]
    payload = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate Campaign036 and materialize its complete frozen library."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign036FeatureError("Campaign036 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign036FeatureError(
            "Campaign036 no-return protocol has a failed binding"
        )
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    source_chain = delta.get("source_chain") or {}
    campaign_delta = delta.get(
        "campaign036_delta_from_effective_campaign035_protocol"
    ) or {}
    appended = uniqueness.get("appended_comparison") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign036_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign036_minute_candidate_comparison_daily_"
            "price_or_return_values"
        )
        and (source_chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "close", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_expansion_opportunity_count")
        == EXPANSION_OPPORTUNITIES
        and candidate.get("running_frontier_reset_each_half") is True
        and candidate.get("include_lunch_transition") is False
        and candidate.get("expansion_distance")
        == "natural_log_boundary_ratio"
        and candidate.get("inside_or_equal_boundary_contribution") == 0.0
        and candidate.get("pool_before_balance") is True
        and candidate.get("balance_transform") == "1-abs(U-D)/(U+D)"
        and candidate.get("identity_check_tolerance") == IDENTITY_TOLERANCE
        and candidate.get("zero_total_expansion_is_missing") is True
        and candidate.get("valid_range") == [0.0, 1.0]
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "event_count_arithmetic_distance_per_half_average_activity_weight_"
            "subwindow_board_or_year_search"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_comparison_count") == 56
        and uniqueness.get("inherited_comparison_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and appended
        == {"name": C35_FACTOR_NAMES[0], "score_direction": "higher"}
        and uniqueness.get("comparison_factor_count") == 57
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_57_must_pass") is True
        and campaign_delta.get("candidate_factor_count") == 1
        and campaign_delta.get("comparison_factor_count") == 57
        and campaign_delta.get("development_trial_count_if_admitted") == 1
        and finite.get("trial_id")
        == "wf036_intraday_two_sided_range_frontier_balance_238m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("external_campaign036_minute_partitions_read") is False
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("training_or_model_fitting_performed") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get(
            "candidate49_historical_return_signal_or_execution_backfill_performed"
        )
        is False
        and boundary.get("candidate50_activation_created") is False
        and boundary.get(
            "current_scoring_selection_sizing_or_orders_performed"
        )
        is False
    ):
        raise Campaign036FeatureError("Campaign036 no-return semantics changed")

    base_spec = campaign035.load_protocol()
    base_gates = base_spec.get("ordered_no_return_gates") or {}
    base_coverage = base_gates.get(
        "coverage_and_capacity_before_comparison_values"
    ) or {}
    base_uniqueness = base_gates.get("uniqueness_after_coverage_only") or {}
    comparisons = copy.deepcopy(
        list(base_uniqueness.get("comparison_factors") or [])
    )
    if not (
        base_coverage.get("holding_period_sessions") == 3
        and len(comparisons) == 56
        and len({str(item.get("name")) for item in comparisons}) == 56
        and _comparison_order_digest(comparisons)
        == INHERITED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign036FeatureError(
            "Campaign036 inherited comparison or holding-period context changed"
        )
    comparisons.append(copy.deepcopy(appended))
    if (
        len({str(item.get("name")) for item in comparisons}) != 57
        or _comparison_order_digest(comparisons) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign036FeatureError(
            "Campaign036 complete comparison library changed"
        )

    runtime_coverage = copy.deepcopy(coverage)
    runtime_coverage["holding_period_sessions"] = 3
    runtime_uniqueness = copy.deepcopy(uniqueness)
    runtime_uniqueness["comparison_factors"] = comparisons
    spec = copy.deepcopy(base_spec)
    spec["version"] = 1
    spec["kind"] = delta["kind"]
    spec["status"] = delta["status"]
    spec["candidates"] = [
        {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "source_fields_allowed": list(RAW_COLUMNS),
            "source_fields_used_by_formula": list(RAW_COLUMNS),
            "selected_bar_count": SELECTED_BAR_COUNT,
            "valid_range": [0.0, 1.0],
        }
    ]
    spec["ordered_no_return_gates"] = {
        "coverage_and_capacity_before_comparison_values": runtime_coverage,
        "uniqueness_after_coverage_only": runtime_uniqueness,
    }
    spec["finite_post_admissibility_search"] = {
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
            "start": finite["development_interval"][0],
            "end": finite["development_interval"][1],
            "folds": copy.deepcopy(
                (base_spec.get("finite_post_admissibility_search") or {})
                .get("development_interval", {})
                .get("folds", [])
            ),
            "purge_local_signal_sessions": 3,
        },
    }
    return spec


def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute pooled within-half two-sided running-frontier balance."""

    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign036FeatureError(
            "Campaign036 aligned high-low shapes are invalid"
        )
    finite = np.isfinite(highs).all(axis=1) & np.isfinite(lows).all(axis=1)
    positive = (highs > 0.0).all(axis=1) & (lows > 0.0).all(axis=1)
    ordered = (lows <= highs).all(axis=1)
    required_valid = finite & positive & ordered
    safe_highs = np.where(np.isfinite(highs) & (highs > 0.0), highs, 1.0)
    safe_lows = np.where(np.isfinite(lows) & (lows > 0.0), lows, 1.0)

    up_parts: list[np.ndarray] = []
    down_parts: list[np.ndarray] = []
    for start, stop in ((0, 120), (120, 240)):
        half_high = safe_highs[:, start:stop]
        half_low = safe_lows[:, start:stop]
        prior_high = np.maximum.accumulate(half_high, axis=1)[:, :-1]
        prior_low = np.minimum.accumulate(half_low, axis=1)[:, :-1]
        with np.errstate(divide="ignore", invalid="ignore"):
            up_parts.append(
                np.maximum(np.log(half_high[:, 1:] / prior_high), 0.0)
            )
            down_parts.append(
                np.maximum(np.log(prior_low / half_low[:, 1:]), 0.0)
            )
    up = np.concatenate(up_parts, axis=1)
    down = np.concatenate(down_parts, axis=1)
    if up.shape[1] != EXPANSION_OPPORTUNITIES or down.shape != up.shape:
        raise Campaign036FeatureError(
            "Campaign036 expansion opportunity support changed"
        )
    finite_expansion = np.isfinite(up).all(axis=1) & np.isfinite(down).all(
        axis=1
    )
    upward_total = up.sum(axis=1)
    downward_total = down.sum(axis=1)
    total = upward_total + downward_total
    positive_total = total > 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.divide(
            total - np.abs(upward_total - downward_total),
            total,
            out=np.full(len(highs), np.nan, dtype=float),
            where=positive_total,
        )
        identity = np.divide(
            2.0 * np.minimum(upward_total, downward_total),
            total,
            out=np.full(len(highs), np.nan, dtype=float),
            where=positive_total,
        )
    identity_valid = (
        np.isfinite(values)
        & np.isfinite(identity)
        & (np.abs(values - identity) <= IDENTITY_TOLERANCE)
    )
    finite_values = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = (
        required_valid
        & finite_expansion
        & positive_total
        & identity_valid
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_high_low_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_high_low_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_expansion_rows": int(
            (required_valid & ~finite_expansion).sum()
        ),
        f"{FACTOR_NAME}__zero_total_expansion_rows": int(
            (required_valid & finite_expansion & ~positive_total).sum()
        ),
        f"{FACTOR_NAME}__upward_expansion_observations": int((up > 0.0).sum()),
        f"{FACTOR_NAME}__downward_expansion_observations": int(
            (down > 0.0).sum()
        ),
        f"{FACTOR_NAME}__identity_mismatch_rows": int(
            (
                required_valid
                & finite_expansion
                & positive_total
                & ~identity_valid
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_expansion
                & positive_total
                & identity_valid
                & (~finite_values | ~in_range)
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
    """Validate one source partition and compute range-frontier balance."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign036FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign036FeatureError(
            f"unexpected joint-base columns for {symbol}: "
            f"{tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return _generated["empty_output_frame"](), {"base_rows": 0}
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign036FeatureError(
            f"joint-base identity changed for {symbol}"
        )
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("high", "low"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign036FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    source_counts = work.groupby(
        "trade_date", sort=True, observed=True
    ).size()
    if not source_counts.eq(241).all():
        raise Campaign036FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby(
        "trade_date", sort=True, observed=True
    )["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign036FeatureError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(
        drop=True
    )
    if not base_work["trade_date"].reset_index(drop=True).equals(
        expected_dates
    ):
        raise Campaign036FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "high", "low"],
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
        raise Campaign036FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    highs = continuous["high"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    lows = continuous["low"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(
        highs=highs,
        lows=lows,
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


def _snapshot_spec(
    *,
    campaign: int,
    path: Path,
    manifest_sha256: str,
    dataset_sha256: str,
    factors: tuple[str, ...],
) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    output_columns = ["trade_date", "symbol", "provider"]
    for factor in factors:
        output_columns.extend([factor, f"{factor}_eligible"])
    return {
        "campaign": campaign,
        "path": path,
        "sha256": manifest_sha256,
        "dataset_sha256": dataset_sha256,
        "kind": str(manifest.get("kind") or ""),
        "all_factors": factors,
        "output_columns": tuple(output_columns),
        "selected": factors,
    }


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before the complete frozen 57-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign036FeatureError(
            "bind Campaign036 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign036FeatureError("Campaign036 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign036_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign036FeatureError(
                "existing Campaign036 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign036FeatureError("Campaign036 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print(
        "building Campaign036 no-price quality/listing eligibility",
        flush=True,
    )
    foundation = campaign035.campaign034.campaign033.campaign032.foundation
    engine = campaign035.campaign034.campaign033.campaign032.engine
    eligible_keys = foundation.quality_listing_eligible_keys(
        campaign035.campaign034.campaign033.campaign032.load_protocol()
    )
    candidate = engine.load_factor_frame(
        manifest_path,
        manifest,
        FACTOR_NAME,
    )
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        expected_order = [
            str(item["name"]) for item in gate["comparison_factors"]
        ]
        keys, values = engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
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
        snapshot_specs = []
        for prior_spec in (
            campaign035.campaign034.campaign033.campaign032
            ._snapshot_specs_from_campaign031()
        ):
            selected = tuple(
                factor
                for factor in prior_spec["all_factors"]
                if factor in expected_order
            )
            snapshot_specs.append({**prior_spec, "selected": selected})
        snapshot_specs.extend(
            [
                _snapshot_spec(
                    campaign=32,
                    path=campaign035.campaign034.campaign033.C32_SNAPSHOT_PATH,
                    manifest_sha256=(
                        campaign035.campaign034.campaign033.C32_SNAPSHOT_SHA256
                    ),
                    dataset_sha256=(
                        campaign035.campaign034.campaign033.C32_DATASET_SHA256
                    ),
                    factors=campaign035.campaign034.campaign033.C32_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=33,
                    path=campaign035.campaign034.C33_SNAPSHOT_PATH,
                    manifest_sha256=campaign035.campaign034.C33_SNAPSHOT_SHA256,
                    dataset_sha256=campaign035.campaign034.C33_DATASET_SHA256,
                    factors=campaign035.campaign034.C33_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=34,
                    path=campaign035.C34_SNAPSHOT_PATH,
                    manifest_sha256=campaign035.C34_SNAPSHOT_SHA256,
                    dataset_sha256=campaign035.C34_DATASET_SHA256,
                    factors=campaign035.C34_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=35,
                    path=C35_SNAPSHOT_PATH,
                    manifest_sha256=C35_SNAPSHOT_SHA256,
                    dataset_sha256=C35_DATASET_SHA256,
                    factors=C35_FACTOR_NAMES,
                ),
            ]
        )
        snapshot_verifications: dict[str, Any] = {}
        executor = (
            campaign035.campaign034.campaign033.campaign032.executor
        )
        for prior_spec in snapshot_specs:
            campaign_number = int(prior_spec["campaign"])
            prior_manifest, prior_verification = executor._verify_prior_snapshot(
                path=prior_spec["path"],
                manifest_sha256=prior_spec["sha256"],
                dataset_sha256=prior_spec["dataset_sha256"],
                kind=prior_spec["kind"],
                factor_names=prior_spec["all_factors"],
                output_columns=prior_spec["output_columns"],
                workers=workers,
            )
            selected = tuple(prior_spec["selected"])
            if selected:
                comparisons.extend(
                    executor._prior_comparisons(
                        candidate_keys=keys,
                        candidate_values=values,
                        manifest=prior_manifest,
                        factors=selected,
                        gate=gate,
                    )
                )
            snapshot_verifications[
                f"campaign{campaign_number:03d}"
            ] = prior_verification
        observed_order = [
            str(item["comparison_factor"]) for item in comparisons
        ]
        observed = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == 57
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": (
                observed_order == expected_order
            ),
            "pre_campaign004_comparison_count": 25,
            "post_campaign003_snapshot_verification": snapshot_verifications,
            "prior_snapshot_file_verification": frozen_verifications,
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
    research = campaign035.campaign034.campaign033.campaign032.research
    run_id = f"{research._timestamp()}_campaign036_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign036_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
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
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign036 walk-forward catalog before "
            "reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_volume_amount_fields_read": ["high", "low"],
        "market_quarterly_or_event_fields_read": [],
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
            "*_campaign036_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "minute_open_high_low_volume_amount_fields_read_by_status": [
            "high",
            "low",
        ],
        "market_quarterly_or_event_fields_read_by_status": [],
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


_generated["DEFAULT_PROTOCOL"] = DEFAULT_PROTOCOL
_generated["DEFAULT_EXPERIMENT_ROOT"] = DEFAULT_EXPERIMENT_ROOT
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["FACTOR_NAME"] = FACTOR_NAME
_generated["FACTOR_NAMES"] = FACTOR_NAMES
_generated["FACTOR_DIRECTIONS"] = FACTOR_DIRECTIONS
_generated["FACTOR_RANGES"] = FACTOR_RANGES
_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["FACTOR_FORMULAS"] = FACTOR_FORMULAS
_generated["OUTPUT_COLUMNS"] = OUTPUT_COLUMNS
_generated["OUTPUT_RUN_ID"] = OUTPUT_RUN_ID
_generated["PROTOCOL_SHA256"] = PROTOCOL_SHA256
_generated["SNAPSHOT_MANIFEST_SHA256"] = SNAPSHOT_MANIFEST_SHA256
_generated["SNAPSHOT_DATASET_SHA256"] = SNAPSHOT_DATASET_SHA256
_generated["NO_RETURN_AUDIT_SHA256"] = NO_RETURN_AUDIT_SHA256
_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["compute_partition_frame"] = compute_partition_frame
_generated["run_no_return_audit"] = run_no_return_audit
_generated["status"] = status

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
parser = _generated["parser"]
main = _generated["main"]
engine_namespace = run_no_return_audit.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
