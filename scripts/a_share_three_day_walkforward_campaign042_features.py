#!/usr/bin/env python3
"""Build and no-return audit Campaign042 lunch repricing persistence."""

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
    import scripts.a_share_three_day_walkforward_campaign041_features as campaign041
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign041_features as campaign041


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign041_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "4c220a2fccaf5a89b7ea21a1940ef514dd47c38e86784fc13ee32a992e3061c5"
)
OLD_FACTOR = "intraday_microgap_absorption_share_238p"
FACTOR_NAME = "intraday_lunch_repricing_persistence_2r"
MECHANISM_AUDIT_SHA256 = (
    "8f4fae4cf996a90ce82cb6266ce82991a04cd4307103c97bb2b316d8f2a9e3aa"
)
PROTOCOL_SHA256 = (
    "69a554576358c6f2330b4caa3c91d7bbfc67b576259a5f342a89912587d9e826"
)

# Bind these only after immutable artifacts have been published.
SNAPSHOT_MANIFEST_SHA256 = (
    "c56a81a461aae4ea9d1f44c238dd381541e18425837872a17f3d34f8dc796acd"
)
SNAPSHOT_DATASET_SHA256 = (
    "9fe1a6095a70702ef3ce7ba6cbca8e1386749513b00e8494b37813a1639826c8"
)
NO_RETURN_AUDIT_SHA256 = (
    "e4fe41f785a2ad653bf5d64bc5e61ddc9b0abaecdb1cf313d684a64c040fe8ee"
)

INHERITED_COMPARISON_ORDER_SHA256 = (
    "16ea65e40e50d1ef04f967da6f98aa077791bcd1680fab78d2cf28d0509713d8"
)
COMPARISON_ORDER_SHA256 = (
    "2318bc5774032e9a41519936dde4943a9d5f577b5c05999d2fe0f8bef617fa77"
)
SELECTED_BAR_COUNT = 240
LUNCH_PRE_INDEX = 119
AFTERNOON_OPEN_INDEX = 120
AFTERNOON_CLOSE_INDEX = 239
ENDPOINT_CANONICALIZATION_TOLERANCE = 1e-12
LOWER_BOUND = -1.0
UPPER_BOUND = 1.0
FACTOR_FORMULA = (
    "Let g=log(close_13:01/close_11:30) and "
    "a=log(close_15:00/close_13:01). Return "
    "2*g*a/(g^2+a^2). If g=a=0, return missing."
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign042_feature_library_v1"
)

C41_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign041_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign041_feature_library_v1/snapshot_manifest.json"
)
C41_SNAPSHOT_SHA256 = (
    "838f71169e90d33e9ebbfd34d62dd2c4969432454eeaa69ae6601bb6fdc95391"
)
C41_DATASET_SHA256 = (
    "d330e806262d5e3187649273aea14bb20e53d13cc18edfbc8d8dd0616aa0ac0b"
)
C41_FACTOR_NAMES = (OLD_FACTOR,)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign041 feature runner changed")

