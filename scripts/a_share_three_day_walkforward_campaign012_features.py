#!/usr/bin/env python3
"""Build and audit the frozen Campaign012 intrabar-range reversal factor.

Campaign011 supplies only the already-tested checkpoint, snapshot, coverage,
and first 33-factor comparison orchestration. This wrapper deterministically
changes the campaign namespace, replaces the factor calculation with the
independently preregistered within-half lag-one range reversal, and adds the
usable terminal Campaign011 factor as comparison number 34.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign011_features as campaign011
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign011_features as campaign011


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN011_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign011_features.py"
)
CAMPAIGN011_FEATURE_RUNNER_SHA256 = (
    "48888fd4a686371bc0b0baf887f4a682beac192f4a73dd83bcc3916e44f2a61d"
)
OLD_FACTOR = "intraday_intrabar_range_participation_entropy_240m"
FACTOR_NAME = "intraday_intrabar_range_reversal_238p"
MECHANISM_AUDIT_SHA256 = (
    "2311e40efb3d97a913c91fced47eff041490112b72285c60f0e3ff3a9bc25918"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "23ffe9f165cf03bdbe3a0fc1ab0119e687c8388040674f5256ccbd1c1a5ffe86"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "58fca32b58be53523daa0fe7a971a1394a35d4f1251c484214d06f5deff6677a"
)
SNAPSHOT_DATASET_SHA256 = (
    "aaa33541d55f68699e99a4a9d5abc697feafe215dd70ab1ba1c807b7cab3c18f"
)
NO_RETURN_AUDIT_SHA256 = (
    "ddce865c259d712fefac213c2db923a292f49aa78f5e8cac8ad16dba3fc570fe"
)

C11_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign011_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign011_feature_library_v1/snapshot_manifest.json"
)
C11_SNAPSHOT_SHA256 = (
    "36efe15038681d3a2fc154dfd3ce6d918c54ab56d1a5e803ee7aa86c295f4084"
)
C11_DATASET_SHA256 = (
    "078dcb053e641813978ed96542fb9c69fbf3108ac490d3463e870b640feeee11"
)
C11_FACTOR_NAMES = ("intraday_intrabar_range_participation_entropy_240m",)
C11_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C11_FACTOR_NAMES[0],
    f"{C11_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN011_FEATURE_RUNNER) != CAMPAIGN011_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign011 feature orchestration fingerprint changed")

_source = campaign011._source
for _old, _new in (
    ("Campaign011", "Campaign012"),
    ("campaign011", "campaign012"),
    ("campaign_011", "campaign_012"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "fe50e938523f49fe8038e72036b2d3d7c8a08ef3c5870747d5f967b910679eed",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "3e530c7a2f76e6a1eecdb18c6058a1d20fb1e3e54aaffb5ae4b3a857d5112e56",
        PROTOCOL_SHA256,
    ),
    (
        "36efe15038681d3a2fc154dfd3ce6d918c54ab56d1a5e803ee7aa86c295f4084",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "078dcb053e641813978ed96542fb9c69fbf3108ac490d3463e870b640feeee11",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "1c07ddba4d3447016aa9460e6a9018b33eb380246cd672fbbb533d397066e995",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "-sum(p_i * log(p_i)) / log(240), where p_i = "
    "log(high_i/low_i) / sum_j(log(high_j/low_j)) across the 240 "
    "continuous-session bars and zero-range terms contribute zero"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "-PearsonCorr(x_i, y_i) across 238 within-half adjacent pairs, "
    "where x_i=log(high_t/low_t) and "
    "y_i=log(high_(t+1)/low_(t+1)); morning and afternoon each "
    "contribute 119 pairs and no lunch pair is formed"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign011 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    1,
)
_source = _source.replace(
    """SELECTED_BAR_COUNT = 240
MINIMUM_POSITIVE_RANGE_BARS = 120
ENTROPY_SUPPORT_BAR_COUNT = 240
ENDPOINT_TOLERANCE = 1e-12""",
    """SELECTED_BAR_COUNT = 240
