#!/usr/bin/env python3
"""Build and audit the frozen Campaign016 internal-boundary factor.

Campaign015 supplies the tested checkpoint, snapshot, coverage, and first
36-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, adds open to the OHLC source projection, and
appends the usable Campaign015 factor as comparison number 37.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign015_features as campaign015
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign015_features as campaign015


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN015_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign015_features.py"
)
CAMPAIGN015_FEATURE_RUNNER_SHA256 = (
    "5ca1a816d3f2e736871be326f97f9133012a34bb1beed7ff65c4a8d59553df99"
)
OLD_FACTOR = "intraday_prior_range_breakout_pressure_238p"
FACTOR_NAME = "intraday_interbar_gap_body_confirmation_238p"
MECHANISM_AUDIT_SHA256 = (
    "ef932893c2e6afb5f5601846cdd7ac3e84c0eee375cec5930b817776bb6429d1"
)
PROTOCOL_SHA256 = (
    "8cb26965a4a4802e8e5c68730e7aae57b8fb3883aacd8f2d38c8b9d6daec5f89"
)

# Bind these immutable fingerprints after the artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "052ff2096a18951f884825453a730fbf0175b693ec497a2faca23c5150e8830c"
)
SNAPSHOT_DATASET_SHA256 = (
    "3279806f522c347bdcd0beeef8249a89656de4204fcc22276ac53afb136c8242"
)
NO_RETURN_AUDIT_SHA256 = (
    "36e19377f5406e8beb992627b1b456fcd4d5cbe0bcb54b0e814055ef80643224"
)

C15_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign015_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign015_feature_library_v1/snapshot_manifest.json"
)
C15_SNAPSHOT_SHA256 = (
    "450cefd5b268658997841038fd45156f436b7f3645a8ba5980681370abf42811"
)
C15_DATASET_SHA256 = (
    "681c048babc594bf0b215fada4ff868d70d0a6bf450cf59cb610e22c6002747f"
)
C15_FACTOR_NAMES = ("intraday_prior_range_breakout_pressure_238p",)
C15_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C15_FACTOR_NAMES[0],
    f"{C15_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN015_FEATURE_RUNNER) != CAMPAIGN015_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign015 feature orchestration fingerprint changed")

_source = campaign015._source
for _old, _new in (
    ("Campaign015", "Campaign016"),
    ("campaign015", "campaign016"),
    ("campaign_015", "campaign_016"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "64af6fd2b9381f11495737fabd568b9c1685e0ca7793a79dc9b73d2f1dc7160e",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "ef8cfbf9d7cb1dcc50f65c2d050d9e1931c97d86f74770d4270a5b94da21609e",
        PROTOCOL_SHA256,
    ),
    (
        "450cefd5b268658997841038fd45156f436b7f3645a8ba5980681370abf42811",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "681c048babc594bf0b215fada4ff868d70d0a6bf450cf59cb610e22c6002747f",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "1f09cca7bc62445558b1e8e2cee1d42f87e7bd784fdb1e8212c897d6fb503608",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(U-D)/(U+D), where U=sum(max(log(close_t/high_(t-1)),0)) "
    "and D=sum(max(log(low_(t-1)/close_t),0)) across 238 "
    "within-half adjacent pairs"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation Corr(g_t,b_t), where "
    "g_t=log(open_t/close_(t-1)) and b_t=log(close_t/open_t) "
    "across exactly 238 within-half internal transitions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign015 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
_source = _source.replace(
    """SELECTED_BAR_COUNT = 240
WITHIN_HALF_PAIR_COUNT = 238
MINIMUM_NONZERO_BREAKOUT_PAIR_COUNT = 1""",
    """SELECTED_BAR_COUNT = 240
