#!/usr/bin/env python3
"""Build and no-return audit Campaign041 intraday microgap absorption."""

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
    import scripts.a_share_three_day_walkforward_campaign040_features as campaign040
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign040_features as campaign040


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign040_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "dd96f564d60853b6c51a31912f2cc5537e699d5b1a93516748124a06da9e43f0"
)
OLD_FACTOR = "intraday_morning_afternoon_range_profile_similarity_120b"
FACTOR_NAME = "intraday_microgap_absorption_share_238p"
MECHANISM_AUDIT_SHA256 = (
    "2eee8a371218fe931274c577365c0ad3c1d9d0374665321791477ac9e422a3ba"
)
PROTOCOL_SHA256 = (
    "6691fb6a382d6f2f481473f25a0060606edf59290bc822b635b23de25105ae7c"
)

# Bind these only after immutable artifacts have been published.
SNAPSHOT_MANIFEST_SHA256 = (
    "838f71169e90d33e9ebbfd34d62dd2c4969432454eeaa69ae6601bb6fdc95391"
)
SNAPSHOT_DATASET_SHA256 = (
    "d330e806262d5e3187649273aea14bb20e53d13cc18edfbc8d8dd0616aa0ac0b"
)
NO_RETURN_AUDIT_SHA256 = (
    "fe00c12d6cb1ebfbb0c7eb31e7f43e188f845ae41a4efff5ebbc9d7230fcf52b"
)

INHERITED_COMPARISON_ORDER_SHA256 = (
    "1a4adb3be52af565306ddbb08dade8643c6c63e926772ada6ab8c6c3f9817a9e"
)
COMPARISON_ORDER_SHA256 = (
    "16ea65e40e50d1ef04f967da6f98aa077791bcd1680fab78d2cf28d0509713d8"
)
SELECTED_BAR_COUNT = 240
FIXED_TRANSITION_COUNT = 238
MINIMUM_INFORMATIVE_GAPS = 30
ENDPOINT_CANONICALIZATION_TOLERANCE = 1e-12
UPPER_BOUND = 1.0
FACTOR_FORMULA = (
    "Across the 119 adjacent transitions inside each 120-bar half session, "
    "let g_t=log(open_t/close_(t-1)). A transition is informative only "
    "when g_t is exactly nonzero. An informative transition is absorbed "
    "when low_t <= close_(t-1) <= high_t. Return "
    "absorbed_informative_transition_count / informative_transition_count."
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign041_feature_library_v1"
)

C40_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign040_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign040_feature_library_v1/snapshot_manifest.json"
)
C40_SNAPSHOT_SHA256 = (
    "9830dc3dc4f5ceb86f6983c1353bd52c3b6c87eeb206f433b10c19adc7d82f40"
)
C40_DATASET_SHA256 = (
    "9b7443611ce0da082aa31fb88d4b001c0d7231639112e15fd9645d7ede46dee8"
)
C40_FACTOR_NAMES = (OLD_FACTOR,)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign040 feature runner changed")

