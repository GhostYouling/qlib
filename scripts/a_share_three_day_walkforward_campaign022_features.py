#!/usr/bin/env python3
"""Build and no-return audit the frozen Campaign022 close-location factor.

Campaign021 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
high/low/close from each complete continuous-session minute bar, removes the
Campaign021-only market benchmark, and appends Campaign021 as comparison 43.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign021_features as campaign021
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign021_features as campaign021


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN021_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign021_features.py"
)
CAMPAIGN021_FEATURE_RUNNER_SHA256 = (
    "e248ba871152236e8831d422e71b1abfabac644884e79f4528a1de7b9d6fb83a"
)
OLD_FACTOR = "intraday_market_response_delay_asymmetry_236p"
FACTOR_NAME = "intraday_intrabar_close_location_pressure_240m"
MECHANISM_AUDIT_SHA256 = (
    "6db5024304c4142cdbb3f04529af5c21719fd16684d9c99c7befa0e5152dadd5"
)
PROTOCOL_SHA256 = (
    "82a8a7038155c0ac40dcad5275b0a987ca7f938cf51cbbc28c050a737d468d8b"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "987fae851b1b003ba5c171746a964f99d969bf660e99b6038feebb7deda3883c"
)
SNAPSHOT_DATASET_SHA256 = (
    "d3dd2cba290b662116c466d67543393c7cec4ef398bc0a6f010acbef05934e61"
)
NO_RETURN_AUDIT_SHA256 = (
    "cc84e8e22bae5393889853503f61f61ba5d2735ccb4c752613601490629e097b"
)

MINIMUM_POSITIVE_RANGE_BAR_COUNT = 120
ENDPOINT_TOLERANCE = 1e-12

C21_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign021_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign021_feature_library_v1/snapshot_manifest.json"
)
C21_SNAPSHOT_SHA256 = (
    "05b1d511d9c53c1167ee97015c762b0882ab21469258fd9562eab7b28e8a24f2"
)
C21_DATASET_SHA256 = (
    "1557eb872713ee5456fdfd0caef1d6aae6b2e9d43951afd5ca7f7b93766429a2"
)
C21_FACTOR_NAMES = ("intraday_market_response_delay_asymmetry_236p",)
C21_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C21_FACTOR_NAMES[0],
    f"{C21_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN021_FEATURE_RUNNER) != CAMPAIGN021_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign021 feature orchestration fingerprint changed")

_source = campaign021._source
for _old, _new in (
    ("Campaign021", "Campaign022"),
    ("campaign021", "campaign022"),
    ("campaign_021", "campaign_022"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "056988a36deb220a221fe46bde5e9554628cd078f258684869ca9dc30c262ad7",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "6daee3570af9fa29ca29bb0e3b642b525d9822c8f94b99e3b1e36e20e37e43b7",
        PROTOCOL_SHA256,
    ),
    (
        "05b1d511d9c53c1167ee97015c762b0882ab21469258fd9562eab7b28e8a24f2",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "1557eb872713ee5456fdfd0caef1d6aae6b2e9d43951afd5ca7f7b93766429a2",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "b198a2deec6d31634adb4ac00b10f8c22a18cd70739f8ce10c2dd2cd70068623",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
    1,
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (-2.0, 2.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(r_i,t,m_-i,t-1) minus population "
    "PearsonCorr(r_i,t-1,m_-i,t) over exactly 236 adjacent return "
    "pairs wholly inside the two trading halves"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "(sum_i(log(close_i/low_i)) - sum_i(log(high_i/close_i))) / "
    "sum_i(log(high_i/low_i)) over exactly 240 continuous-session bars"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign021 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign022 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign022FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign022 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign022 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign022 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign022_no_return_preregistration",
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
        == "frozen_before_campaign022_candidate_or_comparison_values_or_returns"
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
        and candidate.get("minimum_positive_range_bar_count")
        == MINIMUM_POSITIVE_RANGE_BAR_COUNT
        and candidate.get("zero_range_semantics")
        == (
            "A zero-range bar remains in the fixed 240-bar support and "
            "contributes exactly zero to lower distance, upper distance, "
            "and total range."
        )
        and candidate.get("aggregation")
        == "ratio_of_full_day_summed_log_distances"
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
        and len(comparisons) == 43
        and str(comparisons[-1].get("name") or "") == C21_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_high_low_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_volume_amount_fields_read_before_admissibility"
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
        raise Campaign022FeatureError(
            "Campaign022 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen full-day ratio of signed within-bar close location."""

    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    closes = np.asarray(closes, dtype=float)
    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
        or closes.shape != highs.shape
    ):
        raise Campaign022FeatureError("Campaign022 aligned array shapes are invalid")

    finite = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & np.isfinite(closes).all(axis=1)
    )
    positive = (
        (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (closes > 0.0).all(axis=1)
    )
    ordered = ((lows <= closes) & (closes <= highs)).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_range = np.log(highs) - np.log(lows)
        lower_distance = np.log(closes) - np.log(lows)
        upper_distance = np.log(highs) - np.log(closes)
    components_finite = (
        np.isfinite(log_range).all(axis=1)
        & np.isfinite(lower_distance).all(axis=1)
        & np.isfinite(upper_distance).all(axis=1)
    )
    positive_range_count = (log_range > 0.0).sum(axis=1)
    total_range = np.sum(log_range, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_values = (
            np.sum(lower_distance, axis=1)
            - np.sum(upper_distance, axis=1)
        ) / total_range

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
    support_valid = (
        required_valid
        & (positive_range_count >= MINIMUM_POSITIVE_RANGE_BAR_COUNT)
        & (total_range > 0.0)
    )
    value_finite = np.isfinite(values)
    in_range = (values >= low_bound) & (values <= high_bound)
    eligible = support_valid & value_finite & in_range
    zero_range = log_range == 0.0
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_close_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_high_low_close_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__misordered_high_low_close_rows": int(
            (finite & positive & ~ordered).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_log_component_rows": int(
            (finite & positive & ordered & ~components_finite).sum()
        ),
        f"{FACTOR_NAME}__zero_range_observations": int(zero_range.sum()),
        f"{FACTOR_NAME}__rows_with_zero_range": int(zero_range.any(axis=1).sum()),
        f"{FACTOR_NAME}__insufficient_positive_range_rows": int(
            (
                required_valid
                & (
                    positive_range_count
                    < MINIMUM_POSITIVE_RANGE_BAR_COUNT
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_total_range_rows": int(
            (required_valid & (total_range <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (support_valid & (~value_finite | ~in_range)).sum()
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
    """Validate one source partition and compute close-location pressure."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign022FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign022FeatureError(
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
        raise Campaign022FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("high", "low", "close"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign022FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign022FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign022FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign022FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "high", "low", "close"]
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
        raise Campaign022FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("high", "low", "close")
    }
    values, eligible, quality = compute_factor_values(
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
_compute_start = _source.index("def _population_correlation(", _loader_start)
_partition_start = _source.index("_MARKET_BENCHMARK_CACHE:", _compute_start)
_configure_start = _source.index("def _configure_engine(", _partition_start)
_source = (
    _source[:_loader_start]
    + _new_loader
    + _new_compute
    + _new_partition
    + _source[_configure_start:]
)

# Final Campaign022 manifests truthfully record high/low/close and no benchmark.
_source = _source.replace(
    '        and manifest.get("source_open_high_low_read") is False',
    '''        and (
            manifest.get("source_open_high_low_read") is True
            if require_fingerprint_constants
            else manifest.get("source_open_high_low_read") is False
        )''',
    1,
)
_benchmark_validation = '''        and (
            manifest.get("market_benchmark_manifest_sha256")
            == MARKET_BENCHMARK_MANIFEST_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_manifest_sha256") is None
        )
        and (
            manifest.get("market_benchmark_byte_sha256")
            == MARKET_BENCHMARK_BYTE_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_byte_sha256") is None
        )
        and (
            manifest.get("market_benchmark_frame_sha256")
            == MARKET_BENCHMARK_FRAME_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_frame_sha256") is None
        )
'''
if _benchmark_validation not in _source:
    raise RuntimeError("Campaign021 benchmark manifest validation was not found")
_source = _source.replace(_benchmark_validation, "", 1)
_source = _source.replace(
    '            value["source_open_high_low_read"] = False',
    '            value["source_open_high_low_read"] = True',
    1,
)
_benchmark_injection = '''            value["market_benchmark_manifest_sha256"] = (
                MARKET_BENCHMARK_MANIFEST_SHA256
            )
            value["market_benchmark_byte_sha256"] = (
                MARKET_BENCHMARK_BYTE_SHA256
            )
            value["market_benchmark_frame_sha256"] = (
                MARKET_BENCHMARK_FRAME_SHA256
            )
            value["market_benchmark_fields_read"] = list(
                market.BENCHMARK_COLUMNS
            )
'''
if _benchmark_injection not in _source:
    raise RuntimeError("Campaign021 benchmark manifest injection was not found")
_source = _source.replace(_benchmark_injection, "", 1)
_source = _source.replace(
    '        "market_benchmark_fields_read": list(market.BENCHMARK_COLUMNS),\n',
    "",
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": True,
        "minute_close_read": True,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": True,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": False,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": True,''',
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": True,''',
    1,
)

_verify_c20 = '''        c20_manifest, c20_verification = executor._verify_prior_snapshot(
            path=C20_SNAPSHOT_PATH,
            manifest_sha256=C20_SNAPSHOT_SHA256,
            dataset_sha256=C20_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign020_feature_snapshot",
            factor_names=C20_FACTOR_NAMES,
            output_columns=C20_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c21 = _verify_c20 + '''        c21_manifest, c21_verification = executor._verify_prior_snapshot(
            path=C21_SNAPSHOT_PATH,
            manifest_sha256=C21_SNAPSHOT_SHA256,
            dataset_sha256=C21_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign021_feature_snapshot",
            factor_names=C21_FACTOR_NAMES,
            output_columns=C21_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c20 not in _source:
    raise RuntimeError("Campaign021 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c20, _verify_c21, 1)

_compare_c20 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c20_manifest,
                factors=C20_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c21 = _compare_c20 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c21_manifest,
                factors=C21_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c20 not in _source:
    raise RuntimeError("Campaign021 comparison extension block was not found")
_source = _source.replace(_compare_c20, _compare_c21, 1)
_source = _source.replace(
    "Apply coverage before all 42 frozen uniqueness comparisons.",
    "Apply coverage before all 43 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 42", "len(comparisons) == 43", 1)
_source = _source.replace(
    '''            "campaign020_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign020_terminal_comparison_count": 1,
            "campaign021_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign020_snapshot_file_verification": c20_verification,
            "comparisons": comparisons,''',
    '''            "campaign020_snapshot_file_verification": c20_verification,
            "campaign021_snapshot_file_verification": c21_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign022_features_generated",
    "MINIMUM_POSITIVE_RANGE_BAR_COUNT": MINIMUM_POSITIVE_RANGE_BAR_COUNT,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign021.engine_namespace[_key]
_generated.update(
    {
        "C21_SNAPSHOT_PATH": C21_SNAPSHOT_PATH,
        "C21_SNAPSHOT_SHA256": C21_SNAPSHOT_SHA256,
        "C21_DATASET_SHA256": C21_DATASET_SHA256,
        "C21_FACTOR_NAMES": C21_FACTOR_NAMES,
        "C21_OUTPUT_COLUMNS": C21_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN021_FEATURE_RUNNER), "exec"), _generated)

Campaign022FeatureError = _generated["Campaign022FeatureError"]
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
