#!/usr/bin/env python3
"""Build and audit the frozen Campaign017 directional-range factor.

Campaign016 supplies the tested checkpoint, snapshot, coverage, and first
37-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, narrows the source projection to high/low,
and appends the usable Campaign016 factor as comparison number 38.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign016_features as campaign016
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign016_features as campaign016


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN016_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign016_features.py"
)
CAMPAIGN016_FEATURE_RUNNER_SHA256 = (
    "4308c106d3386891f573b4b0d0d56bac0001a80f71c635b59a08d5112e69e646"
)
OLD_FACTOR = "intraday_interbar_gap_body_confirmation_238p"
FACTOR_NAME = "intraday_midrange_width_change_coupling_238p"
MECHANISM_AUDIT_SHA256 = (
    "bd0c6487d55baad23e41713b07e94206cafb9681f54e88cf609d161ebda68f48"
)
PROTOCOL_SHA256 = (
    "4676afee54b66b558dfd96dc238cbc4d8545aa728fbcf27ec09a8681001929ba"
)

# Bind these immutable fingerprints after the artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "04b588681f64a61525407f7de5501e38244256e100d9895dbbee8635127e358a"
)
SNAPSHOT_DATASET_SHA256 = (
    "e91a17f29edbd59f82801469187ac16c8bc460e08a1c2d6110cc4b2e99e17276"
)
NO_RETURN_AUDIT_SHA256 = (
    "be1c69e7184209f74d7d86ca9be0dff4281da7984461c1d35b7de0dbc7d5da92"
)

C16_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign016_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign016_feature_library_v1/snapshot_manifest.json"
)
C16_SNAPSHOT_SHA256 = (
    "052ff2096a18951f884825453a730fbf0175b693ec497a2faca23c5150e8830c"
)
C16_DATASET_SHA256 = (
    "3279806f522c347bdcd0beeef8249a89656de4204fcc22276ac53afb136c8242"
)
C16_FACTOR_NAMES = ("intraday_interbar_gap_body_confirmation_238p",)
C16_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C16_FACTOR_NAMES[0],
    f"{C16_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN016_FEATURE_RUNNER) != CAMPAIGN016_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign016 feature orchestration fingerprint changed")

_source = campaign016._source
for _old, _new in (
    ("Campaign016", "Campaign017"),
    ("campaign016", "campaign017"),
    ("campaign_016", "campaign_017"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "ef932893c2e6afb5f5601846cdd7ac3e84c0eee375cec5930b817776bb6429d1",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "8cb26965a4a4802e8e5c68730e7aae57b8fb3883aacd8f2d38c8b9d6daec5f89",
        PROTOCOL_SHA256,
    ),
    (
        "052ff2096a18951f884825453a730fbf0175b693ec497a2faca23c5150e8830c",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "3279806f522c347bdcd0beeef8249a89656de4204fcc22276ac53afb136c8242",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "36e19377f5406e8beb992627b1b456fcd4d5cbe0bcb54b0e814055ef80643224",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation Corr(g_t,b_t), where "
    "g_t=log(open_t/close_(t-1)) and b_t=log(close_t/open_t) "
    "across exactly 238 within-half internal transitions"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation Corr(delta_m_t,delta_w_t), where "
    "m_i=(log(high_i)+log(low_i))/2 and w_i=log(high_i/low_i), "
    "across exactly 238 within-half adjacent transitions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign016 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign017 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign017FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign017 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign017 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign017 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign017_no_return_preregistration",
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
        == "frozen_before_campaign017_candidate_or_comparison_values_or_returns"
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
        and candidates[0].get("within_half_pair_count")
        == WITHIN_HALF_PAIR_COUNT
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
        and len(comparisons) == 38
        and str(comparisons[-1].get("name") or "")
        == C16_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get("minute_high_low_fields_read_before_admissibility")
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
    ):
        raise Campaign017FeatureError(
            "Campaign017 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen midrange/width-change coupling."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign017FeatureError("Campaign017 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    low_high_ordering = (lows <= highs).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_highs = np.log(highs)
        log_lows = np.log(lows)
        midranges = (log_highs + log_lows) / 2.0
        widths = log_highs - log_lows

    previous_positions = np.concatenate(
        [np.arange(0, 119, dtype=int), np.arange(120, 239, dtype=int)]
    )
    current_positions = previous_positions + 1
    midrange_changes = (
        midranges[:, current_positions] - midranges[:, previous_positions]
    )
    width_changes = (
        widths[:, current_positions] - widths[:, previous_positions]
    )
    components_finite = (
        np.isfinite(midranges).all(axis=1)
        & np.isfinite(widths).all(axis=1)
        & np.isfinite(midrange_changes).all(axis=1)
        & np.isfinite(width_changes).all(axis=1)
    )
    midrange_centered = (
        midrange_changes - midrange_changes.mean(axis=1, keepdims=True)
    )
    width_centered = width_changes - width_changes.mean(axis=1, keepdims=True)
    midrange_sum_squares = np.sum(
        midrange_centered * midrange_centered, axis=1
    )
    width_sum_squares = np.sum(width_centered * width_centered, axis=1)
    cross_sum = np.sum(midrange_centered * width_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denominator = np.sqrt(midrange_sum_squares * width_sum_squares)
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

    required_valid = finite_positive & low_high_ordering & components_finite
    variance_valid = (
        required_valid
        & np.isfinite(midrange_sum_squares)
        & np.isfinite(width_sum_squares)
        & (midrange_sum_squares > 0.0)
        & (width_sum_squares > 0.0)
    )
    denominator_valid = (
        variance_valid
        & np.isfinite(cross_sum)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = denominator_valid & finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~low_high_ordering).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_transformed_or_change_rows": int(
            (finite_positive & low_high_ordering & ~components_finite).sum()
        ),
        f"{FACTOR_NAME}__zero_midrange_change_variance_rows": int(
            (required_valid & (midrange_sum_squares <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__zero_width_change_variance_rows": int(
            (required_valid & (width_sum_squares <= 0.0)).sum()
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
            (denominator_valid & (~finite | ~in_range)).sum()
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
    """Validate one source partition and compute directional range coupling."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign017FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign017FeatureError(
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
        raise Campaign017FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
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
        raise Campaign017FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign017FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign017FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign017FeatureError(
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
        raise Campaign017FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
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

# Campaign017 reads high/low only and forbids open/close/volume/amount.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": True,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": True,
        "minute_close_read_by_status": True,''',
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,''',
    1,
)
_source = _source.replace(
    'manifest.get("source_close_read") is True',
    'manifest.get("source_close_read") is False',
)
_source = _source.replace(
    'manifest.get("source_close_read") in {None, True}',
    'manifest.get("source_close_read") in {None, False}',
)
_source = _source.replace(
    'value["source_close_read"] = True',
    'value["source_close_read"] = False',
)