ADJACENT_PAIR_COUNT = 238
MINIMUM_INFORMATIVE_PAIRS = 120
ENDPOINT_TOLERANCE = 1e-12""",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign012 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign012FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign012 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign012 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign012 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign012_no_return_preregistration",
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
        == "frozen_before_campaign012_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("adjacent_pair_count") == ADJACENT_PAIR_COUNT
        and candidates[0].get("minimum_informative_pairs")
        == MINIMUM_INFORMATIVE_PAIRS
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
        and len(comparisons) == 34
        and str(comparisons[-1].get("name") or "") == C11_FACTOR_NAMES[0]
        and boundary.get("minute_open_high_low_fields_read_before_admissibility")
        is True
        and boundary.get("minute_close_field_read_before_admissibility") is False
        and boundary.get("minute_volume_field_read_before_admissibility") is False
        and boundary.get("minute_amount_field_read_before_admissibility") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign012FeatureError(
            "Campaign012 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen within-half lag-one intrabar-range reversal."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign012FeatureError("Campaign012 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordering = (lows <= highs).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_ranges = np.log(highs / lows)
    nonnegative_ranges = (log_ranges >= 0.0).all(axis=1)
    finite_ranges = np.isfinite(log_ranges).all(axis=1)
    lags = np.concatenate(
        (log_ranges[:, :119], log_ranges[:, 120:239]),
        axis=1,
    )
    leads = np.concatenate(
        (log_ranges[:, 1:120], log_ranges[:, 121:240]),
        axis=1,
    )
    if lags.shape[1] != ADJACENT_PAIR_COUNT or leads.shape != lags.shape:
        raise Campaign012FeatureError("Campaign012 pair construction changed")
    informative_pair_count = ((lags > 0.0) | (leads > 0.0)).sum(axis=1)
    lag_centered = lags - lags.mean(axis=1, keepdims=True)
    lead_centered = leads - leads.mean(axis=1, keepdims=True)
    lag_ss = np.square(lag_centered).sum(axis=1)
    lead_ss = np.square(lead_centered).sum(axis=1)
    covariance_sum = (lag_centered * lead_centered).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        denominator = np.sqrt(lag_ss * lead_ss)
        values = -(covariance_sum / denominator)
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    valid_ordered = finite_positive & ordering & finite_ranges & nonnegative_ranges
    sufficiently_observed = (
        valid_ordered
        & (informative_pair_count >= MINIMUM_INFORMATIVE_PAIRS)
    )
    nondegenerate = (
        sufficiently_observed
        & np.isfinite(lag_ss)
        & np.isfinite(lead_ss)
        & (lag_ss > 0.0)
        & (lead_ss > 0.0)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )
    eligible = nondegenerate & finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~ordering).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_or_negative_log_range_rows": int(
            (finite_positive & ordering & (~finite_ranges | ~nonnegative_ranges)).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__fewer_than_120_informative_pair_rows": int(
            (
                valid_ordered
                & (informative_pair_count < MINIMUM_INFORMATIVE_PAIRS)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_lag_or_lead_variance_rows": int(
            (
                sufficiently_observed
                & (
                    ~np.isfinite(lag_ss)
                    | ~np.isfinite(lead_ss)
                    | (lag_ss <= 0.0)
                    | (lead_ss <= 0.0)
                    | ~np.isfinite(denominator)
                    | (denominator <= 0.0)
                )
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (nondegenerate & (~finite | ~in_range)).sum()
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
    """Validate one source partition and compute the frozen range reversal."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign012FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign012FeatureError(
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
        raise Campaign012FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign012FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign012FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign012FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign012FeatureError(
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
        raise Campaign012FeatureError(
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

_verify_c10 = '''        c10_manifest, c10_verification = executor._verify_prior_snapshot(
            path=C10_SNAPSHOT_PATH,
            manifest_sha256=C10_SNAPSHOT_SHA256,
            dataset_sha256=C10_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign010_feature_snapshot",
            factor_names=C10_FACTOR_NAMES,
            output_columns=C10_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c11 = _verify_c10 + '''        c11_manifest, c11_verification = executor._verify_prior_snapshot(
            path=C11_SNAPSHOT_PATH,
            manifest_sha256=C11_SNAPSHOT_SHA256,
            dataset_sha256=C11_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign011_feature_snapshot",
            factor_names=C11_FACTOR_NAMES,
            output_columns=C11_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c10 not in _source:
    raise RuntimeError("Campaign011 comparison verification block was not found")
_source = _source.replace(_verify_c10, _verify_c11, 1)

_compare_c10 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c10_manifest,
                factors=C10_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c11 = _compare_c10 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c11_manifest,
                factors=C11_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c10 not in _source:
    raise RuntimeError("Campaign011 comparison extension block was not found")
_source = _source.replace(_compare_c10, _compare_c11, 1)
_source = _source.replace(
    "Apply coverage before all 33 frozen uniqueness comparisons.",
    "Apply coverage before all 34 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace(
    "len(comparisons) == 33",
    "len(comparisons) == 34",
    1,
)
_source = _source.replace(
    '''            "campaign010_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign010_terminal_comparison_count": 1,
            "campaign011_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign010_snapshot_file_verification": c10_verification,
            "comparisons": comparisons,''',
    '''            "campaign010_snapshot_file_verification": c10_verification,
            "campaign011_snapshot_file_verification": c11_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign012_features_generated",
    "C9_SNAPSHOT_PATH": campaign011.campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign011.campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign011.campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign011.campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign011.campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": campaign011.C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": campaign011.C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": campaign011.C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": campaign011.C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": campaign011.C10_OUTPUT_COLUMNS,
    "C11_SNAPSHOT_PATH": C11_SNAPSHOT_PATH,
    "C11_SNAPSHOT_SHA256": C11_SNAPSHOT_SHA256,
    "C11_DATASET_SHA256": C11_DATASET_SHA256,
    "C11_FACTOR_NAMES": C11_FACTOR_NAMES,
    "C11_OUTPUT_COLUMNS": C11_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN011_FEATURE_RUNNER), "exec"), _generated)

Campaign012FeatureError = _generated["Campaign012FeatureError"]
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
    "ADJACENT_PAIR_COUNT",
    "MINIMUM_INFORMATIVE_PAIRS",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
