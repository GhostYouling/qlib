#!/usr/bin/env python3
"""Build and no-return audit Campaign039 return time-reversal asymmetry."""

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
    import scripts.a_share_three_day_walkforward_campaign033_features as close_base
    import scripts.a_share_three_day_walkforward_campaign038_features as campaign038
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign033_features as close_base
    import a_share_three_day_walkforward_campaign038_features as campaign038


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign033_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "ae3a523b3fdf0de128a878346b4b0368744ddc61e32e89bc94c0abe3426f70d1"
)
OLD_FACTOR = "intraday_return_spectral_entropy_59f"
FACTOR_NAME = "intraday_return_time_reversal_asymmetry_236p"
MECHANISM_AUDIT_SHA256 = (
    "a2a01837c74fa1ede9e7e3b143b3dbe8fdb11708552358aba5fa804113c4a5c6"
)
PROTOCOL_SHA256 = (
    "0cc9067d86ea2b1312d9b66bb884f9ffaee6d3b9b0b5a72d086d7962728ac105"
)

# Bind these only after immutable artifacts have been published.
SNAPSHOT_MANIFEST_SHA256 = (
    "cda070af6d700a32f5dba1c003a3a38c9921b1c75b29ac9b8a9aa4d39d169d17"
)
SNAPSHOT_DATASET_SHA256 = (
    "4d61fc2b98d2a1fc3f884668b23fcc763857926ba34abb08fab4f8ae6a3a4948"
)
NO_RETURN_AUDIT_SHA256 = "9afe7310fbcf3bd8f062ddbeb5dac7f65708d60a3e376b96ffa3b1d265226db2"

INHERITED_COMPARISON_ORDER_SHA256 = (
    "31b91c750ee06df0a862fc44b3871b159782fceea746784693c5255006df8fd3"
)
COMPARISON_ORDER_SHA256 = (
    "bfd0905b6fa58e30fc30d5618120e37b9a7edc341b947e111bb6edaab6824049"
)
SELECTED_BAR_COUNT = 240
HALF_SESSION_BAR_COUNT = 120
RETURN_COUNT = 238
ADJACENT_RETURN_PAIR_COUNT = 236
ENDPOINT_CANONICALIZATION_TOLERANCE = 1e-12
UPPER_BOUND = 1.0
FACTOR_FORMULA = (
    "For each 120-close half independently, form 119 adjacent log returns. "
    "For each of the 118 ordered adjacent-return pairs (a,b) in that half, "
    "accumulate the antisymmetric cubic contrast a^2*b-a*b^2. Pool both "
    "halves into T=sum(a^2*b-a*b^2) and "
    "Q=sum(abs(a*b)*(abs(a)+abs(b))) across exactly 236 pairs. "
    "Return abs(T)/Q."
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign039_feature_library_v1"
)

C38_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign038_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign038_feature_library_v1/snapshot_manifest.json"
)
C38_SNAPSHOT_SHA256 = (
    "d8042490037077c68c42bbf24f5b354b2a808894ac0bad79ad0c63c43404519a"
)
C38_DATASET_SHA256 = (
    "0791779f97992d3c9cd9ee6501a2eacb6df45d534f5c6b0359088221de951904"
)
C38_FACTOR_NAMES = ("intraday_half_session_chord_adherence_240m",)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign033 close-only feature runner changed")