WITHIN_HALF_PAIR_COUNT = 238
ENDPOINT_TOLERANCE = 1e-12""",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign016 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign016FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign016 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign016 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign016 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign016_no_return_preregistration",
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
        == "frozen_before_campaign016_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == ("datetime", "symbol", "provider", "open", "close")
        and tuple(candidates[0].get("source_fields_used_only_for_validation") or ())
        == ("high", "low")
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
        and len(comparisons) == 37
        and str(comparisons[-1].get("name") or "")
        == C15_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_open_high_low_close_fields_read_before_admissibility"
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
    ):
        raise Campaign016FeatureError(
            "Campaign016 no-return protocol semantics changed"
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
    """Compute the frozen internal-boundary gap/body confirmation."""

    if (
        opens.ndim != 2
        or opens.shape[1] != SELECTED_BAR_COUNT
        or highs.shape != opens.shape
        or lows.shape != opens.shape
        or closes.shape != opens.shape
    ):
        raise Campaign016FeatureError("Campaign016 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(opens).all(axis=1)
        & np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & np.isfinite(closes).all(axis=1)
        & (opens > 0.0).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (closes > 0.0).all(axis=1)
    )
    low_high_ordering = (lows <= highs).all(axis=1)
    open_containment = ((lows <= opens) & (opens <= highs)).all(axis=1)
    close_containment = ((lows <= closes) & (closes <= highs)).all(axis=1)

    previous_positions = np.concatenate(
        [np.arange(0, 119, dtype=int), np.arange(120, 239, dtype=int)]
    )
    current_positions = previous_positions + 1
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        gaps = np.log(
            opens[:, current_positions] / closes[:, previous_positions]
        )
        bodies = np.log(
            closes[:, current_positions] / opens[:, current_positions]
        )
    components_finite = (
        np.isfinite(gaps).all(axis=1)
        & np.isfinite(bodies).all(axis=1)
    )
    gap_centered = gaps - gaps.mean(axis=1, keepdims=True)
    body_centered = bodies - bodies.mean(axis=1, keepdims=True)
    gap_sum_squares = np.sum(gap_centered * gap_centered, axis=1)
    body_sum_squares = np.sum(body_centered * body_centered, axis=1)
    cross_sum = np.sum(gap_centered * body_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denominator = np.sqrt(gap_sum_squares * body_sum_squares)
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
        finite_positive
        & low_high_ordering
        & open_containment
        & close_containment
        & components_finite
    )
    variance_valid = (
        required_valid
        & np.isfinite(gap_sum_squares)
        & np.isfinite(body_sum_squares)
        & (gap_sum_squares > 0.0)
        & (body_sum_squares > 0.0)
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
        "base_rows": int(len(opens)),
        "invalid_required_ohlc_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~low_high_ordering).sum()
        ),
        f"{FACTOR_NAME}__own_bar_open_containment_violation_rows": int(
            (finite_positive & low_high_ordering & ~open_containment).sum()
        ),
        f"{FACTOR_NAME}__own_bar_close_containment_violation_rows": int(
            (
                finite_positive
                & low_high_ordering
                & open_containment
                & ~close_containment
            ).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_gap_or_body_rows": int(
            (
                finite_positive
                & low_high_ordering
                & open_containment
                & close_containment
                & ~components_finite
            ).sum()
        ),
        f"{FACTOR_NAME}__zero_gap_variance_rows": int(
            (required_valid & (gap_sum_squares <= 0.0)).sum()
        ),
        f"{FACTOR_NAME}__zero_body_variance_rows": int(
            (required_valid & (body_sum_squares <= 0.0)).sum()
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
    """Validate one source partition and compute gap/body confirmation."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign016FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign016FeatureError(
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
        raise Campaign016FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
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
        raise Campaign016FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign016FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign016FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign016FeatureError(
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
        raise Campaign016FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
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

# Campaign016 reads open/high/low/close and forbids volume/amount.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": True,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_close_read_by_status": True,''',
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": True,
        "minute_close_read_by_status": True,''',
    1,
)

_verify_c14 = '''        c14_manifest, c14_verification = executor._verify_prior_snapshot(
            path=C14_SNAPSHOT_PATH,
            manifest_sha256=C14_SNAPSHOT_SHA256,
            dataset_sha256=C14_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign014_feature_snapshot",
            factor_names=C14_FACTOR_NAMES,
            output_columns=C14_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c15 = _verify_c14 + '''        c15_manifest, c15_verification = executor._verify_prior_snapshot(
            path=C15_SNAPSHOT_PATH,
            manifest_sha256=C15_SNAPSHOT_SHA256,
            dataset_sha256=C15_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign015_feature_snapshot",
            factor_names=C15_FACTOR_NAMES,
            output_columns=C15_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c14 not in _source:
    raise RuntimeError("Campaign015 comparison verification block was not found")
_source = _source.replace(_verify_c14, _verify_c15, 1)

_compare_c14 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c14_manifest,
                factors=C14_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c15 = _compare_c14 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c15_manifest,
                factors=C15_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c14 not in _source:
    raise RuntimeError("Campaign015 comparison extension block was not found")
_source = _source.replace(_compare_c14, _compare_c15, 1)
_source = _source.replace(
    "Apply coverage before all 36 frozen uniqueness comparisons.",
    "Apply coverage before all 37 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 36", "len(comparisons) == 37", 1)
_source = _source.replace(
    '''            "campaign014_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign014_terminal_comparison_count": 1,
            "campaign015_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign014_snapshot_file_verification": c14_verification,
            "comparisons": comparisons,''',
    '''            "campaign014_snapshot_file_verification": c14_verification,
            "campaign015_snapshot_file_verification": c15_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign016_features_generated",
    "C9_SNAPSHOT_PATH": campaign015.campaign014.campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign015.campaign014.campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign015.campaign014.campaign013.campaign012.campaign011.campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign015.campaign014.campaign013.campaign012.campaign011.campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign015.campaign014.campaign013.campaign012.campaign011.campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": campaign015.campaign014.campaign013.campaign012.campaign011.C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": campaign015.campaign014.campaign013.campaign012.campaign011.C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": campaign015.campaign014.campaign013.campaign012.campaign011.C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": campaign015.campaign014.campaign013.campaign012.campaign011.C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": campaign015.campaign014.campaign013.campaign012.campaign011.C10_OUTPUT_COLUMNS,
    "C11_SNAPSHOT_PATH": campaign015.campaign014.campaign013.campaign012.C11_SNAPSHOT_PATH,
    "C11_SNAPSHOT_SHA256": campaign015.campaign014.campaign013.campaign012.C11_SNAPSHOT_SHA256,
    "C11_DATASET_SHA256": campaign015.campaign014.campaign013.campaign012.C11_DATASET_SHA256,
    "C11_FACTOR_NAMES": campaign015.campaign014.campaign013.campaign012.C11_FACTOR_NAMES,
    "C11_OUTPUT_COLUMNS": campaign015.campaign014.campaign013.campaign012.C11_OUTPUT_COLUMNS,
    "C12_SNAPSHOT_PATH": campaign015.campaign014.campaign013.C12_SNAPSHOT_PATH,
    "C12_SNAPSHOT_SHA256": campaign015.campaign014.campaign013.C12_SNAPSHOT_SHA256,
    "C12_DATASET_SHA256": campaign015.campaign014.campaign013.C12_DATASET_SHA256,
    "C12_FACTOR_NAMES": campaign015.campaign014.campaign013.C12_FACTOR_NAMES,
    "C12_OUTPUT_COLUMNS": campaign015.campaign014.campaign013.C12_OUTPUT_COLUMNS,
    "C14_SNAPSHOT_PATH": campaign015.C14_SNAPSHOT_PATH,
    "C14_SNAPSHOT_SHA256": campaign015.C14_SNAPSHOT_SHA256,
    "C14_DATASET_SHA256": campaign015.C14_DATASET_SHA256,
    "C14_FACTOR_NAMES": campaign015.C14_FACTOR_NAMES,
    "C14_OUTPUT_COLUMNS": campaign015.C14_OUTPUT_COLUMNS,
    "C15_SNAPSHOT_PATH": C15_SNAPSHOT_PATH,
    "C15_SNAPSHOT_SHA256": C15_SNAPSHOT_SHA256,
    "C15_DATASET_SHA256": C15_DATASET_SHA256,
    "C15_FACTOR_NAMES": C15_FACTOR_NAMES,
    "C15_OUTPUT_COLUMNS": C15_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN015_FEATURE_RUNNER), "exec"), _generated)

Campaign016FeatureError = _generated["Campaign016FeatureError"]
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
