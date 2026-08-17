#!/usr/bin/env python3
"""Build and no-return audit Campaign027 half-session profile persistence.

Campaign025 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
the close path, and appends the Campaign025 and Campaign026 terminal snapshots
as comparisons 47 and 48.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign025_features as campaign025
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign025_features as campaign025


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN025_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign025_features.py"
)
CAMPAIGN025_FEATURE_RUNNER_SHA256 = (
    "27f79dbf8e86ae17f71a8cc1e4626b8517d8dde62aa74901a1f9447dd6c0e03d"
)
OLD_FACTOR = "intraday_extreme_arrival_order_240m"
FACTOR_NAME = "intraday_morning_afternoon_return_profile_persistence_119p"
MECHANISM_AUDIT_SHA256 = (
    "1d11781aa307ea32390e702bd5bb1522008e0b7163a5e8ce13b3cdeca07561ef"
)
PROTOCOL_SHA256 = (
    "eb5b83b7b0d957a515c7083d481f4fe6a375f9a3500910270f3c0bc62c2ac7cd"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "0c7082a9c249f1567ca85f1490cb63a7affb86fe7583e92fa13b6dc9e88dab50"
)
SNAPSHOT_DATASET_SHA256 = (
    "bdde7057d2f7174afccd7b5789d79c3c01cc56c13a7e14889d9913cd81851365"
)
NO_RETURN_AUDIT_SHA256 = (
    "efdbdca5b7bb41eb82e7680543d29675675919cbe1df97044289c5e43a1cf1e1"
)

RETURNS_PER_HALF = 119
PAIRED_RETURN_COUNT = 119
ENDPOINT_TOLERANCE = 1e-12

C25_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign025_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign025_feature_library_v1/snapshot_manifest.json"
)
C25_SNAPSHOT_SHA256 = (
    "4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def"
)
C25_DATASET_SHA256 = (
    "57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056"
)
C25_FACTOR_NAMES = ("intraday_extreme_arrival_order_240m",)
C25_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C25_FACTOR_NAMES[0],
    f"{C25_FACTOR_NAMES[0]}_eligible",
)

C26_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign026_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign026_feature_library_v1/snapshot_manifest.json"
)
C26_SNAPSHOT_SHA256 = (
    "1a946ab1a6960100679a4090451ec1c2f3f13950a3f36d8cfc4ff635966537dc"
)
C26_DATASET_SHA256 = (
    "c95e3b2551a4bfc6baf68b55f48add9dd044dcde44bf2e981c403624d0fe958f"
)
C26_FACTOR_NAMES = ("intraday_market_up_down_correlation_asymmetry_238m",)
C26_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C26_FACTOR_NAMES[0],
    f"{C26_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN025_FEATURE_RUNNER) != CAMPAIGN025_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign025 feature orchestration fingerprint changed")

_source = campaign025._source
for _old, _new in (
    ("Campaign025", "Campaign027"),
    ("campaign025", "campaign027"),
    ("campaign_025", "campaign_027"),
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

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(first_index(global_max(high)) - first_index(global_min(low))) / 239 "
    "over the ordered 240-bar continuous-session grid"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(r_am,k, r_pm,k) for k=1..119, where each "
    "vector contains adjacent log-close returns inside its own 120-bar "
    "trading half"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign025 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_source = _source.replace(
    '''        and (
            manifest.get("source_open_high_low_read") is True
            if require_fingerprint_constants
            else manifest.get("source_open_high_low_read") is False
        )''',
    '''        and manifest.get("source_open_high_low_read") is False''',
    1,
)
_source = _source.replace(
    '''        and (
            manifest.get("source_close_read") is False
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, False}
        )''',
    '''        and (
            manifest.get("source_close_read") is True
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, True}
        )''',
    1,
)
_source = _source.replace(
    'value["source_open_high_low_read"] = True',
    'value["source_open_high_low_read"] = False',
    1,
)
_source = _source.replace(
    'value["source_close_read"] = False',
    'value["source_close_read"] = True',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,''',
    '''        "minute_open_high_low_read_by_status": False,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": True,''',
    1,
)

_verify_c24 = '''        c24_manifest, c24_verification = executor._verify_prior_snapshot(
            path=C24_SNAPSHOT_PATH,
            manifest_sha256=C24_SNAPSHOT_SHA256,
            dataset_sha256=C24_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign024_feature_snapshot",
            factor_names=C24_FACTOR_NAMES,
            output_columns=C24_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c25_c26 = _verify_c24 + '''        c25_manifest, c25_verification = executor._verify_prior_snapshot(
            path=C25_SNAPSHOT_PATH,
            manifest_sha256=C25_SNAPSHOT_SHA256,
            dataset_sha256=C25_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign025_feature_snapshot",
            factor_names=C25_FACTOR_NAMES,
            output_columns=C25_OUTPUT_COLUMNS,
            workers=workers,
        )
        c26_manifest, c26_verification = executor._verify_prior_snapshot(
            path=C26_SNAPSHOT_PATH,
            manifest_sha256=C26_SNAPSHOT_SHA256,
            dataset_sha256=C26_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign026_feature_snapshot",
            factor_names=C26_FACTOR_NAMES,
            output_columns=C26_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c24 not in _source:
    raise RuntimeError("Campaign025 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c24, _verify_c25_c26, 1)

_compare_c24 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c24_manifest,
                factors=C24_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c25_c26 = _compare_c24 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c25_manifest,
                factors=C25_FACTOR_NAMES,
                gate=gate,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c26_manifest,
                factors=C26_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c24 not in _source:
    raise RuntimeError("Campaign025 comparison extension block was not found")
_source = _source.replace(_compare_c24, _compare_c25_c26, 1)
_source = _source.replace(
    "Apply coverage before all 46 frozen uniqueness comparisons.",
    "Apply coverage before all 48 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 46", "len(comparisons) == 48")
_source = _source.replace(
    '''            "campaign024_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign024_terminal_comparison_count": 1,
            "campaign025_terminal_comparison_count": 1,
            "campaign026_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign024_snapshot_file_verification": c24_verification,
            "comparisons": comparisons,''',
    '''            "campaign024_snapshot_file_verification": c24_verification,
            "campaign025_snapshot_file_verification": c25_verification,
            "campaign026_snapshot_file_verification": c26_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign027_features_generated",
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign025.engine_namespace[_key]
_generated.update(
    {
        "C25_SNAPSHOT_PATH": C25_SNAPSHOT_PATH,
        "C25_SNAPSHOT_SHA256": C25_SNAPSHOT_SHA256,
        "C25_DATASET_SHA256": C25_DATASET_SHA256,
        "C25_FACTOR_NAMES": C25_FACTOR_NAMES,
        "C25_OUTPUT_COLUMNS": C25_OUTPUT_COLUMNS,
        "C26_SNAPSHOT_PATH": C26_SNAPSHOT_PATH,
        "C26_SNAPSHOT_SHA256": C26_SNAPSHOT_SHA256,
        "C26_DATASET_SHA256": C26_DATASET_SHA256,
        "C26_FACTOR_NAMES": C26_FACTOR_NAMES,
        "C26_OUTPUT_COLUMNS": C26_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN025_FEATURE_RUNNER), "exec"), _generated)

RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = _generated["BASE_COLUMNS"]
SELECTED_BAR_COUNT = _generated["SELECTED_BAR_COUNT"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
FACTOR_NAMES = _generated["FACTOR_NAMES"]
FACTOR_DIRECTIONS = _generated["FACTOR_DIRECTIONS"]
FACTOR_RANGES = _generated["FACTOR_RANGES"]
FACTOR_FORMULA = _generated["FACTOR_FORMULA"]
FACTOR_FORMULAS = _generated["FACTOR_FORMULAS"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
market = _generated["market"]

Campaign027FeatureError = _generated["Campaign027FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and the exact no-return semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign027FeatureError("Campaign027 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign027FeatureError(
            "Campaign027 no-return protocol has a failed file binding"
        )
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate_list = list(spec.get("candidates") or [])
    candidate = candidate_list[0] if len(candidate_list) == 1 else {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get("mechanism_overlap_audit") or {}
    finite_search = spec.get("finite_post_admissibility_search") or {}
    trial = finite_search.get("trial") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign027_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign027_candidate_or_comparison_values_or_returns"
        and len(candidate_list) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("returns_per_half") == RETURNS_PER_HALF
        and candidate.get("paired_return_count") == PAIRED_RETURN_COUNT
        and candidate.get("return_semantics")
        == (
            "Natural-log adjacent close returns are formed separately inside "
            "each 120-close half; no return crosses lunch."
        )
        and candidate.get("pairing_semantics")
        == (
            "Pair morning and afternoon returns only by equal ordinal "
            "positions 1 through 119 within their respective halves."
        )
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_pair_weight"
        and candidate.get("zero_return_semantics")
        == (
            "Retain every exact-zero morning or afternoon return at its fixed "
            "paired position."
        )
        and candidate.get("variance_semantics")
        == (
            "Require strictly positive population variance in both complete "
            "119-return vectors."
        )
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == [-1.0, 1.0]
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 48
        and str(comparisons[-2].get("name") or "") == C25_FACTOR_NAMES[0]
        and str(comparisons[-1].get("name") or "") == C26_FACTOR_NAMES[0]
        and finite_search.get("candidate_factor_count") == 1
        and finite_search.get("development_trial_count") == 1
        and trial.get("factor") == FACTOR_NAME
        and trial.get("direction") == "higher"
        and trial.get("transform") == "none"
        and trial.get("threshold") == "none"
        and trial.get("filter") == "none"
        and trial.get("combination") == "none"
        and boundary.get("binding_validation_required_before_candidate_values")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_high_low_volume_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get("market_benchmark_fields_read_before_admissibility")
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get(
            "candidate49_signal_or_execution_ledger_changed"
        )
        is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign027FeatureError("Campaign027 no-return semantics changed")
    return spec


def compute_factor_values(
    *,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen morning-to-afternoon return-profile persistence."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign027FeatureError("Campaign027 aligned close shape is invalid")
    finite_closes = np.isfinite(closes).all(axis=1)
    positive_closes = (closes > 0.0).all(axis=1)
    required_valid = finite_closes & positive_closes
    safe_closes = np.where(closes > 0.0, closes, 1.0)
    log_closes = np.log(safe_closes)
    morning_returns = np.diff(log_closes[:, :120], axis=1)
    afternoon_returns = np.diff(log_closes[:, 120:], axis=1)
    if (
        morning_returns.shape[1] != RETURNS_PER_HALF
        or afternoon_returns.shape != morning_returns.shape
    ):
        raise Campaign027FeatureError("Campaign027 return-vector shape changed")
    finite_returns = np.isfinite(morning_returns).all(axis=1) & np.isfinite(
        afternoon_returns
    ).all(axis=1)
    morning_centered = morning_returns - morning_returns.mean(axis=1)[:, None]
    afternoon_centered = (
        afternoon_returns - afternoon_returns.mean(axis=1)[:, None]
    )
    morning_energy = np.sum(morning_centered * morning_centered, axis=1)
    afternoon_energy = np.sum(afternoon_centered * afternoon_centered, axis=1)
    denominator = np.sqrt(morning_energy * afternoon_energy)
    positive_variance = denominator > 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.divide(
            np.sum(morning_centered * afternoon_centered, axis=1),
            denominator,
            out=np.full(len(closes), np.nan, dtype=float),
            where=positive_variance,
        )
    low = -1.0
    high = 1.0
    canonicalized = (
        ((values < low) & (values >= low - ENDPOINT_TOLERANCE))
        | ((values > high) & (values <= high + ENDPOINT_TOLERANCE))
    )
    values = np.where(
        (values < low) & (values >= low - ENDPOINT_TOLERANCE),
        low,
        values,
    )
    values = np.where(
        (values > high) & (values <= high + ENDPOINT_TOLERANCE),
        high,
        values,
    )
    finite_values = np.isfinite(values)
    in_range = (values >= low) & (values <= high)
    eligible = (
        required_valid
        & finite_returns
        & positive_variance
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite_closes).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_closes & ~positive_closes).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_return_rows": int(
            (required_valid & ~finite_returns).sum()
        ),
        f"{FACTOR_NAME}__degenerate_morning_variance_rows": int(
            (required_valid & finite_returns & ~(morning_energy > 0.0)).sum()
        ),
        f"{FACTOR_NAME}__degenerate_afternoon_variance_rows": int(
            (required_valid & finite_returns & ~(afternoon_energy > 0.0)).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (required_valid & finite_returns & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_returns
                & positive_variance
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
    """Validate one source partition and compute paired-half persistence."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign027FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign027FeatureError(
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
        raise Campaign027FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign027FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign027FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign027FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign027FeatureError(
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
        raise Campaign027FeatureError(f"continuous minute grid changed for {symbol}")
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


_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["compute_partition_frame"] = compute_partition_frame

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
parser = _generated["parser"]
main = _generated["main"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
engine_namespace = run_no_return_audit.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
