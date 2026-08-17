#!/usr/bin/env python3
"""Build and audit the frozen Campaign018 range-volume factor.

Campaign017 supplies the tested checkpoint, snapshot, coverage, and first
38-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, expands the source projection to
high/low/volume, and appends the usable Campaign017 factor as comparison 39.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign017_features as campaign017
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign017_features as campaign017


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN017_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign017_features.py"
)
CAMPAIGN017_FEATURE_RUNNER_SHA256 = (
    "527c0d1223a87d31d4cd24feee74774e39c07ec672393c9261cbf986e81bdeda"
)
OLD_FACTOR = "intraday_midrange_width_change_coupling_238p"
FACTOR_NAME = "intraday_range_share_volume_confirmation_240m"
MECHANISM_AUDIT_SHA256 = (
    "20cab7f44607e53c9af0a3bf95eee96a13711c3e72b051038d1b0bcccbf044e5"
)
PROTOCOL_SHA256 = (
    "5cc74329648ce47787291d2f4b5c960084ca1a0fc148284170e1a23d429c1fe6"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "9fe343dc34d57e59c3a5d12fb3d159b10e9d98cdd02cf1ce8c82b77fbbdb37a0"
)
SNAPSHOT_DATASET_SHA256 = (
    "7762728e0a7d94dcddb1bcfb21531d4b66f98620a0282ffe501767c7e4f607be"
)
NO_RETURN_AUDIT_SHA256 = (
    "16e8c23e8a4cac9d7e0e70649cf9f1b01e809b61459c7dbbc71b55870a4f58ff"
)

C17_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign017_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign017_feature_library_v1/snapshot_manifest.json"
)
C17_SNAPSHOT_SHA256 = (
    "04b588681f64a61525407f7de5501e38244256e100d9895dbbee8635127e358a"
)
C17_DATASET_SHA256 = (
    "e91a17f29edbd59f82801469187ac16c8bc460e08a1c2d6110cc4b2e99e17276"
)
C17_FACTOR_NAMES = ("intraday_midrange_width_change_coupling_238p",)
C17_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C17_FACTOR_NAMES[0],
    f"{C17_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN017_FEATURE_RUNNER) != CAMPAIGN017_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign017 feature orchestration fingerprint changed")

_source = campaign017._source
for _old, _new in (
    ("Campaign017", "Campaign018"),
    ("campaign017", "campaign018"),
    ("campaign_017", "campaign_018"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "bd0c6487d55baad23e41713b07e94206cafb9681f54e88cf609d161ebda68f48",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "4676afee54b66b558dfd96dc238cbc4d8545aa728fbcf27ec09a8681001929ba",
        PROTOCOL_SHA256,
    ),
    (
        "04b588681f64a61525407f7de5501e38244256e100d9895dbbee8635127e358a",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "e91a17f29edbd59f82801469187ac16c8bc460e08a1c2d6110cc4b2e99e17276",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "be1c69e7184209f74d7d86ca9be0dff4281da7984461c1d35b7de0dbc7d5da92",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "volume")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation Corr(delta_m_t,delta_w_t), where "
    "m_i=(log(high_i)+log(low_i))/2 and w_i=log(high_i/low_i), "
    "across exactly 238 within-half adjacent transitions"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation "
    "Corr(log(high_i/low_i),log1p(volume_i)) across exactly 240 "
    "continuous-session bars"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign017 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign018 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign018FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign018 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign018 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign018 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign018_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
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
        == "frozen_before_campaign018_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_only_for_validation") or ())
        == ()
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("within_half_pair_count") is None
        and candidates[0].get("minimum_nonzero_pair_count") is None
        and candidates[0].get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts")
        == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 39
        and str(comparisons[-1].get("name") or "")
        == C17_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_high_low_volume_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_close_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign018FeatureError(
            "Campaign018 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen range/share-volume confirmation."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
        or volumes.shape != highs.shape
    ):
        raise Campaign018FeatureError("Campaign018 aligned array shapes are invalid")
    finite = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & np.isfinite(volumes).all(axis=1)
    )
    price_positive = (highs > 0.0).all(axis=1) & (lows > 0.0).all(axis=1)
    low_high_ordering = (lows <= highs).all(axis=1)
    volume_nonnegative = (volumes >= 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_ranges = np.log(highs) - np.log(lows)
        log_volumes = np.log1p(volumes)
    components_finite = (
        np.isfinite(log_ranges).all(axis=1)
        & np.isfinite(log_volumes).all(axis=1)
    )
    range_centered = log_ranges - log_ranges.mean(axis=1, keepdims=True)
    volume_centered = log_volumes - log_volumes.mean(axis=1, keepdims=True)
    range_sum_squares = np.sum(range_centered * range_centered, axis=1)
    volume_sum_squares = np.sum(volume_centered * volume_centered, axis=1)
    cross_sum = np.sum(range_centered * volume_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denominator = np.sqrt(range_sum_squares * volume_sum_squares)
        raw_values = cross_sum / denominator
    values = raw_values.copy()
    upper_endpoint = (
        (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    )
    lower_endpoint = (
        (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    )
    values = np.where(upper_endpoint, 1.0, values)
    values = np.where(lower_endpoint, -1.0, values)

    required_valid = (
        finite
        & price_positive
        & low_high_ordering
        & volume_nonnegative
        & components_finite
    )
    variance_valid = (
        required_valid
        & np.isfinite(range_sum_squares)
        & np.isfinite(volume_sum_squares)
        & (range_sum_squares > 0.0)
        & (volume_sum_squares > 0.0)
    )
    denominator_valid = (
        variance_valid
        & np.isfinite(cross_sum)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )
    value_finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = denominator_valid & value_finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_volume_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_high_low_rows": int(
            (finite & ~price_positive).sum()
        ),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite & price_positive & ~low_high_ordering).sum()
        ),
        f"{FACTOR_NAME}__negative_volume_rows": int(
            (finite & price_positive & low_high_ordering & ~volume_nonnegative).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_transformed_rows": int(
            (
                finite
                & price_positive
                & low_high_ordering
                & volume_nonnegative
                & ~components_finite
            ).sum()
        ),
        f"{FACTOR_NAME}__zero_range_variance_rows": int(
            (required_valid & (range_sum_squares <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__zero_volume_variance_rows": int(
            (required_valid & (volume_sum_squares <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_denominator_rows": int(
            (
                variance_valid
                & (
                    ~np.isfinite(cross_sum)
                    | ~np.isfinite(denominator)
                    | (denominator <= 0.0)
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalization_rows": int(
            (denominator_valid & (upper_endpoint | lower_endpoint)).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (denominator_valid & (~value_finite | ~in_range)).sum()
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
    """Validate one source partition and compute range-volume confirmation."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign018FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign018FeatureError(
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
        raise Campaign018FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("high", "low", "volume"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign018FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign018FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign018FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign018FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "high", "low", "volume"]
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
        raise Campaign018FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("high", "low", "volume")
    }
    values, eligible, quality = compute_factor_values(
        highs=arrays["high"],
        lows=arrays["low"],
        volumes=arrays["volume"],
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

# Campaign018 reads high/low/volume and forbids open/close/amount.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": True,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,
        "minute_volume_read_by_status": False,''',
    '''        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,
        "minute_volume_read_by_status": True,''',
    1,
)
_source = _source.replace(
    '''        and (
            manifest.get("source_volume_read") is False
            if require_fingerprint_constants
            else manifest.get("source_volume_read") is True
        )''',
    '''        and manifest.get("source_volume_read") is True''',
    1,
)
_source = _source.replace(
    'value["source_volume_read"] = False',
    'value["source_volume_read"] = True',
    1,
)

_verify_c16 = '''        c16_manifest, c16_verification = executor._verify_prior_snapshot(
            path=C16_SNAPSHOT_PATH,
            manifest_sha256=C16_SNAPSHOT_SHA256,
            dataset_sha256=C16_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign016_feature_snapshot",
            factor_names=C16_FACTOR_NAMES,
            output_columns=C16_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c17 = _verify_c16 + '''        c17_manifest, c17_verification = executor._verify_prior_snapshot(
            path=C17_SNAPSHOT_PATH,
            manifest_sha256=C17_SNAPSHOT_SHA256,
            dataset_sha256=C17_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign017_feature_snapshot",
            factor_names=C17_FACTOR_NAMES,
            output_columns=C17_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c16 not in _source:
    raise RuntimeError("Campaign017 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c16, _verify_c17, 1)

_compare_c16 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c16_manifest,
                factors=C16_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c17 = _compare_c16 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c17_manifest,
                factors=C17_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c16 not in _source:
    raise RuntimeError("Campaign017 comparison extension block was not found")
_source = _source.replace(_compare_c16, _compare_c17, 1)
_source = _source.replace(
    "Apply coverage before all 38 frozen uniqueness comparisons.",
    "Apply coverage before all 39 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 38", "len(comparisons) == 39", 1)
_source = _source.replace(
    '''            "campaign016_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign016_terminal_comparison_count": 1,
            "campaign017_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign016_snapshot_file_verification": c16_verification,
            "comparisons": comparisons,''',
    '''            "campaign016_snapshot_file_verification": c16_verification,
            "campaign017_snapshot_file_verification": c17_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign018_features_generated",
}
for _campaign in (9, 10, 11, 12, 14, 15, 16):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign017.engine_namespace[_key]
_generated.update(
    {
        "C17_SNAPSHOT_PATH": C17_SNAPSHOT_PATH,
        "C17_SNAPSHOT_SHA256": C17_SNAPSHOT_SHA256,
        "C17_DATASET_SHA256": C17_DATASET_SHA256,
        "C17_FACTOR_NAMES": C17_FACTOR_NAMES,
        "C17_OUTPUT_COLUMNS": C17_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN017_FEATURE_RUNNER), "exec"), _generated)

Campaign018FeatureError = _generated["Campaign018FeatureError"]
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
    "FACTOR_NAME",
    "FACTOR_NAMES",
    "FACTOR_DIRECTIONS",
    "FACTOR_RANGES",
    "FACTOR_FORMULA",
    "FACTOR_FORMULAS",
    "OUTPUT_COLUMNS",
    "SELECTED_BAR_COUNT",
    "WITHIN_HALF_PAIR_COUNT",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
