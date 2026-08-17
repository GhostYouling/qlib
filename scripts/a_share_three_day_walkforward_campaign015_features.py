#!/usr/bin/env python3
"""Build and audit the frozen Campaign015 prior-range breakout factor.

Campaign014 supplies the tested checkpoint, snapshot, coverage, and first
35-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, adds close to the high/low source projection,
and appends the usable Campaign014 factor as comparison number 36.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign014_features as campaign014
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign014_features as campaign014


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN014_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign014_features.py"
)
CAMPAIGN014_FEATURE_RUNNER_SHA256 = (
    "ff6aaec40d57432aeb74e3197d0367f3ffe6416682357710c310913e1081d064"
)
OLD_FACTOR = "intraday_global_price_range_revisit_240m"
FACTOR_NAME = "intraday_prior_range_breakout_pressure_238p"
MECHANISM_AUDIT_SHA256 = (
    "64af6fd2b9381f11495737fabd568b9c1685e0ca7793a79dc9b73d2f1dc7160e"
)

# Bind the snapshot and no-return fingerprints after those artifacts exist.
PROTOCOL_SHA256 = (
    "ef8cfbf9d7cb1dcc50f65c2d050d9e1931c97d86f74770d4270a5b94da21609e"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "450cefd5b268658997841038fd45156f436b7f3645a8ba5980681370abf42811"
)
SNAPSHOT_DATASET_SHA256 = (
    "681c048babc594bf0b215fada4ff868d70d0a6bf450cf59cb610e22c6002747f"
)
NO_RETURN_AUDIT_SHA256 = (
    "1f09cca7bc62445558b1e8e2cee1d42f87e7bd784fdb1e8212c897d6fb503608"
)

C14_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign014_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign014_feature_library_v1/snapshot_manifest.json"
)
C14_SNAPSHOT_SHA256 = (
    "62469bb340ea9be6ee93321f4f81707c6753c30f4395ebcdd1db967efb360a67"
)
C14_DATASET_SHA256 = (
    "7bea5c1047c4c5fdde5043d5b102a337a0f28deb26bb17c94eff82b65cb317bf"
)
C14_FACTOR_NAMES = ("intraday_global_price_range_revisit_240m",)
C14_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C14_FACTOR_NAMES[0],
    f"{C14_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN014_FEATURE_RUNNER) != CAMPAIGN014_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign014 feature orchestration fingerprint changed")

_source = campaign014._source
for _old, _new in (
    ("Campaign014", "Campaign015"),
    ("campaign014", "campaign015"),
    ("campaign_014", "campaign_015"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "2c5db4acd886d57649e7ac7cc0ce2232ae8efe957412d1fdc4804fcb7bb96890",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "82e5cf3e26b6f2edc34e37651bf49026bb90d0409b97fd19bc853d71778cd16c",
        PROTOCOL_SHA256,
    ),
    (
        "62469bb340ea9be6ee93321f4f81707c6753c30f4395ebcdd1db967efb360a67",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "7bea5c1047c4c5fdde5043d5b102a337a0f28deb26bb17c94eff82b65cb317bf",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "827fa9d5079ad86e9c25545fcbe680b2e26bc17edc1506dd1d3a7c883f44819f",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(S-U)/S, where S is the sum of all 240 log high-low interval "
    "lengths and U is the exact length of their merged session-wide "
    "union in log-price space"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "(U-D)/(U+D), where U=sum(max(log(close_t/high_(t-1)),0)) "
    "and D=sum(max(log(low_(t-1)/close_t),0)) across 238 "
    "within-half adjacent pairs"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign014 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    1,
)
_source = _source.replace(
    """SELECTED_BAR_COUNT = 240
MINIMUM_POSITIVE_RANGE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12
UNION_TOLERANCE = 1e-12""",
    """SELECTED_BAR_COUNT = 240