# Clone the tested close-only partition/checkpoint/publication machinery into a
# private globals dictionary. Candidate computation and comparison audit are
# replaced below, so importing Campaign039 cannot mutate an earlier campaign.
_source = close_base._source
for _old, _new in (
    ("Campaign033", "Campaign039"),
    ("campaign033", "campaign039"),
    ("campaign_033", "campaign_039"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "fc932c2f9172d81bccb503f94d03e6407e2b807044eaab13d167f4a817289c1c",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "3e5546941b5954f96fc5a2d7dc7fbcf03b48d063ea1414133c2c17ae191fad4f",
        PROTOCOL_SHA256,
    ),
    (
        "bbd2b064885e90576712610a5b11426c3f3048fd10ff1d0590ea02861e423bd6",
        "0" * 64,
    ),
    (
        "ef76f920ab1b88dcbec40b640de240db308e60fc9711f42bb9cffbfe002e27cf",
        "0" * 64,
    ),
    (
        "f92d564c0a8f8bd32ae0a29f3879cb7c4bee85e61f9030f6ee8b635f4f5c1b35",
        "0" * 64,
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign039_features_generated",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _generated)

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_039_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_039/no_return"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
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
Campaign039FeatureError = _generated["Campaign039FeatureError"]


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
    """Validate Campaign039 and materialize its complete frozen library."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign039FeatureError("Campaign039 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign039FeatureError(
            "Campaign039 no-return protocol has a failed binding"
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
        "campaign039_delta_from_effective_campaign038_protocol"
    ) or {}
    appended = uniqueness.get("appended_comparison") or {}
    valid_range = candidate.get("valid_range") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign039_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign039_minute_candidate_comparison_daily_"
            "price_or_return_values"
        )
        and (source_chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("half_session_bar_count")
        == HALF_SESSION_BAR_COUNT
        and candidate.get("within_half_return_count") == RETURN_COUNT
        and candidate.get("within_half_adjacent_return_pair_count")
        == ADJACENT_RETURN_PAIR_COUNT
        and candidate.get("include_lunch_transition") is False
        and candidate.get("separate_half_session_pair_construction") is True
        and candidate.get("signed_return_demeaning_or_standardization") is False
        and candidate.get("cubic_contrast") == "a^2*b-a*b^2"
        and candidate.get("normalization")
        == "sum(abs(a*b)*(abs(a)+abs(b)))"
        and candidate.get("absolute_value_after_pooling_both_halves") is True
        and candidate.get("pairwise_or_separate_half_absolute_value") is False
        and candidate.get("zero_normalization_is_missing") is True
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
            "alternate_power_signed_pairwise_absolute_separate_half_clipped_"
            "winsorized_scaled_subwindow_inverse_board_or_year_search"
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
        and uniqueness.get("inherited_comparison_count") == 59
        and uniqueness.get("inherited_comparison_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and appended
        == {"name": C38_FACTOR_NAMES[0], "score_direction": "higher"}
        and uniqueness.get("comparison_factor_count") == 60
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_60_must_pass") is True
        and campaign_delta.get("candidate_factor_count") == 1
        and campaign_delta.get("comparison_factor_count") == 60
        and campaign_delta.get("development_trial_count_if_admitted") == 1
        and finite.get("trial_id")
        == "wf039_intraday_return_time_reversal_asymmetry_236p_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("external_campaign039_minute_partitions_read")
        is False
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
        and boundary.get("candidate49_ledgers_changed") is False
        and boundary.get("candidate50_activation_created") is False
        and boundary.get(
            "current_scoring_selection_sizing_or_orders_performed"
        )
        is False
    ):
        raise Campaign039FeatureError("Campaign039 no-return semantics changed")

    base_spec = campaign038.load_protocol()
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
        and len(comparisons) == 59
        and len({str(item.get("name")) for item in comparisons}) == 59
        and _comparison_order_digest(comparisons)
        == INHERITED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign039FeatureError(
            "Campaign039 inherited comparison or holding-period context changed"
        )
    comparisons.append(copy.deepcopy(appended))
    if (
        len({str(item.get("name")) for item in comparisons}) != 60
        or _comparison_order_digest(comparisons) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign039FeatureError(
            "Campaign039 complete comparison library changed"
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
            "valid_range": [0.0, UPPER_BOUND],
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
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the fixed within-half return time-reversal asymmetry."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign039FeatureError("Campaign039 close shape is invalid")
    finite = np.isfinite(closes).all(axis=1)
    positive = (closes > 0.0).all(axis=1)
    required_valid = finite & positive
    safe = np.where(np.isfinite(closes) & (closes > 0.0), closes, 1.0)

    return_parts: list[np.ndarray] = []
    left_parts: list[np.ndarray] = []
    right_parts: list[np.ndarray] = []
    for start, stop in (
        (0, HALF_SESSION_BAR_COUNT),
        (HALF_SESSION_BAR_COUNT, SELECTED_BAR_COUNT),
    ):
        with np.errstate(divide="ignore", invalid="ignore"):
            log_prices = np.log(safe[:, start:stop])
        half_returns = np.diff(log_prices, axis=1)
        return_parts.append(half_returns)
        left_parts.append(half_returns[:, :-1])
        right_parts.append(half_returns[:, 1:])
    within_half_returns = np.concatenate(return_parts, axis=1)
    pair_left = np.concatenate(left_parts, axis=1)
    pair_right = np.concatenate(right_parts, axis=1)
    if (
        within_half_returns.shape[1] != RETURN_COUNT
        or pair_left.shape[1] != ADJACENT_RETURN_PAIR_COUNT
        or pair_right.shape[1] != ADJACENT_RETURN_PAIR_COUNT
    ):
        raise Campaign039FeatureError("Campaign039 fixed support changed")

    finite_returns = np.isfinite(within_half_returns).all(axis=1)
    with np.errstate(over="ignore", invalid="ignore"):
        cubic_contrasts = pair_left * pair_right * (pair_left - pair_right)
        normalization_components = (
            np.abs(pair_left * pair_right)
            * (np.abs(pair_left) + np.abs(pair_right))
        )
        total_contrast = cubic_contrasts.sum(axis=1)
        total_normalization = normalization_components.sum(axis=1)
    finite_components = (
        finite_returns
        & np.isfinite(cubic_contrasts).all(axis=1)
        & np.isfinite(normalization_components).all(axis=1)
        & np.isfinite(total_contrast)
        & np.isfinite(total_normalization)
    )
    positive_denominator = total_normalization > 0.0
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_values = np.divide(
            np.abs(total_contrast),
            total_normalization,
            out=np.full(len(closes), np.nan, dtype=float),
            where=positive_denominator,
        )
    finite_values = np.isfinite(raw_values)
    within_tolerance = (
        (raw_values >= -ENDPOINT_CANONICALIZATION_TOLERANCE)
        & (
            raw_values
            <= UPPER_BOUND + ENDPOINT_CANONICALIZATION_TOLERANCE
        )
    )
    canonicalized = np.clip(raw_values, 0.0, UPPER_BOUND)
    eligible = (
        required_valid
        & finite_components
        & positive_denominator
        & finite_values
        & within_tolerance
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_component_rows": int(
            (required_valid & ~finite_components).sum()
        ),
        f"{FACTOR_NAME}__zero_normalization_rows": int(
            (required_valid & finite_components & ~positive_denominator).sum()
        ),
        f"{FACTOR_NAME}__within_half_return_observations": int(
            len(closes) * RETURN_COUNT
        ),
        f"{FACTOR_NAME}__adjacent_return_pair_observations": int(
            len(closes) * ADJACENT_RETURN_PAIR_COUNT
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (
                required_valid
                & finite_components
                & positive_denominator
                & finite_values
                & within_tolerance
                & ((raw_values < 0.0) | (raw_values > UPPER_BOUND))
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_components
                & positive_denominator
                & (~finite_values | ~within_tolerance)
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
    """Validate one source partition and compute time-reversal asymmetry."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign039FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign039FeatureError(
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
        raise Campaign039FeatureError(
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
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign039FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    source_counts = work.groupby(
        "trade_date", sort=True, observed=True
    ).size()
    if not source_counts.eq(241).all():
        raise Campaign039FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby(
        "trade_date", sort=True, observed=True
    )["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign039FeatureError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(
        drop=True
    )
    if not base_work["trade_date"].reset_index(drop=True).equals(
        expected_dates
    ):
        raise Campaign039FeatureError(
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
        raise Campaign039FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(closes=closes)
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
    """Apply coverage before the complete frozen 60-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign039FeatureError(
            "bind Campaign039 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign039FeatureError("Campaign039 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign039_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign039FeatureError(
                "existing Campaign039 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign039FeatureError("Campaign039 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print(
        "building Campaign039 no-price quality/listing eligibility",
        flush=True,
    )
    prior = (
        campaign038.campaign037.campaign036.campaign035.campaign034
        .campaign033.campaign032
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
        snapshot_specs.extend(
            [
                _snapshot_spec(
                    campaign=32,
                    path=campaign038.campaign037.campaign036.campaign035.campaign034.campaign033.C32_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.campaign037.campaign036.campaign035.campaign034.campaign033.C32_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.campaign037.campaign036.campaign035.campaign034.campaign033.C32_DATASET_SHA256,
                    factors=campaign038.campaign037.campaign036.campaign035.campaign034.campaign033.C32_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=33,
                    path=campaign038.campaign037.campaign036.campaign035.campaign034.C33_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.campaign037.campaign036.campaign035.campaign034.C33_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.campaign037.campaign036.campaign035.campaign034.C33_DATASET_SHA256,
                    factors=campaign038.campaign037.campaign036.campaign035.campaign034.C33_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=34,
                    path=campaign038.campaign037.campaign036.campaign035.C34_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.campaign037.campaign036.campaign035.C34_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.campaign037.campaign036.campaign035.C34_DATASET_SHA256,
                    factors=campaign038.campaign037.campaign036.campaign035.C34_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=35,
                    path=campaign038.campaign037.campaign036.C35_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.campaign037.campaign036.C35_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.campaign037.campaign036.C35_DATASET_SHA256,
                    factors=campaign038.campaign037.campaign036.C35_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=36,
                    path=campaign038.campaign037.C36_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.campaign037.C36_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.campaign037.C36_DATASET_SHA256,
                    factors=campaign038.campaign037.C36_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=37,
                    path=campaign038.C37_SNAPSHOT_PATH,
                    manifest_sha256=campaign038.C37_SNAPSHOT_SHA256,
                    dataset_sha256=campaign038.C37_DATASET_SHA256,
                    factors=campaign038.C37_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=38,
                    path=C38_SNAPSHOT_PATH,
                    manifest_sha256=C38_SNAPSHOT_SHA256,
                    dataset_sha256=C38_DATASET_SHA256,
                    factors=C38_FACTOR_NAMES,
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
            and len(comparisons) == 60
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
    run_id = f"{research._timestamp()}_campaign039_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign039_no_return_audit",
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
            "freeze the exact one-trial Campaign039 walk-forward catalog before "
            "reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_volume_amount_fields_read": [],
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
            "*_campaign039_no_return_audit.json"
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
        "minute_open_high_low_volume_amount_fields_read_by_status": [],
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

# The cloned close-only wrapper owns a second private execution namespace for
# the low-level checkpoint builder. Bind the Campaign039 callables there too;
# otherwise the build entry reaches the cloned Campaign033 protocol validator.
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
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
engine_namespace = run_no_return_audit.__globals__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and no-return audit Campaign039 feature mechanism."
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
