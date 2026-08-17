#!/usr/bin/env python3
"""Build and no-return audit the frozen Campaign023 boundary-coherence factor.

Campaign022 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
high/low from each complete continuous-session minute bar, and appends
Campaign022 as comparison 44.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign022_features as campaign022
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign022_features as campaign022


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN022_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign022_features.py"
)
CAMPAIGN022_FEATURE_RUNNER_SHA256 = (
    "28e96b837368cec999e60aa595833b2fa7da1dbb1c7505461598b59967a1069e"
)
OLD_FACTOR = "intraday_intrabar_close_location_pressure_240m"
FACTOR_NAME = "intraday_range_boundary_translation_coherence_238p"
MECHANISM_AUDIT_SHA256 = (
    "0a686cacdcce6e281e1b3c7100a5230f61308f09a9acb692859c44d24fad30c7"
)
PROTOCOL_SHA256 = (
    "bf796a2b251fcd8ff717180c59d74da4e664dca85fbdb96d9d565fc801bcf61b"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "64732b36c84cf95024e615569bd5626f5951282e24a2ea534ea3f09c03fc41c8"
)
SNAPSHOT_DATASET_SHA256 = (
    "443aa07644a31721eda4a3791ea24f3726049319aaabd917cb0ad00e5551d0b7"
)
NO_RETURN_AUDIT_SHA256 = (
    "d44a4a1d0147515655e11cc5456d87ff5067d2f6e15b0a78b7b4313d0a87ac08"
)

ENDPOINT_TOLERANCE = 1e-12
WITHIN_HALF_TRANSITION_COUNT = 238

C22_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign022_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign022_feature_library_v1/snapshot_manifest.json"
)
C22_SNAPSHOT_SHA256 = (
    "987fae851b1b003ba5c171746a964f99d969bf660e99b6038feebb7deda3883c"
)
C22_DATASET_SHA256 = (
    "d3dd2cba290b662116c466d67543393c7cec4ef398bc0a6f010acbef05934e61"
)
C22_FACTOR_NAMES = ("intraday_intrabar_close_location_pressure_240m",)
C22_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C22_FACTOR_NAMES[0],
    f"{C22_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN022_FEATURE_RUNNER) != CAMPAIGN022_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign022 feature orchestration fingerprint changed")

_source = campaign022._source
for _old, _new in (
    ("Campaign022", "Campaign023"),
    ("campaign022", "campaign023"),
    ("campaign_022", "campaign_023"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "6db5024304c4142cdbb3f04529af5c21719fd16684d9c99c7befa0e5152dadd5",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "82a8a7038155c0ac40dcad5275b0a987ca7f938cf51cbbc28c050a737d468d8b",
        PROTOCOL_SHA256,
    ),
    (
        "987fae851b1b003ba5c171746a964f99d969bf660e99b6038feebb7deda3883c",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "d3dd2cba290b662116c466d67543393c7cec4ef398bc0a6f010acbef05934e61",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "cc84e8e22bae5393889853503f61f61ba5d2735ccb4c752613601490629e097b",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(sum_i(log(close_i/low_i)) - sum_i(log(high_i/close_i))) / "
    "sum_i(log(high_i/low_i)) over exactly 240 continuous-session bars"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(delta_log_high_t, delta_log_low_t) over "
    "exactly 238 adjacent transitions wholly inside the two trading halves"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign022 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign023 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign023FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign023 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign023 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign023 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign023_no_return_preregistration",
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
        == "frozen_before_campaign023_candidate_or_comparison_values_or_returns"
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
            "119 adjacent log-high/log-low boundary changes in the morning "
            "plus 119 in the afternoon; standalone 09:30 and the lunch "
            "transition are excluded."
        )
        and candidate.get("zero_change_semantics")
        == (
            "Every zero, same-sign, and opposite-sign boundary-change pair "
            "remains in the fixed 238-pair support; no filtering or bridging "
            "is allowed."
        )
        and candidate.get("variance_semantics")
        == (
            "Both complete change vectors require strictly positive "
            "population variance."
        )
        and candidate.get("bar_semantics")
        == (
            "All 240 high and low values must be finite and positive with "
            "exact low<=high; zero-range bars remain valid."
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
        and len(comparisons) == 44
        and str(comparisons[-1].get("name") or "") == C22_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
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
        raise Campaign023FeatureError(
            "Campaign023 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen within-half high/low boundary-change correlation."""

    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign023FeatureError("Campaign023 aligned array shapes are invalid")

    finite = np.isfinite(highs).all(axis=1) & np.isfinite(lows).all(axis=1)
    positive = (highs > 0.0).all(axis=1) & (lows > 0.0).all(axis=1)
    ordered = (lows <= highs).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_high = np.log(highs)
        log_low = np.log(lows)
        high_changes = np.concatenate(
            (
                np.diff(log_high[:, :120], axis=1),
                np.diff(log_high[:, 120:], axis=1),
            ),
            axis=1,
        )
        low_changes = np.concatenate(
            (
                np.diff(log_low[:, :120], axis=1),
                np.diff(log_low[:, 120:], axis=1),
            ),
            axis=1,
        )
    components_finite = (
        np.isfinite(high_changes).all(axis=1)
        & np.isfinite(low_changes).all(axis=1)
    )
    high_centered = high_changes - np.mean(high_changes, axis=1, keepdims=True)
    low_centered = low_changes - np.mean(low_changes, axis=1, keepdims=True)
    high_variance = np.mean(high_centered * high_centered, axis=1)
    low_variance = np.mean(low_centered * low_centered, axis=1)
    covariance = np.mean(high_centered * low_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_values = covariance / np.sqrt(high_variance * low_variance)

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
        required_valid & (high_variance > 0.0) & (low_variance > 0.0)
    )
    value_finite = np.isfinite(values)
    in_range = (values >= low_bound) & (values <= high_bound)
    eligible = variance_valid & value_finite & in_range
    zero_range = highs == lows
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_high_low_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_high_low_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_change_rows": int(
            (finite & positive & ordered & ~components_finite).sum()
        ),
        f"{FACTOR_NAME}__zero_range_observations": int(zero_range.sum()),
        f"{FACTOR_NAME}__rows_with_zero_range": int(zero_range.any(axis=1).sum()),
        f"{FACTOR_NAME}__zero_high_change_observations": int(
            (high_changes == 0.0).sum()
        ),
        f"{FACTOR_NAME}__zero_low_change_observations": int(
            (low_changes == 0.0).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_high_change_variance_rows": int(
            (required_valid & (high_variance <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_low_change_variance_rows": int(
            (required_valid & (low_variance <= 0.0)).sum()
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
    """Validate one source partition and compute boundary coherence."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign023FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign023FeatureError(
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
        raise Campaign023FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign023FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign023FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign023FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign023FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "high", "low"]
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
        raise Campaign023FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("high", "low")
    }
    values, eligible, quality = compute_factor_values(
        highs=arrays["high"],
        lows=arrays["low"],
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

# Final Campaign023 manifests truthfully record high/low and no close/benchmark.
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
_source = _source.replace(
    '"minute_close_read": True',
    '"minute_close_read": False',
    1,
)
_source = _source.replace(
    '"minute_close_read_by_status": True',
    '"minute_close_read_by_status": False',
    1,
)

_verify_c21 = '''        c21_manifest, c21_verification = executor._verify_prior_snapshot(
            path=C21_SNAPSHOT_PATH,
            manifest_sha256=C21_SNAPSHOT_SHA256,
            dataset_sha256=C21_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign021_feature_snapshot",
            factor_names=C21_FACTOR_NAMES,
            output_columns=C21_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c22 = _verify_c21 + '''        c22_manifest, c22_verification = executor._verify_prior_snapshot(
            path=C22_SNAPSHOT_PATH,
            manifest_sha256=C22_SNAPSHOT_SHA256,
            dataset_sha256=C22_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign022_feature_snapshot",
            factor_names=C22_FACTOR_NAMES,
            output_columns=C22_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c21 not in _source:
    raise RuntimeError("Campaign022 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c21, _verify_c22, 1)

_compare_c21 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c21_manifest,
                factors=C21_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c22 = _compare_c21 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c22_manifest,
                factors=C22_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c21 not in _source:
    raise RuntimeError("Campaign022 comparison extension block was not found")
_source = _source.replace(_compare_c21, _compare_c22, 1)
_source = _source.replace(
    "Apply coverage before all 43 frozen uniqueness comparisons.",
    "Apply coverage before all 44 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 43", "len(comparisons) == 44")
_source = _source.replace(
    '''            "campaign021_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign021_terminal_comparison_count": 1,
            "campaign022_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign021_snapshot_file_verification": c21_verification,
            "comparisons": comparisons,''',
    '''            "campaign021_snapshot_file_verification": c21_verification,
            "campaign022_snapshot_file_verification": c22_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign023_features_generated",
    "WITHIN_HALF_TRANSITION_COUNT": WITHIN_HALF_TRANSITION_COUNT,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign022.engine_namespace[_key]
_generated.update(
    {
        "C22_SNAPSHOT_PATH": C22_SNAPSHOT_PATH,
        "C22_SNAPSHOT_SHA256": C22_SNAPSHOT_SHA256,
        "C22_DATASET_SHA256": C22_DATASET_SHA256,
        "C22_FACTOR_NAMES": C22_FACTOR_NAMES,
        "C22_OUTPUT_COLUMNS": C22_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN022_FEATURE_RUNNER), "exec"), _generated)

Campaign023FeatureError = _generated["Campaign023FeatureError"]
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
