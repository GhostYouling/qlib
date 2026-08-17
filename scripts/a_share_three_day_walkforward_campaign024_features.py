#!/usr/bin/env python3
"""Build and no-return audit the frozen Campaign024 range-response factor.

Campaign023 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
OHLC from each complete continuous-session minute bar, and appends Campaign023
as comparison 45.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign023_features as campaign023
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign023_features as campaign023


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN023_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign023_features.py"
)
CAMPAIGN023_FEATURE_RUNNER_SHA256 = (
    "2de8207b904332d8c4dda0b284bf1f1853d72874db9f1ad92d4cfd633da7f154"
)
OLD_FACTOR = "intraday_range_boundary_translation_coherence_238p"
FACTOR_NAME = "intraday_directional_range_response_coupling_238p"
MECHANISM_AUDIT_SHA256 = (
    "ffe4485ebfe0387076f33e2a631d7a14e93ae6d8559e13a67b0b74f3b32d72b6"
)
PROTOCOL_SHA256 = (
    "70d8e8f1fc6b0b74f3f19e41bc6a148e999eb57239ed5a156d75a3315edecb02"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "855d4f64b6c06d294ba971472e0a6a0b13a82b5cfd708be0535a04255151282b"
)
SNAPSHOT_DATASET_SHA256 = (
    "b204fd6048454308fda9fc9724dfe7d0379847230c29822b71d18948a3ce2f20"
)
NO_RETURN_AUDIT_SHA256 = (
    "90587a0029069e1e6a339b9d406cbbd25bb689e748cb6a0d48c4cacffe043d7e"
)

ENDPOINT_TOLERANCE = 1e-12
WITHIN_HALF_TRANSITION_COUNT = 238

C23_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign023_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign023_feature_library_v1/snapshot_manifest.json"
)
C23_SNAPSHOT_SHA256 = (
    "64732b36c84cf95024e615569bd5626f5951282e24a2ea534ea3f09c03fc41c8"
)
C23_DATASET_SHA256 = (
    "443aa07644a31721eda4a3791ea24f3726049319aaabd917cb0ad00e5551d0b7"
)
C23_FACTOR_NAMES = ("intraday_range_boundary_translation_coherence_238p",)
C23_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C23_FACTOR_NAMES[0],
    f"{C23_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN023_FEATURE_RUNNER) != CAMPAIGN023_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign023 feature orchestration fingerprint changed")

_source = campaign023._source
for _old, _new in (
    ("Campaign023", "Campaign024"),
    ("campaign023", "campaign024"),
    ("campaign_023", "campaign_024"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "0a686cacdcce6e281e1b3c7100a5230f61308f09a9acb692859c44d24fad30c7",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "bf796a2b251fcd8ff717180c59d74da4e664dca85fbdb96d9d565fc801bcf61b",
        PROTOCOL_SHA256,
    ),
    (
        "64732b36c84cf95024e615569bd5626f5951282e24a2ea534ea3f09c03fc41c8",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "443aa07644a31721eda4a3791ea24f3726049319aaabd917cb0ad00e5551d0b7",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "d44a4a1d0147515655e11cc5456d87ff5067d2f6e15b0a78b7b4313d0a87ac08",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", '
        '"low", "close")'
    ),
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(delta_log_high_t, delta_log_low_t) over "
    "exactly 238 adjacent transitions wholly inside the two trading halves"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(log(close_t/open_t), "
    "log(high_{t+1}/low_{t+1})) over exactly 238 one-step transitions "
    "wholly inside the two trading halves"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign023 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign024 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign024FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign024 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign024 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign024 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign024_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
    candidate = candidates[0] if len(candidates) == 1 else {}
    names = tuple(str(item.get("name") or "") for item in candidates)
    formulas = {
        str(item.get("name") or ""): str(item.get("formula") or "")
        for item in candidates
    }
    directions = {
        str(item.get("name") or ""): str(item.get("direction") or "")
        for item in candidates
    }
    audit = spec.get("ordered_no_return_gates") or {}
    coverage = audit.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = audit.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get(
        "mechanism_overlap_audit"
    ) or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign024_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_only_for_validation") or ())
        == ()
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_transition_count")
        == WITHIN_HALF_TRANSITION_COUNT
        and candidate.get("transition_semantics")
        == (
            "For each trading half, pair log(close_t/open_t) from current "
            "positions 1-119 with log(high_{t+1}/low_{t+1}) from following "
            "positions 2-120; concatenate 119 morning and 119 afternoon "
            "pairs. Standalone 09:30 and lunch are excluded."
        )
        and candidate.get("zero_value_semantics")
        == (
            "Every exact-zero current body and exact-zero following range "
            "remains in the fixed 238-pair support; no filtering or bridging "
            "is allowed."
        )
        and candidate.get("variance_semantics")
        == (
            "Both complete 238-element body and following-range vectors "
            "require strictly positive population variance."
        )
        and candidate.get("bar_semantics")
        == (
            "All 240 selected open, high, low, and close values must be "
            "finite and positive with exact low<=open<=high and "
            "low<=close<=high; zero bodies and zero-range bars remain valid."
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
        and len(comparisons) == 45
        and str(comparisons[-1].get("name") or "") == C23_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_open_high_low_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get("minute_volume_amount_fields_read_before_admissibility")
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
        raise Campaign024FeatureError(
            "Campaign024 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen current-body to following-range correlation."""

    opens = np.asarray(opens, dtype=float)
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    closes = np.asarray(closes, dtype=float)
    if (
        opens.ndim != 2
        or opens.shape[1] != SELECTED_BAR_COUNT
        or highs.shape != opens.shape
        or lows.shape != opens.shape
        or closes.shape != opens.shape
    ):
        raise Campaign024FeatureError("Campaign024 aligned array shapes are invalid")

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
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_bodies = np.log(closes / opens)
        log_ranges = np.log(highs / lows)
        current_bodies = np.concatenate(
            (log_bodies[:, :119], log_bodies[:, 120:239]),
            axis=1,
        )
        following_ranges = np.concatenate(
            (log_ranges[:, 1:120], log_ranges[:, 121:240]),
            axis=1,
        )
    components_finite = (
        np.isfinite(current_bodies).all(axis=1)
        & np.isfinite(following_ranges).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        body_centered = current_bodies - np.mean(
            current_bodies, axis=1, keepdims=True
        )
        range_centered = following_ranges - np.mean(
            following_ranges, axis=1, keepdims=True
        )
        body_variance = np.mean(body_centered * body_centered, axis=1)
        range_variance = np.mean(range_centered * range_centered, axis=1)
        covariance = np.mean(body_centered * range_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_values = covariance / np.sqrt(body_variance * range_variance)

    low_bound = -1.0
    high_bound = 1.0
    canonicalized = (
        ((raw_values < low_bound) & (raw_values >= low_bound - ENDPOINT_TOLERANCE))
        | (
            (raw_values > high_bound)
            & (raw_values <= high_bound + ENDPOINT_TOLERANCE)
        )
    )
    values = np.where(
        (raw_values < low_bound)
        & (raw_values >= low_bound - ENDPOINT_TOLERANCE),
        low_bound,
        raw_values,
    )
    values = np.where(
        (values > high_bound) & (values <= high_bound + ENDPOINT_TOLERANCE),
        high_bound,
        values,
    )
    required_valid = finite & positive & ordered & components_finite
    variance_valid = (
        required_valid & (body_variance > 0.0) & (range_variance > 0.0)
    )
    value_finite = np.isfinite(values)
    in_range = (values >= low_bound) & (values <= high_bound)
    eligible = variance_valid & value_finite & in_range
    zero_body = current_bodies == 0.0
    zero_following_range = following_ranges == 0.0
    quality = {
        "base_rows": int(len(opens)),
        "invalid_required_ohlc_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_ohlc_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_ohlc_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_component_rows": int(
            (finite & positive & ordered & ~components_finite).sum()
        ),
        f"{FACTOR_NAME}__zero_body_observations": int(zero_body.sum()),
        f"{FACTOR_NAME}__rows_with_zero_body": int(zero_body.any(axis=1).sum()),
        f"{FACTOR_NAME}__zero_following_range_observations": int(
            zero_following_range.sum()
        ),
        f"{FACTOR_NAME}__rows_with_zero_following_range": int(
            zero_following_range.any(axis=1).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_body_variance_rows": int(
            (required_valid & (body_variance <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_following_range_variance_rows": int(
            (required_valid & (range_variance <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (variance_valid & (~value_finite | ~in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


'''

_new_partition = r'''def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute directional range response."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign024FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign024FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign024FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("open", "high", "low", "close"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign024FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign024FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign024FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign024FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "open", "high", "low", "close"]
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES), fields
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
        raise Campaign024FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("open", "high", "low", "close")
    }
    values, eligible, quality = compute_factor_values(
        opens=arrays["open"],
        highs=arrays["high"],
        lows=arrays["low"],
        closes=arrays["close"],
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


'''

_loader_start = _source.index("def load_protocol(")
_compute_start = _source.index("def compute_factor_values(", _loader_start)
_partition_start = _source.index("def compute_partition_frame(", _compute_start)
_configure_start = _source.index("def _configure_engine(", _partition_start)
_source = (
    _source[:_loader_start]
    + _new_loader
    + _new_compute
    + _new_partition
    + _source[_configure_start:]
)

# Final Campaign024 manifests truthfully record OHLC and no volume/benchmark.
_source = _source.replace(
    'manifest.get("source_close_read") is False',
    'manifest.get("source_close_read") is True',
    1,
)
_source = _source.replace(
    'value["source_close_read"] = False',
    'value["source_close_read"] = True',
    1,
)
_source = _source.replace(
    '"minute_open_read": False',
    '"minute_open_read": True',
    1,
)
_source = _source.replace(
    '"minute_close_read": False',
    '"minute_close_read": True',
    1,
)
_source = _source.replace(
    '"minute_open_read_by_status": False',
    '"minute_open_read_by_status": True',
    1,
)
_source = _source.replace(
    '"minute_close_read_by_status": False',
    '"minute_close_read_by_status": True',
    1,
)

_verify_c22 = '''        c22_manifest, c22_verification = executor._verify_prior_snapshot(
            path=C22_SNAPSHOT_PATH,
            manifest_sha256=C22_SNAPSHOT_SHA256,
            dataset_sha256=C22_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign022_feature_snapshot",
            factor_names=C22_FACTOR_NAMES,
            output_columns=C22_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c23 = _verify_c22 + '''        c23_manifest, c23_verification = executor._verify_prior_snapshot(
            path=C23_SNAPSHOT_PATH,
            manifest_sha256=C23_SNAPSHOT_SHA256,
            dataset_sha256=C23_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign023_feature_snapshot",
            factor_names=C23_FACTOR_NAMES,
            output_columns=C23_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c22 not in _source:
    raise RuntimeError("Campaign023 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c22, _verify_c23, 1)

_compare_c22 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c22_manifest,
                factors=C22_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c23 = _compare_c22 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c23_manifest,
                factors=C23_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c22 not in _source:
    raise RuntimeError("Campaign023 comparison extension block was not found")
_source = _source.replace(_compare_c22, _compare_c23, 1)
_source = _source.replace(
    "Apply coverage before all 44 frozen uniqueness comparisons.",
    "Apply coverage before all 45 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 44", "len(comparisons) == 45")
_source = _source.replace(
    '''            "campaign022_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign022_terminal_comparison_count": 1,
            "campaign023_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign022_snapshot_file_verification": c22_verification,
            "comparisons": comparisons,''',
    '''            "campaign022_snapshot_file_verification": c22_verification,
            "campaign023_snapshot_file_verification": c23_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign024_features_generated",
    "WITHIN_HALF_TRANSITION_COUNT": WITHIN_HALF_TRANSITION_COUNT,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign023.engine_namespace[_key]
_generated.update(
    {
        "C23_SNAPSHOT_PATH": C23_SNAPSHOT_PATH,
        "C23_SNAPSHOT_SHA256": C23_SNAPSHOT_SHA256,
        "C23_DATASET_SHA256": C23_DATASET_SHA256,
        "C23_FACTOR_NAMES": C23_FACTOR_NAMES,
        "C23_OUTPUT_COLUMNS": C23_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN023_FEATURE_RUNNER), "exec"), _generated)

Campaign024FeatureError = _generated["Campaign024FeatureError"]
compute_factor_values = _generated["compute_factor_values"]
compute_partition_frame = _generated["compute_partition_frame"]
empty_output_frame = _generated["empty_output_frame"]
load_protocol = _generated["load_protocol"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
parser = _generated["parser"]
main = _generated["main"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
engine_namespace = run_no_return_audit.__globals__
for _export_name in (
    "DEFAULT_PROTOCOL",
    "DEFAULT_DATA_ROOT",
    "DEFAULT_EXPERIMENT_ROOT",
    "RAW_COLUMNS",
    "BASE_COLUMNS",
    "FACTOR_NAMES",
    "FACTOR_DIRECTIONS",
    "FACTOR_RANGES",
    "FACTOR_FORMULA",
    "FACTOR_FORMULAS",
    "OUTPUT_COLUMNS",
    "SELECTED_BAR_COUNT",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
