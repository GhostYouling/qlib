#!/usr/bin/env python3
"""Build and no-return audit Campaign046 return-reversal energy share."""

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
    import scripts.a_share_three_day_walkforward_campaign044_features as campaign044
    import scripts.a_share_three_day_walkforward_campaign045_features as campaign045
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign044_features as campaign044
    import a_share_three_day_walkforward_campaign045_features as campaign045


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign045_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "02d6f27d8cc4763bddb42997d2027aef306acc2b9f1856928ab5b0e412b0dcd0"
)
OLD_FACTOR = "intraday_volatility_activity_lead_lag_asymmetry_236p"
FACTOR_NAME = "intraday_return_reversal_energy_share_236p"
MECHANISM_AUDIT_SHA256 = (
    "ea7c58afc40367f3df2a504c079e751cbe948d14dc38055fd9a6a36462630298"
)
PROTOCOL_SHA256 = (
    "7ca20bdf7d32b78489e3ac5cc4d25c6b6773ee09e9260732778f30e86faa7c52"
)

# Bound additively after immutable publication and ordered no-return audit.
SNAPSHOT_MANIFEST_SHA256 = (
    "4103aeee6e45cd54ffcb304283808abb67e6ea6107605f67441df70653e31ccd"
)
SNAPSHOT_DATASET_SHA256 = (
    "ee089ffd7dc7111ec6a7b620830595805ce998db6ef076f9d3cd516a7784d06f"
)
NO_RETURN_AUDIT_SHA256 = (
    "4d7db211439f4e2c019acf8fbc0e6029450f4a31b0dc78e2c20e4edae8673425"
)

TERMINAL_LIBRARY_COUNT = 66
INHERITED_COMPARISON_COUNT = 68
INHERITED_COMPARISON_ORDER_SHA256 = (
    "86bf315f3e7cf1fa7cc4a70118830807a4e7a311efbab34c2b0df02e0c617a1f"
)
COMPARISON_COUNT = 69
COMPARISON_ORDER_SHA256 = (
    "5fbace24bb791ed6a5cfad1425689a9657a70a09e37ca900941972d23d6602a4"
)
SELECTED_BAR_COUNT = 240
WITHIN_HALF_RETURN_COUNT = 238
ADJACENT_PAIR_COUNT = 236
ENDPOINT_TOLERANCE = 1e-12
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
FACTOR_FORMULA = (
    "Within each 120-close half, form 119 adjacent log returns and 118 "
    "ordered adjacent pairs (a,b). Pool both halves to 236 pairs. Return "
    "sum(abs(a*b) for a*b<0) / sum(abs(a*b))."
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign046_feature_library_v1"
)
C45_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign045_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign045_feature_library_v1/snapshot_manifest.json"
)
C45_SNAPSHOT_SHA256 = (
    "896ecf82cf6d9b8b0609bcb6b28345de57a91980ddd3d8d196e69a51ffbf72d8"
)
C45_DATASET_SHA256 = (
    "96d875a6e9699c771ba8f217400cc15c5d4c36ade2b86422c6ee8f8b2f179fae"
)
C45_FACTOR_NAME = "intraday_volatility_activity_lead_lag_asymmetry_236p"


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


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign045 feature orchestration changed")

# Reuse only Campaign045's tested checkpoint/publication/coverage machinery.
_source = BASE_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign045", "Campaign046"),
    ("campaign045", "campaign046"),
    ("campaign_045", "campaign_046"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "c6f5f8b9a19e2867deca7d1c4fbdbdbd565ebb8d1cf4eb5df6d3587205ebb83e",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "886fab70da8584fdf43cec921064b2891e5477b7118be979313e1950260b145e",
        PROTOCOL_SHA256,
    ),
    (
        "896ecf82cf6d9b8b0609bcb6b28345de57a91980ddd3d8d196e69a51ffbf72d8",
        "",
    ),
    (
        "96d875a6e9699c771ba8f217400cc15c5d4c36ade2b86422c6ee8f8b2f179fae",
        "",
    ),
    (
        "bfa71fa20425e7822c95635783e60d1c9762dacc7c1945d94757e47710c6fa63",
        "",
    ),
):
    _source = _source.replace(_old, _new)