# Reuse the tested partition/checkpoint/publication infrastructure only.
# Candidate computation, protocol materialization, and the complete audit are
# replaced below.
_source = campaign041._source
for _old, _new in (
    ("Campaign041", "Campaign042"),
    ("campaign041", "campaign042"),
    ("campaign_041", "campaign_042"),
    (OLD_FACTOR, FACTOR_NAME),
    (campaign041.MECHANISM_AUDIT_SHA256, MECHANISM_AUDIT_SHA256),
    (campaign041.PROTOCOL_SHA256, PROTOCOL_SHA256),
    (campaign041.SNAPSHOT_MANIFEST_SHA256, "0" * 64),
    (campaign041.SNAPSHOT_DATASET_SHA256, "0" * 64),
    (campaign041.NO_RETURN_AUDIT_SHA256, "0" * 64),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign042_features_generated",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _generated)

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_042_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_042/no_return"
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
FACTOR_RANGES = {FACTOR_NAME: (LOWER_BOUND, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
market = _generated["market"]
Campaign042FeatureError = _generated["Campaign042FeatureError"]


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
    """Validate Campaign042 and materialize its complete frozen library."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign042FeatureError("Campaign042 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign042FeatureError(
            "Campaign042 no-return protocol has a failed binding"
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
        "campaign042_delta_from_effective_campaign041_protocol"
    ) or {}
    appended = uniqueness.get("appended_comparison") or {}
    valid_range = candidate.get("valid_range") or {}
    expected_anchors = ["11:30", "13:01", "15:00"]
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign042_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign042_minute_candidate_comparison_daily_"
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
        and candidate.get("formula_anchor_times") == expected_anchors
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is True
        and candidate.get("lunch_return_definition")
        == "g=log(close_13:01/close_11:30)"
        and candidate.get("afternoon_follow_through_definition")
        == "a=log(close_15:00/close_13:01)"
        and candidate.get("normalized_interaction")
        == "2*g*a/(g^2+a^2)"
        and candidate.get("exact_zero_component_retained") is True
        and candidate.get("both_components_zero_is_missing") is True
        and candidate.get("all_240_closes_must_be_finite_and_positive") is True
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_CANONICALIZATION_TOLERANCE
        and valid_range
        == {
            "lower": LOWER_BOUND,
            "lower_inclusive": True,
            "upper": UPPER_BOUND,
            "upper_inclusive": True,
        }
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "sign_split_inverse_raw_product_gap_weight_alternate_anchor_"
            "subwindow_board_year_cost_or_model_search"
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
        and uniqueness.get("inherited_comparison_count") == 62
        and uniqueness.get("inherited_comparison_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and appended == {"name": OLD_FACTOR, "score_direction": "higher"}
        and uniqueness.get("comparison_factor_count") == 63
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_63_must_pass") is True
        and campaign_delta.get("comparison_factor_count") == 63
        and campaign_delta.get("comparison_order_sha256")
        == COMPARISON_ORDER_SHA256
        and finite.get("trial_id")
        == "wf042_intraday_lunch_repricing_persistence_2r_single_higher"
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
        raise Campaign042FeatureError("Campaign042 protocol semantics changed")

    base_spec = campaign041.load_protocol()
    comparisons = copy.deepcopy(
        base_spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]["comparison_factors"]
    )
    if (
        len(comparisons) != 62
        or _comparison_order_digest(comparisons)
        != INHERITED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign042FeatureError(
            "Campaign042 inherited comparison library changed"
        )
    comparisons.append(copy.deepcopy(appended))
    if (
        len(comparisons) != 63
        or len({item["name"] for item in comparisons}) != 63
        or _comparison_order_digest(comparisons) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign042FeatureError(
            "Campaign042 complete comparison library changed"
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
            "formula_anchor_times": expected_anchors,
            "valid_range": [LOWER_BOUND, UPPER_BOUND],
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
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the fixed lunch-boundary/afternoon normalized concordance."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign042FeatureError("Campaign042 close shape is invalid")
    finite = np.isfinite(closes).all(axis=1)
    positive = (closes > 0.0).all(axis=1)
    required_valid = finite & positive
    safe = np.where(np.isfinite(closes) & (closes > 0.0), closes, 1.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        lunch_returns = np.log(
            safe[:, AFTERNOON_OPEN_INDEX] / safe[:, LUNCH_PRE_INDEX]
        )
        afternoon_returns = np.log(
            safe[:, AFTERNOON_CLOSE_INDEX] / safe[:, AFTERNOON_OPEN_INDEX]
        )
    finite_components = (
        np.isfinite(lunch_returns) & np.isfinite(afternoon_returns)
    )
    denominators = lunch_returns**2 + afternoon_returns**2
    both_zero = denominators == 0.0
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_values = np.divide(
            2.0 * lunch_returns * afternoon_returns,
            denominators,
            out=np.full(len(closes), np.nan, dtype=float),
            where=denominators != 0.0,
        )
    finite_score = np.isfinite(raw_values)
    within_tolerance = (
        (raw_values >= LOWER_BOUND - ENDPOINT_CANONICALIZATION_TOLERANCE)
        & (raw_values <= UPPER_BOUND + ENDPOINT_CANONICALIZATION_TOLERANCE)
    )
    canonicalized = np.clip(raw_values, LOWER_BOUND, UPPER_BOUND)
    eligible = (
        required_valid
        & finite_components
        & ~both_zero
        & finite_score
        & within_tolerance
    )
    valid_components = required_valid & finite_components
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_component_rows": int(
            (required_valid & ~finite_components).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_lunch_return_rows": int(
            (valid_components & (lunch_returns == 0.0)).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_afternoon_return_rows": int(
            (valid_components & (afternoon_returns == 0.0)).sum()
        ),
        f"{FACTOR_NAME}__both_components_zero_rows": int(
            (valid_components & both_zero).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (
                valid_components
                & ~both_zero
                & finite_score
                & within_tolerance
                & (
                    (raw_values < LOWER_BOUND)
                    | (raw_values > UPPER_BOUND)
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                valid_components
                & ~both_zero
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
    """Validate one source partition and compute lunch persistence."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign042FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign042FeatureError(
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
        raise Campaign042FeatureError(
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
        raise Campaign042FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    source_counts = work.groupby(
        "trade_date", sort=True, observed=True
    ).size()
    if not source_counts.eq(241).all():
        raise Campaign042FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby(
        "trade_date", sort=True, observed=True
    )["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign042FeatureError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(
        drop=True
    )
    if not base_work["trade_date"].reset_index(drop=True).equals(
        expected_dates
    ):
        raise Campaign042FeatureError(
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
        raise Campaign042FeatureError(
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


def _post_campaign031_snapshot_specs() -> list[dict[str, Any]]:
    """Return the exact ordered Campaign032--041 snapshot chain."""

    c40 = campaign041.campaign040
    c39 = c40.campaign039
    c38 = c39.campaign038
    c37 = c38.campaign037
    c36 = c37.campaign036
    c35 = c36.campaign035
    c34 = c35.campaign034
    c33 = c34.campaign033
    return [
        _snapshot_spec(
            campaign=32,
            path=c33.C32_SNAPSHOT_PATH,
            manifest_sha256=c33.C32_SNAPSHOT_SHA256,
            dataset_sha256=c33.C32_DATASET_SHA256,
            factors=c33.C32_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=33,
            path=c34.C33_SNAPSHOT_PATH,
            manifest_sha256=c34.C33_SNAPSHOT_SHA256,
            dataset_sha256=c34.C33_DATASET_SHA256,
            factors=c34.C33_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=34,
            path=c35.C34_SNAPSHOT_PATH,
            manifest_sha256=c35.C34_SNAPSHOT_SHA256,
            dataset_sha256=c35.C34_DATASET_SHA256,
            factors=c35.C34_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=35,
            path=c36.C35_SNAPSHOT_PATH,
            manifest_sha256=c36.C35_SNAPSHOT_SHA256,
            dataset_sha256=c36.C35_DATASET_SHA256,
            factors=c36.C35_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=36,
            path=c37.C36_SNAPSHOT_PATH,
            manifest_sha256=c37.C36_SNAPSHOT_SHA256,
            dataset_sha256=c37.C36_DATASET_SHA256,
            factors=c37.C36_FACTOR_NAMES,
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
            path=c39.C38_SNAPSHOT_PATH,
            manifest_sha256=c39.C38_SNAPSHOT_SHA256,
            dataset_sha256=c39.C38_DATASET_SHA256,
            factors=c39.C38_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=39,
            path=c40.C39_SNAPSHOT_PATH,
            manifest_sha256=c40.C39_SNAPSHOT_SHA256,
            dataset_sha256=c40.C39_DATASET_SHA256,
            factors=c40.C39_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=40,
            path=campaign041.C40_SNAPSHOT_PATH,
            manifest_sha256=campaign041.C40_SNAPSHOT_SHA256,
            dataset_sha256=campaign041.C40_DATASET_SHA256,
            factors=campaign041.C40_FACTOR_NAMES,
        ),
        _snapshot_spec(
            campaign=41,
            path=C41_SNAPSHOT_PATH,
            manifest_sha256=C41_SNAPSHOT_SHA256,
            dataset_sha256=C41_DATASET_SHA256,
            factors=C41_FACTOR_NAMES,
        ),
    ]


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before the complete frozen 63-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign042FeatureError(
            "bind Campaign042 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign042FeatureError("Campaign042 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign042_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign042FeatureError(
                "existing Campaign042 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign042FeatureError("Campaign042 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print(
        "building Campaign042 no-price quality/listing eligibility",
        flush=True,
    )
    prior = (
        campaign041.campaign040.campaign039.campaign038.campaign037
        .campaign036.campaign035.campaign034.campaign033.campaign032
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
        snapshot_specs.extend(_post_campaign031_snapshot_specs())
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
            and len(comparisons) == 63
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
    run_id = f"{research._timestamp()}_campaign042_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign042_no_return_audit",
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
            "freeze the exact one-trial Campaign042 walk-forward catalog before "
            "reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_close_fields_read": ["close"],
        "minute_open_high_low_volume_or_amount_fields_read": [],
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
            "*_campaign042_no_return_audit.json"
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
        "minute_close_fields_read_by_status": ["close"],
        "minute_open_high_low_volume_or_amount_fields_read_by_status": [],
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
    """Publish C42 with truthful close-only aggregate source metadata."""

    publication_foundation = _inherited_build_snapshot.__globals__["foundation"]
    original_atomic_write_json = publication_foundation.atomic_write_json

    def campaign042_atomic_write_json(
        value: dict[str, Any],
        path: Path,
    ) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign042_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value["source_open_high_low_read"] = False
            value["source_close_read"] = True
            value["source_volume_read"] = False
            value["source_amount_read"] = False
        original_atomic_write_json(value, path)

    publication_foundation.atomic_write_json = campaign042_atomic_write_json
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
    """Validate truthful C42 source flags through the inherited schema."""

    if not require_fingerprint_constants:
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
    if not (
        manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
    ):
        raise Campaign042FeatureError(
            "Campaign042 snapshot source-field metadata changed"
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
        description="Build and no-return audit Campaign042 feature mechanism."
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
        print(json.dumps({"audit_path": str(path)}, sort_keys=True))
        return 0
    print(
        json.dumps(
            status(args.data_root, args.experiment_root),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
