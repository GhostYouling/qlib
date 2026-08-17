#!/usr/bin/env python3
"""Build and audit the frozen Campaign011 intrabar-range entropy factor.

Campaign010 supplies only the already-tested checkpoint, snapshot, coverage,
and first 32-factor comparison orchestration.  This wrapper deterministically
changes the campaign namespace, replaces the factor calculation with the
independently preregistered fixed-support range-participation entropy, and adds
the usable terminal Campaign010 factor as comparison number 33.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign010_features as campaign010
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign010_features as campaign010


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN010_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign010_features.py"
)
CAMPAIGN010_FEATURE_RUNNER_SHA256 = (
    "329d78f5d503991dafee59a10b3a49ea66acf0b2aaed83ef9a2096fb49dd7d4f"
)
OLD_FACTOR = "intraday_adjacent_range_overlap_continuity_238p"
FACTOR_NAME = "intraday_intrabar_range_participation_entropy_240m"
MECHANISM_AUDIT_SHA256 = (
    "fe50e938523f49fe8038e72036b2d3d7c8a08ef3c5870747d5f967b910679eed"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "3e530c7a2f76e6a1eecdb18c6058a1d20fb1e3e54aaffb5ae4b3a857d5112e56"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "36efe15038681d3a2fc154dfd3ce6d918c54ab56d1a5e803ee7aa86c295f4084"
)
SNAPSHOT_DATASET_SHA256 = (
    "078dcb053e641813978ed96542fb9c69fbf3108ac490d3463e870b640feeee11"
)
NO_RETURN_AUDIT_SHA256 = (
    "1c07ddba4d3447016aa9460e6a9018b33eb380246cd672fbbb533d397066e995"
)

C10_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign010_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign010_feature_library_v1/snapshot_manifest.json"
)
C10_SNAPSHOT_SHA256 = (
    "e700c23b8c86e412153dd7ebd3bcb4a322f12b8a506cbbf5e4659490da50d69b"
)
C10_DATASET_SHA256 = (
    "55303f4934044fa2543d459aa378e28ff440b03b8a0a69d6866e14736d6bdcc0"
)
C10_FACTOR_NAMES = ("intraday_adjacent_range_overlap_continuity_238p",)
C10_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C10_FACTOR_NAMES[0],
    f"{C10_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN010_FEATURE_RUNNER) != CAMPAIGN010_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign010 feature orchestration fingerprint changed")

_source = campaign010._source
for _old, _new in (
    ("Campaign010", "Campaign011"),
    ("campaign010", "campaign011"),
    ("campaign_010", "campaign_011"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "41f4d88ff785ef594c1aec9337a4498de53f08edac532c4237340810f2f57680",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "0981e5915f0ba5eff8f779b7ad594324bccfd75b0fb76f22916ed734d6443a53",
        PROTOCOL_SHA256,
    ),
    (
        "e700c23b8c86e412153dd7ebd3bcb4a322f12b8a506cbbf5e4659490da50d69b",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "55303f4934044fa2543d459aa378e28ff440b03b8a0a69d6866e14736d6bdcc0",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "e86bd79edc830d68bcf72ab5148e42e030dae5df28087d6b68f0147a581fb262",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "sum(overlap_i) / sum(union_span_i) across 238 within-half "
    "adjacent high-low interval pairs"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "-sum(p_i * log(p_i)) / log(240), where p_i = "
    "log(high_i/low_i) / sum_j(log(high_j/low_j)) across the 240 "
    "continuous-session bars and zero-range terms contribute zero"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign010 formula block changed")
_source = _source.replace(_old_formula, _new_formula)
_source = _source.replace(
    "SELECTED_BAR_COUNT = 240\n"
    "MAXIMUM_WITHIN_HALF_ADJACENT_PAIRS = 238\n"
    "MINIMUM_POSITIVE_UNION_PAIRS = 120",
    "SELECTED_BAR_COUNT = 240\n"
    "MINIMUM_POSITIVE_RANGE_BARS = 120\n"
    "ENTROPY_SUPPORT_BAR_COUNT = 240",
)
_source = _source.replace(
    'and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT\n'
    '        and candidates[0].get("maximum_within_half_adjacent_pairs")\n'
    "        == MAXIMUM_WITHIN_HALF_ADJACENT_PAIRS\n"
    '        and candidates[0].get("minimum_positive_union_pairs")\n'
    "        == MINIMUM_POSITIVE_UNION_PAIRS",
    'and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT\n'
    '        and candidates[0].get("minimum_positive_range_bars")\n'
    "        == MINIMUM_POSITIVE_RANGE_BARS\n"
    '        and candidates[0].get("entropy_support_bar_count")\n'
    "        == ENTROPY_SUPPORT_BAR_COUNT",
)
_source = _source.replace(
    "and len(comparisons) == 32\n"
    '        and str(comparisons[-1].get("name") or "") == C9_FACTOR_NAMES[0]',
    "and len(comparisons) == 33\n"
    '        and str(comparisons[-1].get("name") or "") == C10_FACTOR_NAMES[0]',
)
_source = _source.replace(
    '"""Apply coverage before all 32 frozen uniqueness comparisons."""',
    '"""Apply coverage before all 33 frozen uniqueness comparisons."""',
)

_c10_verify_anchor = '''        c9_manifest, c9_verification = executor._verify_prior_snapshot(
            path=C9_SNAPSHOT_PATH,
            manifest_sha256=C9_SNAPSHOT_SHA256,
            dataset_sha256=C9_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign009_feature_snapshot",
            factor_names=C9_FACTOR_NAMES,
            output_columns=C9_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_c10_verify_block = _c10_verify_anchor + '''        c10_manifest, c10_verification = executor._verify_prior_snapshot(
            path=C10_SNAPSHOT_PATH,
            manifest_sha256=C10_SNAPSHOT_SHA256,
            dataset_sha256=C10_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign010_feature_snapshot",
            factor_names=C10_FACTOR_NAMES,
            output_columns=C10_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _c10_verify_anchor not in _source:
    raise RuntimeError("Campaign010 prior-snapshot verification block changed")
_source = _source.replace(_c10_verify_anchor, _c10_verify_block)

_c10_compare_anchor = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c9_manifest,
                factors=C9_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_c10_compare_block = _c10_compare_anchor + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c10_manifest,
                factors=C10_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _c10_compare_anchor not in _source:
    raise RuntimeError("Campaign010 prior-comparison block changed")
_source = _source.replace(_c10_compare_anchor, _c10_compare_block)
_source = _source.replace(
    "len(comparisons) == 32\n"
    '            and all(item["gate_passed"] for item in comparisons)',
    "len(comparisons) == 33\n"
    '            and all(item["gate_passed"] for item in comparisons)',
)
_source = _source.replace(
    '"campaign009_terminal_comparison_count": 1,\n'
    '            "prior_snapshot_file_verification"',
    '"campaign009_terminal_comparison_count": 1,\n'
    '            "campaign010_terminal_comparison_count": 1,\n'
    '            "prior_snapshot_file_verification"',
)
_source = _source.replace(
    '"campaign009_snapshot_file_verification": c9_verification,\n'
    '            "comparisons": comparisons,',
    '"campaign009_snapshot_file_verification": c9_verification,\n'
    '            "campaign010_snapshot_file_verification": c10_verification,\n'
    '            "comparisons": comparisons,',
)

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen fixed-support intrabar-range participation entropy."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign011FeatureError("Campaign011 aligned array shapes are invalid")
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
    positive_range_count = (log_ranges > 0.0).sum(axis=1)
    total_range = log_ranges.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        probabilities = log_ranges / total_range[:, None]
        entropy_terms = np.where(
            probabilities > 0.0,
            -probabilities * np.log(probabilities),
            0.0,
        )
        values = entropy_terms.sum(axis=1) / np.log(
            float(ENTROPY_SUPPORT_BAR_COUNT)
        )
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    valid_ordered = finite_positive & ordering & finite_ranges & nonnegative_ranges
    sufficiently_observed = (
        valid_ordered
        & (positive_range_count >= MINIMUM_POSITIVE_RANGE_BARS)
    )
    eligible = (
        sufficiently_observed
        & np.isfinite(total_range)
        & (total_range > 0.0)
        & finite
        & in_range
    )
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
        f"{FACTOR_NAME}__fewer_than_120_positive_range_bar_rows": int(
            (
                valid_ordered
                & (positive_range_count < MINIMUM_POSITIVE_RANGE_BARS)
            ).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_aggregate_range_rows": int(
            (
                sufficiently_observed
                & (~np.isfinite(total_range) | (total_range <= 0.0))
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                sufficiently_observed
                & np.isfinite(total_range)
                & (total_range > 0.0)
                & (~finite | ~in_range)
            ).sum()
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
    """Validate one source partition and compute the frozen range entropy."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign011FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign011FeatureError(
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
        raise Campaign011FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign011FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign011FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign011FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign011FeatureError(
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
        raise Campaign011FeatureError(
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

_compute_start = _source.index("def compute_factor_values(")
_partition_start = _source.index("def compute_partition_frame(", _compute_start)
_configure_start = _source.index("def _configure_engine(", _partition_start)
_source = (
    _source[:_compute_start]
    + _new_compute
    + _new_partition
    + _source[_configure_start:]
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign011_features_generated",
    "C9_SNAPSHOT_PATH": campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": C10_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN010_FEATURE_RUNNER), "exec"), _generated)

Campaign011FeatureError = _generated["Campaign011FeatureError"]
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
    "MINIMUM_POSITIVE_RANGE_BARS",
    "ENTROPY_SUPPORT_BAR_COUNT",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
