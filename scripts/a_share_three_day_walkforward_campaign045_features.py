#!/usr/bin/env python3
"""Build and no-return audit Campaign045 volatility/activity lead-lag asymmetry."""

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
    import scripts.a_share_three_day_walkforward_campaign043_features as campaign043
    import scripts.a_share_three_day_walkforward_campaign044_features as campaign044
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign043_features as campaign043
    import a_share_three_day_walkforward_campaign044_features as campaign044


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign043_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "2eacbed96bdebfa99b65a1feb7052c466f68db331c9df4467081f4017eaf4f60"
)
OLD_FACTOR = "intraday_transaction_vwap_consensus_240m"
FACTOR_NAME = "intraday_volatility_activity_lead_lag_asymmetry_236p"
MECHANISM_AUDIT_SHA256 = (
    "c6f5f8b9a19e2867deca7d1c4fbdbdbd565ebb8d1cf4eb5df6d3587205ebb83e"
)
PROTOCOL_SHA256 = (
    "886fab70da8584fdf43cec921064b2891e5477b7118be979313e1950260b145e"
)

# Bound additively after immutable publication and the ordered no-return audit.
SNAPSHOT_MANIFEST_SHA256 = (
    "896ecf82cf6d9b8b0609bcb6b28345de57a91980ddd3d8d196e69a51ffbf72d8"
)
SNAPSHOT_DATASET_SHA256 = (
    "96d875a6e9699c771ba8f217400cc15c5d4c36ade2b86422c6ee8f8b2f179fae"
)
NO_RETURN_AUDIT_SHA256 = (
    "bfa71fa20425e7822c95635783e60d1c9762dacc7c1945d94757e47710c6fa63"
)

