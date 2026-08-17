#!/usr/bin/env python3
"""Build and no-return audit the frozen Campaign025 extreme-order factor.

Campaign024 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
high/low from each complete continuous-session minute grid, and appends the
Campaign024 diagnostic-only snapshot as comparison 46.
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
    import scripts.a_share_three_day_walkforward_campaign024_features as campaign024
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign024_features as campaign024


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN024_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign024_features.py"
)
CAMPAIGN024_FEATURE_RUNNER_SHA256 = (
    "61d3e0f9cff0f4be87f3b33d676c68ada65c38ae1b0c47a3858c91bf0740f81e"
)
OLD_FACTOR = "intraday_directional_range_response_coupling_238p"
FACTOR_NAME = "intraday_extreme_arrival_order_240m"
MECHANISM_AUDIT_SHA256 = (
    "09fa633ffbc90e0edcb9ea4edcaeacd96fc8639577492e2c9e40ed2c90dad62f"
)
PROTOCOL_SHA256 = (
    "008d83fcb047601b99a74e6810d58eb26524bb6ebc08add230f4525eb7884904"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def"
)
SNAPSHOT_DATASET_SHA256 = (
    "57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056"
)
NO_RETURN_AUDIT_SHA256 = (
    "e67df10a429b902246450823ea7cb9645e88a8b027ab97965afca6029989b238"
)

POSITION_DENOMINATOR = 239

C24_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign024_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign024_feature_library_v1/snapshot_manifest.json"
)
C24_SNAPSHOT_SHA256 = (
    "855d4f64b6c06d294ba971472e0a6a0b13a82b5cfd708be0535a04255151282b"
)
C24_DATASET_SHA256 = (
    "b204fd6048454308fda9fc9724dfe7d0379847230c29822b71d18948a3ce2f20"
)
C24_FACTOR_NAMES = ("intraday_directional_range_response_coupling_238p",)
C24_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C24_FACTOR_NAMES[0],
    f"{C24_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN024_FEATURE_RUNNER) != CAMPAIGN024_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign024 feature orchestration fingerprint changed")

_source = campaign024._source
for _old, _new in (
    ("Campaign024", "Campaign025"),
    ("campaign024", "campaign025"),
    ("campaign_024", "campaign_025"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "ffe4485ebfe0387076f33e2a631d7a14e93ae6d8559e13a67b0b74f3b32d72b6",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "70d8e8f1fc6b0b74f3f19e41bc6a148e999eb57239ed5a156d75a3315edecb02",
        PROTOCOL_SHA256,
    ),
    (
        "855d4f64b6c06d294ba971472e0a6a0b13a82b5cfd708be0535a04255151282b",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "b204fd6048454308fda9fc9724dfe7d0379847230c29822b71d18948a3ce2f20",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "90587a0029069e1e6a339b9d406cbbd25bb689e748cb6a0d48c4cacffe043d7e",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", '
    '"low", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(log(close_t/open_t), "
    "log(high_{t+1}/low_{t+1})) over exactly 238 one-step transitions "
    "wholly inside the two trading halves"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "(first_index(global_max(high)) - first_index(global_min(low))) / 239 "
    "over the ordered 240-bar continuous-session grid"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign024 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

# Final Campaign025 manifests truthfully record high/low-only source access.
_source = _source.replace(
    'manifest.get("source_close_read") is True',
    'manifest.get("source_close_read") is False',
    1,
)
_source = _source.replace(
    'value["source_close_read"] = True',
    'value["source_close_read"] = False',
    1,
)
_source = _source.replace('"minute_open_read": True', '"minute_open_read": False', 1)
_source = _source.replace(
    '"minute_close_read": True', '"minute_close_read": False', 1
)
_source = _source.replace(
    '"minute_open_read_by_status": True',
    '"minute_open_read_by_status": False',
    1,
)
_source = _source.replace(
    '"minute_close_read_by_status": True',
    '"minute_close_read_by_status": False',
    1,
)

_verify_c23 = '''        c23_manifest, c23_verification = executor._verify_prior_snapshot(
            path=C23_SNAPSHOT_PATH,
            manifest_sha256=C23_SNAPSHOT_SHA256,
            dataset_sha256=C23_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign023_feature_snapshot",
            factor_names=C23_FACTOR_NAMES,
            output_columns=C23_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c24 = _verify_c23 + '''        c24_manifest, c24_verification = executor._verify_prior_snapshot(
            path=C24_SNAPSHOT_PATH,
            manifest_sha256=C24_SNAPSHOT_SHA256,
            dataset_sha256=C24_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign024_feature_snapshot",
            factor_names=C24_FACTOR_NAMES,
            output_columns=C24_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c23 not in _source:
    raise RuntimeError("Campaign024 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c23, _verify_c24, 1)

_compare_c23 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c23_manifest,
                factors=C23_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c24 = _compare_c23 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c24_manifest,
                factors=C24_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c23 not in _source:
    raise RuntimeError("Campaign024 comparison extension block was not found")
_source = _source.replace(_compare_c23, _compare_c24, 1)
_source = _source.replace(
    "Apply coverage before all 45 frozen uniqueness comparisons.",
    "Apply coverage before all 46 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 45", "len(comparisons) == 46")
_source = _source.replace(
    '''            "campaign023_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign023_terminal_comparison_count": 1,
            "campaign024_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign023_snapshot_file_verification": c23_verification,
            "comparisons": comparisons,''',
    '''            "campaign023_snapshot_file_verification": c23_verification,
            "campaign024_snapshot_file_verification": c24_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign025_features_generated",
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
        _generated[_key] = campaign024.engine_namespace[_key]
_generated.update(
    {
        "C24_SNAPSHOT_PATH": C24_SNAPSHOT_PATH,
        "C24_SNAPSHOT_SHA256": C24_SNAPSHOT_SHA256,
        "C24_DATASET_SHA256": C24_DATASET_SHA256,
        "C24_FACTOR_NAMES": C24_FACTOR_NAMES,
        "C24_OUTPUT_COLUMNS": C24_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN024_FEATURE_RUNNER), "exec"), _generated)

RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
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

Campaign025FeatureError = _generated["Campaign025FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and the exact no-return semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign025FeatureError("Campaign025 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign025FeatureError(
            "Campaign025 no-return protocol has a failed file binding"
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
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign025_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign025_candidate_or_comparison_values_or_returns"
        and len(candidate_list) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_only_for_validation") or ())
        == ()
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("position_denominator") == POSITION_DENOMINATOR
        and candidate.get("extreme_semantics")
        == (
            "Find global maximum high and global minimum low over the ordered "
            "240 bars, using the earliest exact occurrence of each extreme."
        )
        and candidate.get("time_semantics")
        == (
            "Positions are integers 0 through 239 on the concatenated "
            "09:31-11:30 and 13:01-15:00 grid; standalone 09:30 is excluded "
            "and lunch is collapsed."
        )
        and candidate.get("tie_semantics")
        == (
            "Use first exact occurrence independently for global high and "
            "global low; never use a tolerance, last occurrence, average tied "
            "position, or random tie break."
        )
        and candidate.get("flat_semantics")
        == (
            "A stock-day with global maximum high exactly equal to global "
            "minimum low is missing."
        )
        and candidate.get("bar_semantics")
        == (
            "All 240 selected high and low values must be finite and positive "
            "with exact low<=high."
        )
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
        and len(comparisons) == 46
        and str(comparisons[-1].get("name") or "") == C24_FACTOR_NAMES[0]
        and boundary.get("binding_validation_required_before_candidate_values")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_high_low_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_close_volume_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign025FeatureError("Campaign025 no-return semantics changed")
    return spec


def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the normalized first-arrival order of global high and low."""

    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign025FeatureError("Campaign025 aligned array shapes are invalid")
    finite = np.isfinite(highs).all(axis=1) & np.isfinite(lows).all(axis=1)
    positive = (highs > 0.0).all(axis=1) & (lows > 0.0).all(axis=1)
    ordered = (lows <= highs).all(axis=1)
    global_high = np.max(highs, axis=1)
    global_low = np.min(lows, axis=1)
    first_high = np.argmax(highs, axis=1)
    first_low = np.argmin(lows, axis=1)
    global_range_positive = global_high > global_low
    values = (first_high - first_low).astype(float) / POSITION_DENOMINATOR
    value_finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    required_valid = finite & positive & ordered
    eligible = required_valid & global_range_positive & value_finite & in_range
    high_ties = (highs == global_high[:, None]).sum(axis=1)
    low_ties = (lows == global_low[:, None]).sum(axis=1)
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_high_low_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_high_low_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__zero_global_range_rows": int(
            (required_valid & ~global_range_positive).sum()
        ),
        f"{FACTOR_NAME}__multiple_global_high_rows": int((high_ties > 1).sum()),
        f"{FACTOR_NAME}__multiple_global_low_rows": int((low_ties > 1).sum()),
        f"{FACTOR_NAME}__same_extreme_position_rows": int(
            (first_high == first_low).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (required_valid & global_range_positive & (~value_finite | ~in_range)).sum()
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
    """Validate one source partition and compute extreme arrival order."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign025FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign025FeatureError(
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
        raise Campaign025FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign025FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign025FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign025FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign025FeatureError(
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
        raise Campaign025FeatureError(f"continuous minute grid changed for {symbol}")
    highs = continuous["high"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    lows = continuous["low"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(highs=highs, lows=lows)
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