_verify_c15 = '''        c15_manifest, c15_verification = executor._verify_prior_snapshot(
            path=C15_SNAPSHOT_PATH,
            manifest_sha256=C15_SNAPSHOT_SHA256,
            dataset_sha256=C15_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign015_feature_snapshot",
            factor_names=C15_FACTOR_NAMES,
            output_columns=C15_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c16 = _verify_c15 + '''        c16_manifest, c16_verification = executor._verify_prior_snapshot(
            path=C16_SNAPSHOT_PATH,
            manifest_sha256=C16_SNAPSHOT_SHA256,
            dataset_sha256=C16_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign016_feature_snapshot",
            factor_names=C16_FACTOR_NAMES,
            output_columns=C16_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c15 not in _source:
    raise RuntimeError("Campaign016 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c15, _verify_c16, 1)

_compare_c15 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c15_manifest,
                factors=C15_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c16 = _compare_c15 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c16_manifest,
                factors=C16_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c15 not in _source:
    raise RuntimeError("Campaign016 comparison extension block was not found")
_source = _source.replace(_compare_c15, _compare_c16, 1)
_source = _source.replace(
    "Apply coverage before all 37 frozen uniqueness comparisons.",
    "Apply coverage before all 38 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 37", "len(comparisons) == 38", 1)
_source = _source.replace(
    '''            "campaign015_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign015_terminal_comparison_count": 1,
            "campaign016_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign015_snapshot_file_verification": c15_verification,
            "comparisons": comparisons,''',
    '''            "campaign015_snapshot_file_verification": c15_verification,
            "campaign016_snapshot_file_verification": c16_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign017_features_generated",
    "C9_SNAPSHOT_PATH": campaign016.engine_namespace["C9_SNAPSHOT_PATH"],
    "C9_SNAPSHOT_SHA256": campaign016.engine_namespace["C9_SNAPSHOT_SHA256"],
    "C9_DATASET_SHA256": campaign016.engine_namespace["C9_DATASET_SHA256"],
    "C9_FACTOR_NAMES": campaign016.engine_namespace["C9_FACTOR_NAMES"],
    "C9_OUTPUT_COLUMNS": campaign016.engine_namespace["C9_OUTPUT_COLUMNS"],
    "C10_SNAPSHOT_PATH": campaign016.engine_namespace["C10_SNAPSHOT_PATH"],
    "C10_SNAPSHOT_SHA256": campaign016.engine_namespace["C10_SNAPSHOT_SHA256"],
    "C10_DATASET_SHA256": campaign016.engine_namespace["C10_DATASET_SHA256"],
    "C10_FACTOR_NAMES": campaign016.engine_namespace["C10_FACTOR_NAMES"],
    "C10_OUTPUT_COLUMNS": campaign016.engine_namespace["C10_OUTPUT_COLUMNS"],
    "C11_SNAPSHOT_PATH": campaign016.engine_namespace["C11_SNAPSHOT_PATH"],
    "C11_SNAPSHOT_SHA256": campaign016.engine_namespace["C11_SNAPSHOT_SHA256"],
    "C11_DATASET_SHA256": campaign016.engine_namespace["C11_DATASET_SHA256"],
    "C11_FACTOR_NAMES": campaign016.engine_namespace["C11_FACTOR_NAMES"],
    "C11_OUTPUT_COLUMNS": campaign016.engine_namespace["C11_OUTPUT_COLUMNS"],
    "C12_SNAPSHOT_PATH": campaign016.engine_namespace["C12_SNAPSHOT_PATH"],
    "C12_SNAPSHOT_SHA256": campaign016.engine_namespace["C12_SNAPSHOT_SHA256"],
    "C12_DATASET_SHA256": campaign016.engine_namespace["C12_DATASET_SHA256"],
    "C12_FACTOR_NAMES": campaign016.engine_namespace["C12_FACTOR_NAMES"],
    "C12_OUTPUT_COLUMNS": campaign016.engine_namespace["C12_OUTPUT_COLUMNS"],
    "C14_SNAPSHOT_PATH": campaign016.engine_namespace["C14_SNAPSHOT_PATH"],
    "C14_SNAPSHOT_SHA256": campaign016.engine_namespace["C14_SNAPSHOT_SHA256"],
    "C14_DATASET_SHA256": campaign016.engine_namespace["C14_DATASET_SHA256"],
    "C14_FACTOR_NAMES": campaign016.engine_namespace["C14_FACTOR_NAMES"],
    "C14_OUTPUT_COLUMNS": campaign016.engine_namespace["C14_OUTPUT_COLUMNS"],
    "C15_SNAPSHOT_PATH": campaign016.engine_namespace["C15_SNAPSHOT_PATH"],
    "C15_SNAPSHOT_SHA256": campaign016.engine_namespace["C15_SNAPSHOT_SHA256"],
    "C15_DATASET_SHA256": campaign016.engine_namespace["C15_DATASET_SHA256"],
    "C15_FACTOR_NAMES": campaign016.engine_namespace["C15_FACTOR_NAMES"],
    "C15_OUTPUT_COLUMNS": campaign016.engine_namespace["C15_OUTPUT_COLUMNS"],
    "C16_SNAPSHOT_PATH": C16_SNAPSHOT_PATH,
    "C16_SNAPSHOT_SHA256": C16_SNAPSHOT_SHA256,
    "C16_DATASET_SHA256": C16_DATASET_SHA256,
    "C16_FACTOR_NAMES": C16_FACTOR_NAMES,
    "C16_OUTPUT_COLUMNS": C16_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN016_FEATURE_RUNNER), "exec"), _generated)

Campaign017FeatureError = _generated["Campaign017FeatureError"]
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
