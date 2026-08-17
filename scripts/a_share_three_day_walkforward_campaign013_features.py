#!/usr/bin/env python3
"""Build and audit the frozen Campaign013 transaction-VWAP envelope factor.

Campaign012 supplies the already-tested checkpoint, snapshot, coverage, and
first 34-factor comparison orchestration.  This wrapper changes the campaign
namespace, replaces the factor calculation with the independently frozen
within-bar transaction-VWAP envelope asymmetry, and adds the usable terminal
Campaign012 factor as comparison number 35.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign012_features as campaign012
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign012_features as campaign012


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN012_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign012_features.py"
)
CAMPAIGN012_FEATURE_RUNNER_SHA256 = (
    "8ff031e7cdfc6e15cd62ef6dc9289b4cd509f1cd93693857d87cc9d2371b0df8"
)
OLD_FACTOR = "intraday_intrabar_range_reversal_238p"
FACTOR_NAME = "intraday_transaction_vwap_envelope_asymmetry_240m"
MECHANISM_AUDIT_SHA256 = (
    "78262a1e90af0de4561329a21217ab5304925d7694877b9f84d61771fe77a715"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "0a5c0225cba49ab11056e232b6ba9875f65c2734d318ef7644031472a9d76764"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "706e71aacb802a2b34cf7b52236823bb3e63cd30d3f0e8340456344c7ef184d7"
)
SNAPSHOT_DATASET_SHA256 = (
    "45ee0352936be01714efba01fef80118bb9fe97ee3cdfcdba65f429bf01b528b"
)
NO_RETURN_AUDIT_SHA256 = (
    "105ac63bc01828cf512be282377f835c87359a2356f29b7ff998734dcf4467b6"
)

C12_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign012_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign012_feature_library_v1/snapshot_manifest.json"
)
C12_SNAPSHOT_SHA256 = (
    "58fca32b58be53523daa0fe7a971a1394a35d4f1251c484214d06f5deff6677a"
)
C12_DATASET_SHA256 = (
    "aaa33541d55f68699e99a4a9d5abc697feafe215dd70ab1ba1c807b7cab3c18f"
)
C12_FACTOR_NAMES = ("intraday_intrabar_range_reversal_238p",)
C12_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C12_FACTOR_NAMES[0],
    f"{C12_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN012_FEATURE_RUNNER) != CAMPAIGN012_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign012 feature orchestration fingerprint changed")

_source = campaign012._source
for _old, _new in (
    ("Campaign012", "Campaign013"),
    ("campaign012", "campaign013"),
    ("campaign_012", "campaign_013"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "2311e40efb3d97a913c91fced47eff041490112b72285c60f0e3ff3a9bc25918",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "23ffe9f165cf03bdbe3a0fc1ab0119e687c8388040674f5256ccbd1c1a5ffe86",
        PROTOCOL_SHA256,
    ),
    (
        "58fca32b58be53523daa0fe7a971a1394a35d4f1251c484214d06f5deff6677a",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "aaa33541d55f68699e99a4a9d5abc697feafe215dd70ab1ba1c807b7cab3c18f",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "ddce865c259d712fefac213c2db923a292f49aa78f5e8cac8ad16dba3fc570fe",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", '
        '"volume", "amount")'
    ),
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "-PearsonCorr(x_i, y_i) across 238 within-half adjacent pairs, "
    "where x_i=log(high_t/low_t) and "
    "y_i=log(high_(t+1)/low_(t+1)); morning and afternoon each "
    "contribute 119 pairs and no lunch pair is formed"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "(sum(u_i) - sum(d_i)) / (sum(u_i) + sum(d_i)) over active "
    "09:31-11:30 and 13:01-15:00 bars, where vwap_i=amount_i/volume_i, "
    "u_i=log(high_i/vwap_i), and d_i=log(vwap_i/low_i)"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign012 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
_source = _source.replace(
    """SELECTED_BAR_COUNT = 240
ADJACENT_PAIR_COUNT = 238
MINIMUM_INFORMATIVE_PAIRS = 120
ENDPOINT_TOLERANCE = 1e-12""",
    """SELECTED_BAR_COUNT = 240