TERMINAL_LIBRARY_COUNT = 66
TERMINAL_LIBRARY_ORDER_SHA256 = (
    "71a34e7decf7ba4a456cff4e08b0ea034a3919ee62edf5eb3bec603eb50a5bed"
)
COMPARISON_COUNT = 68
COMPARISON_ORDER_SHA256 = (
    "86bf315f3e7cf1fa7cc4a70118830807a4e7a311efbab34c2b0df02e0c617a1f"
)
SELECTED_BAR_COUNT = 240
WITHIN_HALF_RETURN_COUNT = 238
ADJACENT_PAIR_COUNT = 236
ENDPOINT_TOLERANCE = 1e-12
LOWER_BOUND = -2.0
UPPER_BOUND = 2.0
FACTOR_FORMULA = (
    "Within each 120-close half, form 119 adjacent log returns r_j and "
    "destination-bar activity a_j=log1p(amount_{j+1}). Across the 118 "
    "adjacent return/activity pairs per half, pooled to 236, return "
    "Corr(abs(r_j),a_{j+1}) - Corr(a_j,abs(r_{j+1})) using equal-position "
    "population Pearson correlations."
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign045_feature_library_v1"
)
C44_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign044_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign044_feature_library_v1/snapshot_manifest.json"
)
C44_SNAPSHOT_SHA256 = (
    "ab5d08bf5c9ca8737c32b13e8a6fcc68d9cfb26fc8cdb43377d34bde5d724964"
)
C44_DATASET_SHA256 = (
    "295c023b3f6a76605ab0413f6ab9410e2dabcb4cb2d262de7a62618818a55487"
)
C44_FACTOR_NAME = "full_terminal_library_directional_percentile_consensus_66f"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [
            (str(item["name"]), str(item["score_direction"]))
            for item in comparisons
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign043 feature orchestration changed")

# Reuse only the tested stock-year checkpoint and publication machinery.
_source = BASE_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign043", "Campaign045"),
    ("campaign043", "campaign045"),
    ("campaign_043", "campaign_045"),
    (OLD_FACTOR, FACTOR_NAME),
    (campaign043.MECHANISM_AUDIT_SHA256, MECHANISM_AUDIT_SHA256),
    (campaign043.PROTOCOL_SHA256, PROTOCOL_SHA256),
    (campaign043.SNAPSHOT_MANIFEST_SHA256, ""),
    (campaign043.SNAPSHOT_DATASET_SHA256, ""),
    (campaign043.NO_RETURN_AUDIT_SHA256, ""),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign045_features_generated",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _generated)

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_045_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_045/no_return"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
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
FACTOR_RANGES = {FACTOR_NAME: (LOWER_BOUND, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
market = _generated["market"]
Campaign045FeatureError = _generated["Campaign045FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every binding and materialize the exact Campaign045 spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign045FeatureError("Campaign045 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign045FeatureError("Campaign045 protocol has a failed binding")
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    source = delta.get("source_chain") or {}
    valid_range = candidate.get("valid_range") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign045_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign045_minute_candidate_comparison_daily_"
            "price_or_return_values"
        )
        and (source.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("selected_grid")
        == ["09:31-11:30", "13:01-15:00"]
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get("within_half_return_count")
        == WITHIN_HALF_RETURN_COUNT
        and candidate.get("adjacent_pair_count") == ADJACENT_PAIR_COUNT
        and candidate.get("return_definition")
        == (
            "r_j=log(close_{j+1}/close_j) separately inside each "
            "120-close half"
        )
        and candidate.get("activity_definition")
        == (
            "a_j=log1p(destination_bar_amount_cny) for each within-half "
            "return"
        )
        and candidate.get("reactive_component")
        == (
            "population PearsonCorr(abs(r_j),a_{j+1}) over the pooled 236 "
            "within-half adjacent pairs"
        )
        and candidate.get("anticipatory_component")
        == (
            "population PearsonCorr(a_j,abs(r_{j+1})) over the same pooled "
            "236 within-half adjacent pairs"
        )
        and candidate.get("score_definition")
        == "reactive_component_minus_anticipatory_component"
        and candidate.get("zero_semantics")
        == "Retain every exact-zero return and exact-zero amount at its fixed position."
        and candidate.get("variance_semantics")
        == (
            "Require strictly positive population variance in both vectors "
            "of each Pearson component."
        )
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and valid_range
        == {
            "lower": LOWER_BOUND,
            "lower_inclusive": True,
            "upper": UPPER_BOUND,
            "upper_inclusive": True,
        }
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "alternate_field_lag_window_transform_component_direction_scale_"
            "board_year_cost_regime_fit_combination_or_model_search"
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
        and uniqueness.get("inherited_terminal_factor_count")
        == TERMINAL_LIBRARY_COUNT
        and uniqueness.get("inherited_terminal_factor_order_sha256")
        == TERMINAL_LIBRARY_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and len({str(item.get("name") or "") for item in comparisons})
        == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_68_must_pass") is True
        and comparisons[-2]
        == {
            "name": "intraday_cumulative_vwap_crossing_rate_240m",
            "score_direction": "higher",
        }
        and comparisons[-1]
        == {"name": C44_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id")
        == "wf045_intraday_volatility_activity_lead_lag_asymmetry_236p_single_higher"
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
        raise Campaign045FeatureError("Campaign045 protocol semantics changed")

    spec = copy.deepcopy(campaign043.load_protocol())
    spec["kind"] = delta["kind"]
    spec["status"] = delta["status"]
    spec["frozen_at"] = delta["frozen_at"]
    spec["purpose"] = delta["purpose"]
    spec["source_chain"] = copy.deepcopy(source)
    spec["candidates"] = [
        {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "source_fields_allowed": list(RAW_COLUMNS),
            "source_fields_used_by_formula": list(RAW_COLUMNS),
            "selected_bar_count": SELECTED_BAR_COUNT,
            "within_half_return_count": WITHIN_HALF_RETURN_COUNT,
            "adjacent_pair_count": ADJACENT_PAIR_COUNT,
            "valid_range": [LOWER_BOUND, UPPER_BOUND],
        }
    ]
    spec["ordered_no_return_gates"] = {
        "coverage_and_capacity_before_comparison_values": copy.deepcopy(coverage),
        "uniqueness_after_coverage_only": copy.deepcopy(uniqueness),
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
            "start": "2019-01-01",
            "end": "2023-12-31",
            "folds": copy.deepcopy(
                (campaign043.load_protocol().get("finite_post_admissibility_search") or {})
                .get("development_interval", {})
                .get("folds", [])
            ),
            "purge_local_signal_sessions": 3,
        },
    }
    return spec


def _population_corr(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        x_centered = x - x.mean(axis=1)[:, None]
        y_centered = y - y.mean(axis=1)[:, None]
        x_energy = np.sum(x_centered * x_centered, axis=1)
        y_energy = np.sum(y_centered * y_centered, axis=1)
        denominator = np.sqrt(x_energy * y_energy)
        positive = denominator > 0.0
        values = np.divide(
            np.sum(x_centered * y_centered, axis=1),
            denominator,
            out=np.full(len(x), np.nan, dtype=float),
            where=positive,
        )
    return values, positive


def compute_factor_values(
    *,
    closes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen reactive-minus-anticipatory correlation difference."""

    closes = np.asarray(closes, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    if (
        closes.ndim != 2
        or closes.shape[1] != SELECTED_BAR_COUNT
        or amounts.shape != closes.shape
    ):
        raise Campaign045FeatureError("Campaign045 close/amount shape is invalid")
    finite_close = np.isfinite(closes).all(axis=1)
    positive_close = (closes > 0.0).all(axis=1)
    finite_amount = np.isfinite(amounts).all(axis=1)
    nonnegative_amount = (amounts >= 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_closes = np.log(closes)
        morning_returns = np.diff(log_closes[:, :120], axis=1)
        afternoon_returns = np.diff(log_closes[:, 120:], axis=1)
        returns = np.concatenate([morning_returns, afternoon_returns], axis=1)
        destination_amounts = np.concatenate(
            [amounts[:, 1:120], amounts[:, 121:240]], axis=1
        )
        activities = np.log1p(destination_amounts)
    magnitudes = np.abs(returns)
    earlier_magnitudes = np.concatenate(
        [magnitudes[:, :118], magnitudes[:, 119:237]], axis=1
    )
    later_magnitudes = np.concatenate(
        [magnitudes[:, 1:119], magnitudes[:, 120:238]], axis=1
    )
    earlier_activities = np.concatenate(
        [activities[:, :118], activities[:, 119:237]], axis=1
    )
    later_activities = np.concatenate(
        [activities[:, 1:119], activities[:, 120:238]], axis=1
    )
    if not all(
        value.shape == (len(closes), ADJACENT_PAIR_COUNT)
        for value in (
            earlier_magnitudes,
            later_magnitudes,
            earlier_activities,
            later_activities,
        )
    ):
        raise Campaign045FeatureError("Campaign045 adjacent-pair support changed")
    reactive, reactive_positive = _population_corr(
        earlier_magnitudes, later_activities
    )
    anticipatory, anticipatory_positive = _population_corr(
        earlier_activities, later_magnitudes
    )
    raw_values = reactive - anticipatory
    finite_vectors = (
        np.isfinite(returns).all(axis=1)
        & np.isfinite(activities).all(axis=1)
        & np.isfinite(earlier_magnitudes).all(axis=1)
        & np.isfinite(later_magnitudes).all(axis=1)
        & np.isfinite(earlier_activities).all(axis=1)
        & np.isfinite(later_activities).all(axis=1)
    )
    low_canonicalized = (
        (raw_values < LOWER_BOUND)
        & (raw_values >= LOWER_BOUND - ENDPOINT_TOLERANCE)
    )
    high_canonicalized = (
        (raw_values > UPPER_BOUND)
        & (raw_values <= UPPER_BOUND + ENDPOINT_TOLERANCE)
    )
    values = np.where(low_canonicalized, LOWER_BOUND, raw_values)
    values = np.where(high_canonicalized, UPPER_BOUND, values)
    finite_score = np.isfinite(values)
    in_range = (values >= LOWER_BOUND) & (values <= UPPER_BOUND)
    required_valid = (
        finite_close & positive_close & finite_amount & nonnegative_amount
    )
    eligible = (
        required_valid
        & finite_vectors
        & reactive_positive
        & anticipatory_positive
        & finite_score
        & in_range
    )
    quality = {
        "base_rows": int(len(closes)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__nonfinite_close_rows": int((~finite_close).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_close & ~positive_close).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_amount_rows": int((~finite_amount).sum()),
        f"{FACTOR_NAME}__negative_amount_rows": int(
            (finite_amount & ~nonnegative_amount).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_return_positions": int((returns == 0.0).sum()),
        f"{FACTOR_NAME}__exact_zero_amount_positions": int(
            (destination_amounts == 0.0).sum()
        ),
        f"{FACTOR_NAME}__invalid_return_or_activity_rows": int(
            (required_valid & ~finite_vectors).sum()
        ),
        f"{FACTOR_NAME}__degenerate_reactive_correlation_rows": int(
            (required_valid & finite_vectors & ~reactive_positive).sum()
        ),
        f"{FACTOR_NAME}__degenerate_anticipatory_correlation_rows": int(
            (required_valid & finite_vectors & ~anticipatory_positive).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & (low_canonicalized | high_canonicalized)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_vectors
                & reactive_positive
                & anticipatory_positive
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
    """Validate one source partition and compute Campaign045."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign045FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign045FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
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
        raise Campaign045FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
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
        raise Campaign045FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign045FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign045FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign045FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
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
        ["trade_date", "minute_code"], kind="stable"
    )
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign045FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    amounts = continuous["amount"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(
        closes=closes,
        amounts=amounts,
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


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = (
            "a_share_three_day_walkforward_campaign045_feature_snapshot"
        )
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = True
        evidence = dict(manifest.get("protocol_evidence") or {})
        for key in list(evidence):
            if key.startswith("campaign006_") or key.startswith("campaign045_"):
                evidence.pop(key)
        evidence["campaign045_mechanism_overlap_audit_sha256"] = (
            MECHANISM_AUDIT_SHA256
        )
        evidence["campaign045_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    files = list(manifest.get("files") or [])
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign045_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is True
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign045_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign045_no_return_preregistration_sha256")
        == PROTOCOL_SHA256
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
        raise Campaign045FeatureError("Campaign045 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign045FeatureError("Campaign045 snapshot fingerprint changed")


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Publish Campaign045 with truthful close-and-amount metadata."""

    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original_atomic_write_json = publication_foundation.atomic_write_json

    def campaign045_atomic_write_json(value: dict[str, Any], path: Path) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign045_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value["source_open_high_low_read"] = False
            value["source_close_read"] = True
            value["source_volume_read"] = False
            value["source_amount_read"] = True
        original_atomic_write_json(value, path)

    publication_foundation.atomic_write_json = campaign045_atomic_write_json
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original_atomic_write_json


def _load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage first, then all 68 frozen uniqueness comparisons."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign045FeatureError(
            "bind Campaign045 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign045FeatureError("Campaign045 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign045_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign045FeatureError(
                "existing Campaign045 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign045FeatureError("Campaign045 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, candidate49, comparison_engine = (
        campaign044._context()
    )
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        direction_by_factor = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        catalog, source_verifications = campaign044._build_source_catalog(
            data_root=data_root,
            workers=workers,
            verify_files=True,
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
                        direction=direction_by_factor[factor],
                        gate=gate,
                    )
                )
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign045FeatureError("complete 66-factor catalog changed")

        _, candidate49_path, candidate49_manifest = engine._comparison_chain(
            data_root
        )
        candidate49_verification = candidate49.verify_snapshot_files(
            candidate49_manifest,
            candidate49_path,
            workers,
        )
        candidate49_values = engine._load_filtered_comparison_values_explicit(
            candidate49_manifest,
            [candidate49.FACTOR_NAME],
            keys,
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
        gc.collect()

        if _sha256(C44_SNAPSHOT_PATH) != C44_SNAPSHOT_SHA256:
            raise Campaign045FeatureError("Campaign044 snapshot manifest changed")
        c44_manifest = json.loads(C44_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if c44_manifest.get("dataset_sha256") != C44_DATASET_SHA256:
            raise Campaign045FeatureError("Campaign044 snapshot dataset changed")
        c44_verification = campaign044.verify_snapshot_files(
            c44_manifest,
            C44_SNAPSHOT_PATH,
            workers,
        )
        c44_values = engine._load_filtered_comparison_values_explicit(
            c44_manifest,
            [C44_FACTOR_NAME],
            keys,
        )[C44_FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=c44_values,
                comparison=C44_FACTOR_NAME,
                direction="higher",
                gate=gate,
            )
        )
        del c44_values, keys, values
        gc.collect()
        observed_order = [
            str(item["comparison_factor"]) for item in comparisons
        ]
        observed_correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
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
            "campaign044_snapshot_file_verification": c44_verification,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed_correlations) if observed_correlations else None
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
    run_id = f"{research._timestamp()}_campaign045_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign045_no_return_audit",
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
            "freeze the exact one-trial Campaign045 walk-forward catalog before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a genuinely new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_close_and_amount_fields_read": ["close", "amount"],
        "minute_open_high_low_or_volume_fields_read": [],
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
        experiment_root.expanduser().resolve().glob("*_campaign045_no_return_audit.json")
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


for _key, _value in {
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
    "run_no_return_audit": run_no_return_audit,
    "status": status,
}.items():
    _generated[_key] = _value

_engine_globals = _generated["_engine_globals"]
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
verify_snapshot_files = _generated["verify_snapshot_files"]
_generated["_validate_snapshot_manifest"] = _validate_snapshot_manifest
_engine_globals["_validate_snapshot_manifest"] = _validate_snapshot_manifest
_generated["build_snapshot"] = build_snapshot
_engine_globals["build_snapshot"] = build_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and no-return audit Campaign045 feature mechanism."
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
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
        print(json.dumps({"snapshot_manifest": str(path)}, sort_keys=True))
        return 0
    if args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
        print(json.dumps({"audit_path": str(path)}, sort_keys=True))
        return 0
    print(json.dumps(status(args.data_root, args.experiment_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