WITHIN_HALF_PAIR_COUNT = 238
MINIMUM_NONZERO_BREAKOUT_PAIR_COUNT = 1""",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign015 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign015FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign015 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign015 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign015 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign015_no_return_preregistration",
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
        == "frozen_before_campaign015_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("within_half_pair_count")
        == WITHIN_HALF_PAIR_COUNT
        and candidates[0].get("minimum_nonzero_breakout_pair_count")
        == MINIMUM_NONZERO_BREAKOUT_PAIR_COUNT
        and candidates[0].get("boundary_semantics")
        == "the previous interval is closed; equality to its high or low is not a breakout"
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
        and len(comparisons) == 36
        and str(comparisons[-1].get("name") or "")
        == C14_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get("minute_high_low_fields_read_before_admissibility")
        is True
        and boundary.get("minute_volume_amount_fields_read_before_admissibility")
        is False
        and boundary.get("minute_open_field_read_before_admissibility") is False
        and boundary.get("minute_close_field_read_before_admissibility") is True
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign015FeatureError(
            "Campaign015 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen within-half prior-range breakout pressure."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
        or closes.shape != highs.shape
    ):
        raise Campaign015FeatureError("Campaign015 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & np.isfinite(closes).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (closes > 0.0).all(axis=1)
    )
    low_high_ordering = (lows <= highs).all(axis=1)
    close_containment = ((lows <= closes) & (closes <= highs)).all(axis=1)

    previous_positions = np.concatenate(
        [np.arange(0, 119, dtype=int), np.arange(120, 239, dtype=int)]
    )
    current_positions = previous_positions + 1
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_current_close = np.log(closes[:, current_positions])
        log_previous_high = np.log(highs[:, previous_positions])
        log_previous_low = np.log(lows[:, previous_positions])
        upward = np.maximum(log_current_close - log_previous_high, 0.0)
        downward = np.maximum(log_previous_low - log_current_close, 0.0)
    components_finite_nonnegative = (
        np.isfinite(upward).all(axis=1)
        & np.isfinite(downward).all(axis=1)
        & (upward >= 0.0).all(axis=1)
        & (downward >= 0.0).all(axis=1)
    )
    simultaneous_direction = ((upward > 0.0) & (downward > 0.0)).any(axis=1)
    nonzero_breakout_count = ((upward > 0.0) | (downward > 0.0)).sum(axis=1)
    upward_sum = upward.sum(axis=1)
    downward_sum = downward.sum(axis=1)
    denominator = upward_sum + downward_sum
    required_valid = (
        finite_positive
        & low_high_ordering
        & close_containment
        & components_finite_nonnegative
        & ~simultaneous_direction
    )
    support_valid = (
        required_valid
        & (nonzero_breakout_count >= MINIMUM_NONZERO_BREAKOUT_PAIR_COUNT)
    )
    denominator_valid = (
        support_valid
        & np.isfinite(upward_sum)
        & np.isfinite(downward_sum)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        values = (upward_sum - downward_sum) / denominator
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = denominator_valid & finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_close_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~low_high_ordering).sum()
        ),
        f"{FACTOR_NAME}__own_bar_close_containment_violation_rows": int(
            (finite_positive & low_high_ordering & ~close_containment).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_or_negative_component_rows": int(
            (
                finite_positive
                & low_high_ordering
                & close_containment
                & ~components_finite_nonnegative
            ).sum()
        ),
        f"{FACTOR_NAME}__simultaneous_up_down_component_rows": int(
            (
                finite_positive
                & low_high_ordering
                & close_containment
                & components_finite_nonnegative
                & simultaneous_direction
            ).sum()
        ),
        f"{FACTOR_NAME}__zero_breakout_denominator_rows": int(
            (required_valid & (nonzero_breakout_count == 0)).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_denominator_rows": int(
            (
                support_valid
                & (
                    ~np.isfinite(upward_sum)
                    | ~np.isfinite(downward_sum)
                    | ~np.isfinite(denominator)
                    | (denominator <= 0.0)
                )
            ).sum()
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
    """Validate one source partition and compute prior-range breakouts."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign015FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign015FeatureError(
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
        raise Campaign015FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
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
        raise Campaign015FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign015FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign015FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign015FeatureError(
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
        raise Campaign015FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
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

# Campaign015 reads high/low/close and forbids open/volume/amount.
_old_close_validation = '''        and (
            manifest.get("source_close_read") is False
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, True}
        )'''
if _old_close_validation not in _source:
    raise RuntimeError("Campaign014 close validation block was not found")
_source = _source.replace(
    _old_close_validation,
    '''        and (
            manifest.get("source_close_read") is True
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, True}
        )''',
    1,
)
_source = _source.replace(
    '''            value["source_volume_read"] = False
            value["source_close_read"] = False
            value["source_amount_read"] = False''',
    '''            value["source_volume_read"] = False
            value["source_close_read"] = True
            value["source_amount_read"] = False''',
    1,
)

_verify_c12 = '''        c12_manifest, c12_verification = executor._verify_prior_snapshot(
            path=C12_SNAPSHOT_PATH,
            manifest_sha256=C12_SNAPSHOT_SHA256,
            dataset_sha256=C12_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign012_feature_snapshot",
            factor_names=C12_FACTOR_NAMES,
            output_columns=C12_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c14 = _verify_c12 + '''        c14_manifest, c14_verification = executor._verify_prior_snapshot(
            path=C14_SNAPSHOT_PATH,
            manifest_sha256=C14_SNAPSHOT_SHA256,
            dataset_sha256=C14_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign014_feature_snapshot",
            factor_names=C14_FACTOR_NAMES,
            output_columns=C14_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c12 not in _source:
    raise RuntimeError("Campaign014 comparison verification block was not found")
_source = _source.replace(_verify_c12, _verify_c14, 1)

_compare_c12 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c12_manifest,
                factors=C12_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c14 = _compare_c12 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c14_manifest,
                factors=C14_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c12 not in _source:
    raise RuntimeError("Campaign014 comparison extension block was not found")
_source = _source.replace(_compare_c12, _compare_c14, 1)
_source = _source.replace(
    "Apply coverage before all 35 frozen uniqueness comparisons.",
    "Apply coverage before all 36 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 35", "len(comparisons) == 36", 1)
_source = _source.replace(
    '''            "campaign012_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign012_terminal_comparison_count": 1,
            "campaign014_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign012_snapshot_file_verification": c12_verification,
            "comparisons": comparisons,''',
    '''            "campaign012_snapshot_file_verification": c12_verification,
            "campaign014_snapshot_file_verification": c14_verification,
            "comparisons": comparisons,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '"minute_close_read_by_status": False',
    '"minute_close_read_by_status": True',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign015_features_generated",
    "C9_SNAPSHOT_PATH": campaign014.campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign014.campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign014.campaign013.campaign012.campaign011.campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign014.campaign013.campaign012.campaign011.campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign014.campaign013.campaign012.campaign011.campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": campaign014.campaign013.campaign012.campaign011.C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": campaign014.campaign013.campaign012.campaign011.C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": campaign014.campaign013.campaign012.campaign011.C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": campaign014.campaign013.campaign012.campaign011.C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": campaign014.campaign013.campaign012.campaign011.C10_OUTPUT_COLUMNS,
    "C11_SNAPSHOT_PATH": campaign014.campaign013.campaign012.C11_SNAPSHOT_PATH,
    "C11_SNAPSHOT_SHA256": campaign014.campaign013.campaign012.C11_SNAPSHOT_SHA256,
    "C11_DATASET_SHA256": campaign014.campaign013.campaign012.C11_DATASET_SHA256,
    "C11_FACTOR_NAMES": campaign014.campaign013.campaign012.C11_FACTOR_NAMES,
    "C11_OUTPUT_COLUMNS": campaign014.campaign013.campaign012.C11_OUTPUT_COLUMNS,
    "C12_SNAPSHOT_PATH": campaign014.campaign013.C12_SNAPSHOT_PATH,
    "C12_SNAPSHOT_SHA256": campaign014.campaign013.C12_SNAPSHOT_SHA256,
    "C12_DATASET_SHA256": campaign014.campaign013.C12_DATASET_SHA256,
    "C12_FACTOR_NAMES": campaign014.campaign013.C12_FACTOR_NAMES,
    "C12_OUTPUT_COLUMNS": campaign014.campaign013.C12_OUTPUT_COLUMNS,
    "C14_SNAPSHOT_PATH": C14_SNAPSHOT_PATH,
    "C14_SNAPSHOT_SHA256": C14_SNAPSHOT_SHA256,
    "C14_DATASET_SHA256": C14_DATASET_SHA256,
    "C14_FACTOR_NAMES": C14_FACTOR_NAMES,
    "C14_OUTPUT_COLUMNS": C14_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN014_FEATURE_RUNNER), "exec"), _generated)

Campaign015FeatureError = _generated["Campaign015FeatureError"]
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
    "MINIMUM_NONZERO_BREAKOUT_PAIR_COUNT",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