MINIMUM_INFORMATIVE_ACTIVE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12
IDENTITY_TOLERANCE = 1e-12""",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign013 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign013FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign013 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign013 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign013 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign013_no_return_preregistration",
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
        == "frozen_before_campaign013_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("minimum_informative_active_bars")
        == MINIMUM_INFORMATIVE_ACTIVE_BARS
        and candidates[0].get("activity_weighting")
        == "none; amount and volume are used only through same-bar vwap_i"
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
        and len(comparisons) == 35
        and str(comparisons[-1].get("name") or "") == C12_FACTOR_NAMES[0]
        and boundary.get("minute_high_low_fields_read_before_admissibility")
        is True
        and boundary.get("minute_volume_amount_fields_read_before_admissibility")
        is True
        and boundary.get("minute_open_field_read_before_admissibility") is False
        and boundary.get("minute_close_field_read_before_admissibility") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign013FeatureError(
            "Campaign013 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen transaction-VWAP envelope asymmetry."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
        or volumes.shape != highs.shape
        or amounts.shape != highs.shape
    ):
        raise Campaign013FeatureError("Campaign013 aligned array shapes are invalid")
    finite_positive_high_low = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordering = (lows <= highs).all(axis=1)
    activity_values_valid = (
        np.isfinite(volumes).all(axis=1)
        & np.isfinite(amounts).all(axis=1)
        & (volumes >= 0.0).all(axis=1)
        & (amounts >= 0.0).all(axis=1)
    )
    active = (volumes > 0.0) & (amounts > 0.0)
    inactive = (volumes == 0.0) & (amounts == 0.0)
    one_sided_zero = ~(active | inactive).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        bar_vwap = np.where(active, amounts / volumes, np.nan)
        upside = np.where(active, np.log(highs / bar_vwap), 0.0)
        downside = np.where(active, np.log(bar_vwap / lows), 0.0)
        active_ranges = np.where(active, np.log(highs / lows), 0.0)
    vwap_finite_positive = (
        (~active) | (np.isfinite(bar_vwap) & (bar_vwap > 0.0))
    ).all(axis=1)
    vwap_contained = (
        (~active) | ((bar_vwap >= lows) & (bar_vwap <= highs))
    ).all(axis=1)
    components_finite_nonnegative = (
        np.isfinite(upside).all(axis=1)
        & np.isfinite(downside).all(axis=1)
        & (upside >= 0.0).all(axis=1)
        & (downside >= 0.0).all(axis=1)
    )
    active_ranges_finite_nonnegative = (
        np.isfinite(active_ranges).all(axis=1)
        & (active_ranges >= 0.0).all(axis=1)
    )
    informative_active_count = (active & (highs > lows)).sum(axis=1)
    upside_sum = upside.sum(axis=1)
    downside_sum = downside.sum(axis=1)
    denominator = upside_sum + downside_sum
    active_range_sum = active_ranges.sum(axis=1)
    identity_error = np.abs(denominator - active_range_sum)
    identity_limit = IDENTITY_TOLERANCE * np.maximum(
        1.0, np.abs(active_range_sum)
    )
    identity_valid = (
        np.isfinite(identity_error)
        & np.isfinite(identity_limit)
        & (identity_error <= identity_limit)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        values = (upside_sum - downside_sum) / denominator
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    required_valid = (
        finite_positive_high_low
        & ordering
        & activity_values_valid
        & ~one_sided_zero
    )
    transaction_center_valid = (
        required_valid
        & vwap_finite_positive
        & vwap_contained
        & components_finite_nonnegative
        & active_ranges_finite_nonnegative
    )
    sufficiently_observed = (
        transaction_center_valid
        & (informative_active_count >= MINIMUM_INFORMATIVE_ACTIVE_BARS)
    )
    denominator_valid = (
        sufficiently_observed
        & np.isfinite(upside_sum)
        & np.isfinite(downside_sum)
        & np.isfinite(denominator)
        & (denominator > 0.0)
        & identity_valid
    )
    eligible = denominator_valid & finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite_positive_high_low).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive_high_low & ~ordering).sum()
        ),
        f"{FACTOR_NAME}__invalid_activity_value_rows": int(
            (finite_positive_high_low & ordering & ~activity_values_valid).sum()
        ),
        f"{FACTOR_NAME}__one_sided_zero_activity_rows": int(
            (
                finite_positive_high_low
                & ordering
                & activity_values_valid
                & one_sided_zero
            ).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_or_nonpositive_active_vwap_rows": int(
            (required_valid & ~vwap_finite_positive).sum()
        ),
        f"{FACTOR_NAME}__active_vwap_outside_high_low_rows": int(
            (required_valid & vwap_finite_positive & ~vwap_contained).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_or_negative_component_rows": int(
            (
                required_valid
                & vwap_finite_positive
                & vwap_contained
                & (
                    ~components_finite_nonnegative
                    | ~active_ranges_finite_nonnegative
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__fewer_than_120_informative_active_bar_rows": int(
            (
                transaction_center_valid
                & (
                    informative_active_count
                    < MINIMUM_INFORMATIVE_ACTIVE_BARS
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__zero_or_nonfinite_denominator_rows": int(
            (
                sufficiently_observed
                & (
                    ~np.isfinite(upside_sum)
                    | ~np.isfinite(downside_sum)
                    | ~np.isfinite(denominator)
                    | (denominator <= 0.0)
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__algebraic_identity_violation_rows": int(
            (
                sufficiently_observed
                & np.isfinite(denominator)
                & (denominator > 0.0)
                & ~identity_valid
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
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
    """Validate one source partition and compute the frozen envelope factor."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign013FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign013FeatureError(
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
        raise Campaign013FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("high", "low", "volume", "amount"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign013FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign013FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign013FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign013FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = [
        "trade_date",
        "minute_code",
        "high",
        "low",
        "volume",
        "amount",
    ]
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
        raise Campaign013FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("high", "low", "volume", "amount")
    }
    values, eligible, quality = compute_factor_values(
        highs=arrays["high"],
        lows=arrays["low"],
        volumes=arrays["volume"],
        amounts=arrays["amount"],
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

# Campaign013 reads high/low plus volume/amount and still forbids open/close.
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
    '''        and (
            manifest.get("source_amount_read") is False
            if require_fingerprint_constants
            else manifest.get("source_amount_read") in {None, False}
        )''',
    '''        and (
            manifest.get("source_amount_read") is True
            if require_fingerprint_constants
            else manifest.get("source_amount_read") in {None, True}
        )''',
    1,
)
_source = _source.replace(
    '''            value["source_volume_read"] = False
            value["source_close_read"] = False
            value["source_amount_read"] = False''',
    '''            value["source_volume_read"] = True
            value["source_close_read"] = False
            value["source_amount_read"] = True''',
    1,
)