_outer_globals: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign046_features_generated",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _outer_globals)
_generated: dict[str, Any] = _outer_globals["_generated"]
campaign043 = _outer_globals["campaign043"]
C44_SNAPSHOT_PATH = _outer_globals["C44_SNAPSHOT_PATH"]
C44_SNAPSHOT_SHA256 = _outer_globals["C44_SNAPSHOT_SHA256"]
C44_FACTOR_NAME = _outer_globals["C44_FACTOR_NAME"]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_046_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_046/no_return"
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
Campaign046FeatureError = _generated["Campaign046FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every binding and materialize the exact Campaign046 spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign046FeatureError("Campaign046 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign046FeatureError("Campaign046 protocol has a failed binding")
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
        == "a_share_three_day_walkforward_campaign046_no_return_preregistration"
        and delta.get("status")
        == "frozen_before_campaign046_minute_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("selected_grid")
        == ["09:31-11:30", "13:01-15:00"]
        and candidate.get("include_0930") is False
        and candidate.get("include_lunch_transition") is False
        and candidate.get("within_half_return_count") == WITHIN_HALF_RETURN_COUNT
        and candidate.get("adjacent_pair_count") == ADJACENT_PAIR_COUNT
        and candidate.get("pair_weight") == "abs(a*b)"
        and candidate.get("opposite_sign_rule") == "a*b<0 exactly"
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
            "alternate_field_lag_window_transform_direction_scale_board_year_"
            "cost_regime_fit_combination_or_model_search"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign045_comparison_factor_count")
        == INHERITED_COMPARISON_COUNT
        and uniqueness.get(
            "inherited_campaign045_comparison_factor_order_sha256"
        )
        == INHERITED_COMPARISON_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and len({str(item.get("name") or "") for item in comparisons})
        == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_69_must_pass") is True
        and comparisons[-1]
        == {"name": C45_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id")
        == "wf046_intraday_return_reversal_energy_share_236p_single_higher"
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
        raise Campaign046FeatureError("Campaign046 protocol semantics changed")

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


def compute_factor_values(
    *, closes: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen adjacent-return reversal-energy share."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign046FeatureError("Campaign046 close shape is invalid")
    finite_close = np.isfinite(closes).all(axis=1)
    positive_close = (closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_closes = np.log(closes)
        morning_returns = np.diff(log_closes[:, :120], axis=1)
        afternoon_returns = np.diff(log_closes[:, 120:], axis=1)
        earlier = np.concatenate(
            [morning_returns[:, :118], afternoon_returns[:, :118]], axis=1
        )
        later = np.concatenate(
            [morning_returns[:, 1:119], afternoon_returns[:, 1:119]], axis=1
        )
        products = earlier * later
        weights = np.abs(products)
        denominator = np.sum(weights, axis=1)
        numerator = np.sum(np.where(products < 0.0, weights, 0.0), axis=1)
        raw_values = np.divide(
            numerator,
            denominator,
            out=np.full(len(closes), np.nan, dtype=float),
            where=denominator > 0.0,
        )
    if earlier.shape != (len(closes), ADJACENT_PAIR_COUNT):
        raise Campaign046FeatureError("Campaign046 adjacent-pair support changed")
    finite_vectors = (
        np.isfinite(morning_returns).all(axis=1)
        & np.isfinite(afternoon_returns).all(axis=1)
        & np.isfinite(products).all(axis=1)
        & np.isfinite(weights).all(axis=1)
    )
    positive_denominator = np.isfinite(denominator) & (denominator > 0.0)
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
    required_valid = finite_close & positive_close
    eligible = (
        required_valid
        & finite_vectors
        & positive_denominator
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
        f"{FACTOR_NAME}__exact_zero_return_positions": int(
            ((morning_returns == 0.0).sum() + (afternoon_returns == 0.0).sum())
        ),
        f"{FACTOR_NAME}__exact_zero_product_positions": int(
            (products == 0.0).sum()
        ),
        f"{FACTOR_NAME}__opposite_sign_pair_positions": int(
            (products < 0.0).sum()
        ),
        f"{FACTOR_NAME}__same_sign_pair_positions": int(
            (products > 0.0).sum()
        ),
        f"{FACTOR_NAME}__invalid_return_or_product_rows": int(
            (required_valid & ~finite_vectors).sum()
        ),
        f"{FACTOR_NAME}__zero_denominator_rows": int(
            (required_valid & finite_vectors & ~positive_denominator).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & (low_canonicalized | high_canonicalized)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_vectors
                & positive_denominator
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
    """Validate one source partition and compute Campaign046."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign046FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign046FeatureError(
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
        raise Campaign046FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign046FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign046FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign046FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign046FeatureError(
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
        raise Campaign046FeatureError(f"continuous minute grid changed for {symbol}")
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


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = "a_share_three_day_walkforward_campaign046_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = dict(manifest.get("protocol_evidence") or {})
        for key in list(evidence):
            if key.startswith("campaign006_") or key.startswith("campaign046_"):
                evidence.pop(key)
        evidence["campaign046_mechanism_overlap_audit_sha256"] = (
            MECHANISM_AUDIT_SHA256
        )
        evidence["campaign046_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    files = list(manifest.get("files") or [])
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign046_feature_snapshot"
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
        and evidence.get("campaign046_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign046_no_return_preregistration_sha256")
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
        raise Campaign046FeatureError("Campaign046 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign046FeatureError("Campaign046 snapshot fingerprint changed")


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Publish Campaign046 with truthful close-only metadata."""

    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original_atomic_write_json = publication_foundation.atomic_write_json

    def campaign046_atomic_write_json(value: dict[str, Any], path: Path) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign046_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value["source_open_high_low_read"] = False
            value["source_close_read"] = True
            value["source_volume_read"] = False
            value["source_amount_read"] = False
        original_atomic_write_json(value, path)

    publication_foundation.atomic_write_json = campaign046_atomic_write_json
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original_atomic_write_json


def _load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    """Apply coverage first, then all 69 frozen uniqueness comparisons."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign046FeatureError(
            "bind Campaign046 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign046FeatureError("Campaign046 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign046_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign046FeatureError(
                "existing Campaign046 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign046FeatureError("Campaign046 audit changed")
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
        direction_by_factor = {
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
                        direction=direction_by_factor[factor],
                        gate=gate,
                    )
                )
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign046FeatureError("complete 66-factor catalog changed")
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
        gc.collect()
        c44_path = C44_SNAPSHOT_PATH
        if _sha256(c44_path) != C44_SNAPSHOT_SHA256:
            raise Campaign046FeatureError("Campaign044 snapshot manifest changed")
        c44_manifest = json.loads(c44_path.read_text(encoding="utf-8"))
        c44_verification = campaign044.verify_snapshot_files(
            c44_manifest, c44_path, workers
        )
        c44_factor = C44_FACTOR_NAME
        c44_values = engine._load_filtered_comparison_values_explicit(
            c44_manifest, [c44_factor], keys
        )[c44_factor]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=c44_values,
                comparison=c44_factor,
                direction="higher",
                gate=gate,
            )
        )
        del c44_values
        gc.collect()
        if _sha256(C45_SNAPSHOT_PATH) != C45_SNAPSHOT_SHA256:
            raise Campaign046FeatureError("Campaign045 snapshot manifest changed")
        c45_manifest = json.loads(C45_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if c45_manifest.get("dataset_sha256") != C45_DATASET_SHA256:
            raise Campaign046FeatureError("Campaign045 snapshot dataset changed")
        c45_verification = campaign045.verify_snapshot_files(
            c45_manifest, C45_SNAPSHOT_PATH, workers
        )
        c45_values = engine._load_filtered_comparison_values_explicit(
            c45_manifest, [C45_FACTOR_NAME], keys
        )[C45_FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=c45_values,
                comparison=C45_FACTOR_NAME,
                direction="higher",
                gate=gate,
            )
        )
        del c45_values, keys, values
        gc.collect()
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
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
            "comparison_order_matches_preregistration": observed_order == expected_order,
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            "campaign044_snapshot_file_verification": c44_verification,
            "campaign045_snapshot_file_verification": c45_verification,
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
    run_id = f"{research._timestamp()}_campaign046_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign046_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {"path": str(DEFAULT_PROTOCOL.resolve()), "sha256": PROTOCOL_SHA256},
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
            "freeze the exact one-trial Campaign046 walk-forward catalog before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a genuinely new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_close_fields_read": ["close"],
        "minute_open_high_low_volume_or_amount_fields_read": [],
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
        experiment_root.expanduser().resolve().glob("*_campaign046_no_return_audit.json")
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
        description="Build and no-return audit Campaign046 feature mechanism."
    )
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
        payload = {"manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
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