# Clone the tested partition/checkpoint/publication machinery into a private
# namespace. Candidate computation and comparison audit are replaced below.
_source = campaign040._source
for _old, _new in (
    ("Campaign040", "Campaign041"),
    ("campaign040", "campaign041"),
    ("campaign_040", "campaign_041"),
    (OLD_FACTOR, FACTOR_NAME),
    (campaign040.MECHANISM_AUDIT_SHA256, MECHANISM_AUDIT_SHA256),
    (campaign040.PROTOCOL_SHA256, PROTOCOL_SHA256),
    (campaign040.SNAPSHOT_MANIFEST_SHA256, "0" * 64),
    (campaign040.SNAPSHOT_DATASET_SHA256, "0" * 64),
    (campaign040.NO_RETURN_AUDIT_SHA256, "0" * 64),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign041_features_generated",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _generated)

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_041_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_041/no_return"
)
RAW_COLUMNS = (
    "datetime",
    "symbol",
    "provider",
    "open",
    "high",
    "low",
    "close",
)
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
FACTOR_RANGES = {FACTOR_NAME: (0.0, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
market = _generated["market"]
Campaign041FeatureError = _generated["Campaign041FeatureError"]


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
    """Validate Campaign041 and materialize its complete frozen library."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign041FeatureError("Campaign041 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign041FeatureError(
            "Campaign041 no-return protocol has a failed binding"
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
        "campaign041_delta_from_effective_campaign040_protocol"
    ) or {}
    appended = uniqueness.get("appended_comparison") or {}
    valid_range = candidate.get("valid_range") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign041_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign041_minute_candidate_comparison_daily_"
            "price_or_return_values"
        )
        and (source_chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("fixed_transition_count") == FIXED_TRANSITION_COUNT
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get(
            "exact_zero_gap_excluded_from_numerator_and_denominator"
        )
        is True
        and candidate.get("minimum_informative_nonzero_gaps")
        == MINIMUM_INFORMATIVE_GAPS
        and candidate.get("absorption_interval_is_closed") is True
        and candidate.get(
            "all_240_bars_must_pass_exact_positive_finite_ohlc_ordering"
        )
        is True
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_CANONICALIZATION_TOLERANCE
        and valid_range
        == {
            "lower": 0.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "gap_weight_sign_split_entropy_zero_gap_credit_lunch_overnight_"
            "inverse_board_year_cost_or_model_search"
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
        and uniqueness.get("inherited_comparison_count") == 61
        and uniqueness.get("inherited_comparison_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and appended
        == {"name": OLD_FACTOR, "score_direction": "higher"}
        and uniqueness.get("comparison_factor_count") == 62
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_62_must_pass") is True
        and campaign_delta.get("comparison_factor_count") == 62
        and campaign_delta.get("comparison_order_sha256")
        == COMPARISON_ORDER_SHA256
        and finite.get("trial_id")
        == "wf041_intraday_microgap_absorption_share_238p_single_higher"
        and finite.get("kind") == "single_factor"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("development_interval")
        == ["2019-01-01", "2023-12-31"]
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("candidate49_ledgers_changed") is False
        and boundary.get("candidate50_activation_created") is False
    ):
        raise Campaign041FeatureError("Campaign041 protocol semantics changed")

    base_spec = campaign040.load_protocol()
    comparisons = copy.deepcopy(
        base_spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]["comparison_factors"]
    )
    if (
        len(comparisons) != 61
        or _comparison_order_digest(comparisons)
        != INHERITED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign041FeatureError(
            "Campaign041 inherited comparison library changed"
        )
    comparisons.append(copy.deepcopy(appended))
    if (
        len(comparisons) != 62
        or len({item["name"] for item in comparisons}) != 62
        or _comparison_order_digest(comparisons) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign041FeatureError(
            "Campaign041 complete comparison library changed"
        )

    spec = copy.deepcopy(base_spec)
    spec["kind"] = delta["kind"]
    spec["status"] = delta["status"]
    spec["frozen_at"] = delta["frozen_at"]
    spec["purpose"] = delta["purpose"]
    spec["source_chain"] = copy.deepcopy(source_chain)
    spec["candidates"] = [
        {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "source_fields_allowed": list(RAW_COLUMNS),
            "source_fields_used_by_formula": list(RAW_COLUMNS),
            "selected_bar_count": SELECTED_BAR_COUNT,
            "fixed_transition_count": FIXED_TRANSITION_COUNT,
            "minimum_informative_nonzero_gaps": MINIMUM_INFORMATIVE_GAPS,
            "valid_range": [0.0, UPPER_BOUND],
        }
    ]
    spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ] = {
        **copy.deepcopy(coverage),
        "holding_period_sessions": 3,
    }
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"] = {
        **copy.deepcopy(uniqueness),
        "comparison_factors": comparisons,
    }
    inherited_search = copy.deepcopy(
        base_spec.get("finite_post_admissibility_search") or {}
    )
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
                (inherited_search.get("development_interval") or {}).get(
                    "folds", []
                )
            ),
            "purge_local_signal_sessions": 3,
        },
    }
    return spec


def compute_factor_values(
    *,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the fixed nonzero microgap same-minute absorption share."""

    arrays = [
        np.asarray(values, dtype=float)
        for values in (opens, highs, lows, closes)
    ]
    if any(
        values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT
        for values in arrays
    ) or len({values.shape for values in arrays}) != 1:
        raise Campaign041FeatureError("Campaign041 OHLC shape is invalid")
    opens, highs, lows, closes = arrays

    finite = (
        np.isfinite(opens).all(axis=1)
        & np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & np.isfinite(closes).all(axis=1)
    )
    positive = (
        (opens > 0.0).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (closes > 0.0).all(axis=1)
    )
    ordered = (
        (lows <= opens).all(axis=1)
        & (opens <= highs).all(axis=1)
        & (lows <= closes).all(axis=1)
        & (closes <= highs).all(axis=1)
    )
    required_valid = finite & positive & ordered

    previous_indices = np.concatenate(
        (np.arange(0, 119), np.arange(120, 239))
    )
    current_indices = previous_indices + 1
    previous_closes = closes[:, previous_indices]
    current_opens = opens[:, current_indices]
    current_highs = highs[:, current_indices]
    current_lows = lows[:, current_indices]
    safe_previous = np.where(
        np.isfinite(previous_closes) & (previous_closes > 0.0),
        previous_closes,
        1.0,
    )
    safe_open = np.where(
        np.isfinite(current_opens) & (current_opens > 0.0),
        current_opens,
        1.0,
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        gaps = np.log(safe_open / safe_previous)
    finite_gaps = np.isfinite(gaps).all(axis=1)
    informative = gaps != 0.0
    informative_count = informative.sum(axis=1)
    absorbed = (
        informative
        & (current_lows <= previous_closes)
        & (previous_closes <= current_highs)
    )
    absorbed_count = absorbed.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw_values = np.divide(
            absorbed_count.astype(float),
            informative_count.astype(float),
            out=np.full(len(opens), np.nan, dtype=float),
            where=informative_count > 0,
        )
    finite_score = np.isfinite(raw_values)
    within_tolerance = (
        (raw_values >= -ENDPOINT_CANONICALIZATION_TOLERANCE)
        & (
            raw_values
            <= UPPER_BOUND + ENDPOINT_CANONICALIZATION_TOLERANCE
        )
    )
    canonicalized = np.clip(raw_values, 0.0, UPPER_BOUND)
    sufficient = informative_count >= MINIMUM_INFORMATIVE_GAPS
    eligible = (
        required_valid
        & finite_gaps
        & sufficient
        & finite_score
        & within_tolerance
    )
    quality = {
        "base_rows": int(len(opens)),
        "invalid_required_ohlc_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_ohlc_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_ohlc_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_gap_rows": int(
            (required_valid & ~finite_gaps).sum()
        ),
        f"{FACTOR_NAME}__fixed_transition_observations": int(
            len(opens) * FIXED_TRANSITION_COUNT
        ),
        f"{FACTOR_NAME}__informative_nonzero_gap_observations": int(
            informative[required_valid & finite_gaps].sum()
        ),
        f"{FACTOR_NAME}__absorbed_informative_gap_observations": int(
            absorbed[required_valid & finite_gaps].sum()
        ),
        f"{FACTOR_NAME}__insufficient_informative_gap_rows": int(
            (required_valid & finite_gaps & ~sufficient).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (
                required_valid
                & finite_gaps
                & sufficient
                & finite_score
                & within_tolerance
                & ((raw_values < 0.0) | (raw_values > UPPER_BOUND))
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_gaps
                & sufficient
                & (~finite_score | ~within_tolerance)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, canonicalized, np.nan)},
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
    """Validate one source partition and compute microgap absorption."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign041FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign041FeatureError(
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
        raise Campaign041FeatureError(
            f"joint-base identity changed for {symbol}"
        )
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("open", "high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign041FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    source_counts = work.groupby(
        "trade_date", sort=True, observed=True
    ).size()
    if not source_counts.eq(241).all():
        raise Campaign041FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby(
        "trade_date", sort=True, observed=True
    )["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign041FeatureError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(
        drop=True
    )
    if not base_work["trade_date"].reset_index(drop=True).equals(
        expected_dates
    ):
        raise Campaign041FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "open", "high", "low", "close"],
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
        raise Campaign041FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    shaped = {
        column: continuous[column].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for column in ("open", "high", "low", "close")
    }
    values, eligible, quality = compute_factor_values(
        opens=shaped["open"],
        highs=shaped["high"],
        lows=shaped["low"],
        closes=shaped["close"],
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
    """Apply coverage before the complete frozen 62-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign041FeatureError(
            "bind Campaign041 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign041FeatureError("Campaign041 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign041_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign041FeatureError(
                "existing Campaign041 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign041FeatureError("Campaign041 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print(
        "building Campaign041 no-price quality/listing eligibility",
        flush=True,
    )
    prior = (
        campaign040.campaign039.campaign038.campaign037.campaign036
        .campaign035.campaign034.campaign033.campaign032
    )
    foundation = prior.foundation
    engine = prior.engine
    eligible_keys = foundation.quality_listing_eligible_keys(
        prior.load_protocol()
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
        for prior_spec in prior._snapshot_specs_from_campaign031():
            selected = tuple(
                factor
                for factor in prior_spec["all_factors"]
                if factor in expected_order
            )
            snapshot_specs.append({**prior_spec, "selected": selected})
        c38 = campaign040.campaign039.campaign038
        snapshot_specs.extend(
            [
                _snapshot_spec(
                    campaign=32,
                    path=c38.campaign037.campaign036.campaign035.campaign034.campaign033.C32_SNAPSHOT_PATH,
                    manifest_sha256=c38.campaign037.campaign036.campaign035.campaign034.campaign033.C32_SNAPSHOT_SHA256,
                    dataset_sha256=c38.campaign037.campaign036.campaign035.campaign034.campaign033.C32_DATASET_SHA256,
                    factors=c38.campaign037.campaign036.campaign035.campaign034.campaign033.C32_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=33,
                    path=c38.campaign037.campaign036.campaign035.campaign034.C33_SNAPSHOT_PATH,
                    manifest_sha256=c38.campaign037.campaign036.campaign035.campaign034.C33_SNAPSHOT_SHA256,
                    dataset_sha256=c38.campaign037.campaign036.campaign035.campaign034.C33_DATASET_SHA256,
                    factors=c38.campaign037.campaign036.campaign035.campaign034.C33_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=34,
                    path=c38.campaign037.campaign036.campaign035.C34_SNAPSHOT_PATH,
                    manifest_sha256=c38.campaign037.campaign036.campaign035.C34_SNAPSHOT_SHA256,
                    dataset_sha256=c38.campaign037.campaign036.campaign035.C34_DATASET_SHA256,
                    factors=c38.campaign037.campaign036.campaign035.C34_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=35,
                    path=c38.campaign037.campaign036.C35_SNAPSHOT_PATH,
                    manifest_sha256=c38.campaign037.campaign036.C35_SNAPSHOT_SHA256,
                    dataset_sha256=c38.campaign037.campaign036.C35_DATASET_SHA256,
                    factors=c38.campaign037.campaign036.C35_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=36,
                    path=c38.campaign037.C36_SNAPSHOT_PATH,
                    manifest_sha256=c38.campaign037.C36_SNAPSHOT_SHA256,
                    dataset_sha256=c38.campaign037.C36_DATASET_SHA256,
                    factors=c38.campaign037.C36_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=37,
                    path=c38.C37_SNAPSHOT_PATH,
                    manifest_sha256=c38.C37_SNAPSHOT_SHA256,
                    dataset_sha256=c38.C37_DATASET_SHA256,
                    factors=c38.C37_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=38,
                    path=campaign040.campaign039.C38_SNAPSHOT_PATH,
                    manifest_sha256=campaign040.campaign039.C38_SNAPSHOT_SHA256,
                    dataset_sha256=campaign040.campaign039.C38_DATASET_SHA256,
                    factors=campaign040.campaign039.C38_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=39,
                    path=campaign040.C39_SNAPSHOT_PATH,
                    manifest_sha256=campaign040.C39_SNAPSHOT_SHA256,
                    dataset_sha256=campaign040.C39_DATASET_SHA256,
                    factors=campaign040.C39_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=40,
                    path=C40_SNAPSHOT_PATH,
                    manifest_sha256=C40_SNAPSHOT_SHA256,
                    dataset_sha256=C40_DATASET_SHA256,
                    factors=C40_FACTOR_NAMES,
                ),
            ]
        )
        snapshot_verifications: dict[str, Any] = {}
        executor = prior.executor
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
            and len(comparisons) == 62
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
    research = prior.research
    run_id = f"{research._timestamp()}_campaign041_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign041_no_return_audit",
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
            "freeze the exact one-trial Campaign041 walk-forward catalog before "
            "reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_close_fields_read": [
            "open",
            "high",
            "low",
            "close",
        ],
        "minute_volume_or_amount_fields_read": [],
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
            "*_campaign041_no_return_audit.json"
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
        "minute_open_high_low_close_fields_read_by_status": [
            "open",
            "high",
            "low",
            "close",
        ],
        "minute_volume_or_amount_fields_read_by_status": [],
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

_engine_globals = _generated["_generated"]
for _key in (
    "DEFAULT_PROTOCOL",
    "DEFAULT_EXPERIMENT_ROOT",
    "RAW_COLUMNS",
    "FACTOR_NAME",
    "FACTOR_NAMES",
    "FACTOR_DIRECTIONS",
    "FACTOR_RANGES",
    "FACTOR_FORMULA",
    "FACTOR_FORMULAS",
    "OUTPUT_COLUMNS",
    "OUTPUT_RUN_ID",
    "PROTOCOL_SHA256",
    "SNAPSHOT_MANIFEST_SHA256",
    "SNAPSHOT_DATASET_SHA256",
    "NO_RETURN_AUDIT_SHA256",
    "load_protocol",
    "compute_factor_values",
    "compute_partition_frame",
    "run_no_return_audit",
    "status",
):
    _engine_globals[_key] = _generated[_key]

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
_inherited_build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_inherited_validate_snapshot_manifest = _generated[
    "_validate_snapshot_manifest"
]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Publish C41 with truthful OHLC-only aggregate source metadata."""

    publication_foundation = _inherited_build_snapshot.__globals__["foundation"]
    original_atomic_write_json = publication_foundation.atomic_write_json

    def campaign041_atomic_write_json(
        value: dict[str, Any],
        path: Path,
    ) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign041_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value["source_open_high_low_read"] = True
            value["source_close_read"] = True
            value["source_volume_read"] = False
            value["source_amount_read"] = False
        original_atomic_write_json(value, path)

    publication_foundation.atomic_write_json = campaign041_atomic_write_json
    try:
        return _inherited_build_snapshot(
            data_root=data_root,
            workers=workers,
        )
    finally:
        publication_foundation.atomic_write_json = original_atomic_write_json


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    """Validate truthful C41 source flags through the inherited schema."""

    if not require_fingerprint_constants:
        manifest["source_open_high_low_read"] = True
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
    if not (
        manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
    ):
        raise Campaign041FeatureError(
            "Campaign041 snapshot source-field metadata changed"
        )
    compatible = copy.deepcopy(manifest)
    compatible["source_open_high_low_read"] = False
    compatible["source_close_read"] = True
    compatible["source_volume_read"] = not require_fingerprint_constants
    _inherited_validate_snapshot_manifest(
        compatible,
        require_fingerprint_constants=require_fingerprint_constants,
    )


_generated["_validate_snapshot_manifest"] = _validate_snapshot_manifest
_engine_globals["_validate_snapshot_manifest"] = _validate_snapshot_manifest
_generated["build_snapshot"] = build_snapshot
_engine_globals["build_snapshot"] = build_snapshot
engine_namespace = run_no_return_audit.__globals__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and no-return audit Campaign041 feature mechanism."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "audit"):
        child = subparsers.add_parser(name)
        child.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        child.add_argument(
            "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
        )
        child.add_argument("--workers", type=int, default=4)
    child = subparsers.add_parser("status")
    child.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    child.add_argument(
        "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "build":
        path = build_snapshot(
            data_root=args.data_root,
            workers=args.workers,
        )
        print(json.dumps({"snapshot_manifest": str(path)}, sort_keys=True))
        return 0
    if args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
        print(json.dumps({"no_return_audit": str(path)}, sort_keys=True))
        return 0
    print(
        json.dumps(
            status(args.data_root, args.experiment_root),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