_verify_c11 = '''        c11_manifest, c11_verification = executor._verify_prior_snapshot(
            path=C11_SNAPSHOT_PATH,
            manifest_sha256=C11_SNAPSHOT_SHA256,
            dataset_sha256=C11_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign011_feature_snapshot",
            factor_names=C11_FACTOR_NAMES,
            output_columns=C11_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c12 = _verify_c11 + '''        c12_manifest, c12_verification = executor._verify_prior_snapshot(
            path=C12_SNAPSHOT_PATH,
            manifest_sha256=C12_SNAPSHOT_SHA256,
            dataset_sha256=C12_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign012_feature_snapshot",
            factor_names=C12_FACTOR_NAMES,
            output_columns=C12_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c11 not in _source:
    raise RuntimeError("Campaign012 comparison verification block was not found")
_source = _source.replace(_verify_c11, _verify_c12, 1)

_compare_c11 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c11_manifest,
                factors=C11_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c12 = _compare_c11 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c12_manifest,
                factors=C12_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c11 not in _source:
    raise RuntimeError("Campaign012 comparison extension block was not found")
_source = _source.replace(_compare_c11, _compare_c12, 1)
_source = _source.replace(
    "Apply coverage before all 34 frozen uniqueness comparisons.",
    "Apply coverage before all 35 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 34", "len(comparisons) == 35", 1)
_source = _source.replace(
    '''            "campaign011_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign011_terminal_comparison_count": 1,
            "campaign012_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign011_snapshot_file_verification": c11_verification,
            "comparisons": comparisons,''',
    '''            "campaign011_snapshot_file_verification": c11_verification,
            "campaign012_snapshot_file_verification": c12_verification,
            "comparisons": comparisons,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": True,
        "minute_amount_read": True,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign013_features_generated",
    "C9_SNAPSHOT_PATH": campaign012.campaign011.campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign012.campaign011.campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign012.campaign011.campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign012.campaign011.campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign012.campaign011.campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": campaign012.campaign011.C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": campaign012.campaign011.C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": campaign012.campaign011.C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": campaign012.campaign011.C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": campaign012.campaign011.C10_OUTPUT_COLUMNS,
    "C11_SNAPSHOT_PATH": campaign012.C11_SNAPSHOT_PATH,
    "C11_SNAPSHOT_SHA256": campaign012.C11_SNAPSHOT_SHA256,
    "C11_DATASET_SHA256": campaign012.C11_DATASET_SHA256,
    "C11_FACTOR_NAMES": campaign012.C11_FACTOR_NAMES,
    "C11_OUTPUT_COLUMNS": campaign012.C11_OUTPUT_COLUMNS,
    "C12_SNAPSHOT_PATH": C12_SNAPSHOT_PATH,
    "C12_SNAPSHOT_SHA256": C12_SNAPSHOT_SHA256,
    "C12_DATASET_SHA256": C12_DATASET_SHA256,
    "C12_FACTOR_NAMES": C12_FACTOR_NAMES,
    "C12_OUTPUT_COLUMNS": C12_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN012_FEATURE_RUNNER), "exec"), _generated)

Campaign013FeatureError = _generated["Campaign013FeatureError"]
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
    "MINIMUM_INFORMATIVE_ACTIVE_BARS",
    "ENDPOINT_TOLERANCE",
    "IDENTITY_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
