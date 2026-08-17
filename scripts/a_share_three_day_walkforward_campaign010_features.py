#!/usr/bin/env python3
"""Build and audit the frozen Campaign010 no-return high-low mechanism.

The byte-bound Campaign008 module supplies only the already-tested checkpoint,
snapshot, coverage, and base 31-factor comparison orchestration. This wrapper
deterministically changes the campaign namespace, replaces the factor
calculation with the independently preregistered adjacent-range formula, and
adds the usable terminal Campaign009 factor as comparison number 32.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN008_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign008_features.py"
)
CAMPAIGN008_FEATURE_RUNNER_SHA256 = (
    "a8921a6a6fc0cedd26095515d52a7d794b7845f6e5a90666aad2ef76a987f466"
)
OLD_FACTOR = "intraday_post_shock_share_volume_replenishment_236p"
FACTOR_NAME = "intraday_adjacent_range_overlap_continuity_238p"
MECHANISM_AUDIT_SHA256 = (
    "41f4d88ff785ef594c1aec9337a4498de53f08edac532c4237340810f2f57680"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "0981e5915f0ba5eff8f779b7ad594324bccfd75b0fb76f22916ed734d6443a53"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "e700c23b8c86e412153dd7ebd3bcb4a322f12b8a506cbbf5e4659490da50d69b"
)
SNAPSHOT_DATASET_SHA256 = (
    "55303f4934044fa2543d459aa378e28ff440b03b8a0a69d6866e14736d6bdcc0"
)
NO_RETURN_AUDIT_SHA256 = (
    "e86bd79edc830d68bcf72ab5148e42e030dae5df28087d6b68f0147a581fb262"
)

C9_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign009_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign009_feature_library_v1/snapshot_manifest.json"
)
C9_SNAPSHOT_SHA256 = (
    "1857176ced53c5515688b4c4b8e0e6e1b5b8332212841e529608169f77496aa7"
)
C9_DATASET_SHA256 = (
    "14fac16f960b84be9ec89c01eea286267bed079c1c17600e94ae2156deac357d"
)
C9_FACTOR_NAMES = ("intraday_intrabar_body_range_efficiency_240m",)
C9_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C9_FACTOR_NAMES[0],
    f"{C9_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN008_FEATURE_RUNNER) != CAMPAIGN008_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign008 feature orchestration fingerprint changed")

_source = CAMPAIGN008_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign008", "Campaign010"),
    ("campaign008", "campaign010"),
    ("campaign_008", "campaign_010"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "259d3055898961287bea478946fa1653deade16b9b9927da9fc8b7a5d3d87246",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "1c209a1611d822531efe178793c80e5a8f68f5752ae5a0dfa890585e62dfcf56",
        PROTOCOL_SHA256,
    ),
    (
        "09d4f82ec350ff8c16106c7ebc007d791f626589d33cd3e09cd4d0725893aaab",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "825b9a68890a6975b0866a99ce5b798968b82d80f226c8fdadbffba3472b40dc",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "af4013e0d439174ab6bb0c08d26bdf4bed71b6bd668eea25c834ec5ff0f5e937",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "volume")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
)
_old_formula = '''FACTOR_FORMULA = (
    "PearsonCorr(abs(log(close_t/close_t-1)), "
    "log(volume_t+1/volume_t)) over retained within-half "
    "one-minute post-shock response pairs"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "sum(overlap_i) / sum(union_span_i) across 238 within-half "
    "adjacent high-low interval pairs"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign008 formula block changed")
_source = _source.replace(_old_formula, _new_formula)
_source = _source.replace(
    "MAXIMUM_PAIRS = 236\nMINIMUM_RETAINED_PAIRS = 120",
    "SELECTED_BAR_COUNT = 240\n"
    "MAXIMUM_WITHIN_HALF_ADJACENT_PAIRS = 238\n"
    "MINIMUM_POSITIVE_UNION_PAIRS = 120",
)
_source = _source.replace(
    'and candidates[0].get("maximum_possible_pairs") == MAXIMUM_PAIRS\n'
    '        and candidates[0].get("minimum_retained_pairs")\n'
    "        == MINIMUM_RETAINED_PAIRS",
    'and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT\n'
    '        and candidates[0].get("maximum_within_half_adjacent_pairs")\n'
    "        == MAXIMUM_WITHIN_HALF_ADJACENT_PAIRS\n"
    '        and candidates[0].get("minimum_positive_union_pairs")\n'
    "        == MINIMUM_POSITIVE_UNION_PAIRS",
)
_source = _source.replace(
    "and len(comparisons) == 31\n"
    '        and str(comparisons[-1].get("name") or "") == C7_FACTOR_NAMES[0]',
    "and len(comparisons) == 32\n"
    '        and str(comparisons[-1].get("name") or "") == C9_FACTOR_NAMES[0]',
)
_source = _source.replace(
    'and boundary.get("minute_close_field_read_before_admissibility") is True\n'
    '        and boundary.get("minute_amount_field_read_before_admissibility") is False',
    'and boundary.get("minute_open_high_low_fields_read_before_admissibility") is True\n'
    '        and boundary.get("minute_close_field_read_before_admissibility") is False\n'
    '        and boundary.get("minute_volume_field_read_before_admissibility") is False\n'
    '        and boundary.get("minute_amount_field_read_before_admissibility") is False',
)
_source = _source.replace(
    'and manifest.get("source_open_high_low_read") is False\n'
    '        and manifest.get("source_volume_read") is True',
    'and (\n'
    '            manifest.get("source_open_high_low_read") is True\n'
    '            if require_fingerprint_constants\n'
    '            else manifest.get("source_open_high_low_read") is False\n'
    '        )\n'
    '        and (\n'
    '            manifest.get("source_volume_read") is False\n'
    '            if require_fingerprint_constants\n'
    '            else manifest.get("source_volume_read") is True\n'
    '        )',
)
_source = _source.replace(
    'manifest.get("source_close_read") is True\n'
    '            if require_fingerprint_constants\n'
    '            else manifest.get("source_close_read") in {None, True}',
    'manifest.get("source_close_read") is False\n'
    '            if require_fingerprint_constants\n'
    '            else manifest.get("source_close_read") in {None, True}',
)
_source = _source.replace(
    'value["source_close_read"] = True\n'
    '            value["source_amount_read"] = False',
    'value["source_open_high_low_read"] = True\n'
    '            value["source_volume_read"] = False\n'
    '            value["source_close_read"] = False\n'
    '            value["source_amount_read"] = False',
)
_source = _source.replace(
    '"minute_close_read": True,\n'
    '        "minute_amount_read": False,',
    '"minute_open_high_low_read": True,\n'
    '        "minute_close_read": False,\n'
    '        "minute_volume_read": False,\n'
    '        "minute_amount_read": False,',
)
_source = _source.replace(
    '"minute_close_read_by_status": True,\n'
    '        "minute_amount_read_by_status": False,',
    '"minute_open_high_low_read_by_status": True,\n'
    '        "minute_close_read_by_status": False,\n'
    '        "minute_volume_read_by_status": False,\n'
    '        "minute_amount_read_by_status": False,',
)
_source = _source.replace(
    '"""Apply coverage before all 31 frozen uniqueness comparisons."""',
    '"""Apply coverage before all 32 frozen uniqueness comparisons."""',
)

_c9_verify_anchor = '''        c7_manifest, c7_verification = executor._verify_prior_snapshot(
            path=C7_SNAPSHOT_PATH,
            manifest_sha256=C7_SNAPSHOT_SHA256,
            dataset_sha256=C7_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign007_feature_snapshot",
            factor_names=C7_FACTOR_NAMES,
            output_columns=C7_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_c9_verify_block = _c9_verify_anchor + '''        c9_manifest, c9_verification = executor._verify_prior_snapshot(
            path=C9_SNAPSHOT_PATH,
            manifest_sha256=C9_SNAPSHOT_SHA256,
            dataset_sha256=C9_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign009_feature_snapshot",
            factor_names=C9_FACTOR_NAMES,
            output_columns=C9_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _c9_verify_anchor not in _source:
    raise RuntimeError("Campaign008 prior-snapshot verification block changed")
_source = _source.replace(_c9_verify_anchor, _c9_verify_block)

_c9_compare_anchor = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c7_manifest,
                factors=C7_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_c9_compare_block = _c9_compare_anchor + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c9_manifest,
                factors=C9_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _c9_compare_anchor not in _source:
    raise RuntimeError("Campaign008 prior-comparison block changed")
_source = _source.replace(_c9_compare_anchor, _c9_compare_block)
_source = _source.replace(
    "len(comparisons) == 31\n"
    '            and all(item["gate_passed"] for item in comparisons)',
    "len(comparisons) == 32\n"
    '            and all(item["gate_passed"] for item in comparisons)',
)
_source = _source.replace(
    '"campaign007_terminal_comparison_count": 1,\n'
    '            "prior_snapshot_file_verification"',
    '"campaign007_terminal_comparison_count": 1,\n'
    '            "campaign009_terminal_comparison_count": 1,\n'
    '            "prior_snapshot_file_verification"',
)
_source = _source.replace(
    '"campaign007_snapshot_file_verification": c7_verification,\n'
    '            "comparisons": comparisons,',
    '"campaign007_snapshot_file_verification": c7_verification,\n'
    '            "campaign009_snapshot_file_verification": c9_verification,\n'
    '            "comparisons": comparisons,',
)

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen adjacent high-low interval overlap continuity."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign010FeatureError("Campaign010 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordering = (lows <= highs).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_highs = np.log(highs)
        log_lows = np.log(lows)
    left_high = np.concatenate(
        [log_highs[:, :119], log_highs[:, 120:239]],
        axis=1,
    )
    right_high = np.concatenate(
        [log_highs[:, 1:120], log_highs[:, 121:240]],
        axis=1,
    )
    left_low = np.concatenate(
        [log_lows[:, :119], log_lows[:, 120:239]],
        axis=1,
    )
    right_low = np.concatenate(
        [log_lows[:, 1:120], log_lows[:, 121:240]],
        axis=1,
    )
    overlap = np.maximum(
        0.0,
        np.minimum(left_high, right_high) - np.maximum(left_low, right_low),
    )
    union_span = (
        np.maximum(left_high, right_high) - np.minimum(left_low, right_low)
    )
    positive_union_count = (union_span > 0.0).sum(axis=1)
    overlap_sum = overlap.sum(axis=1)
    union_sum = union_span.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = overlap_sum / union_sum
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = (
        finite_positive
        & ordering
        & (positive_union_count >= MINIMUM_POSITIVE_UNION_PAIRS)
        & np.isfinite(overlap_sum)
        & (overlap_sum >= 0.0)
        & np.isfinite(union_sum)
        & (union_sum > 0.0)
        & finite
        & in_range
    )
    valid_ordered = finite_positive & ordering
    sufficiently_observed = (
        valid_ordered
        & (positive_union_count >= MINIMUM_POSITIVE_UNION_PAIRS)
    )
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~ordering).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__fewer_than_120_positive_union_pair_rows": int(
            (
                valid_ordered
                & (positive_union_count < MINIMUM_POSITIVE_UNION_PAIRS)
            ).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_aggregate_union_span_rows": int(
            (
                sufficiently_observed
                & (~np.isfinite(union_sum) | (union_sum <= 0.0))
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                sufficiently_observed
                & np.isfinite(union_sum)
                & (union_sum > 0.0)
                & (
                    ~np.isfinite(overlap_sum)
                    | (overlap_sum < 0.0)
                    | ~finite
                    | ~in_range
                )
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
    """Validate one source partition and compute the frozen range feature."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign010FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign010FeatureError(
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
        raise Campaign010FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign010FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign010FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign010FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign010FeatureError(
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
        raise Campaign010FeatureError(
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
    "__name__": "a_share_three_day_walkforward_campaign010_features_generated",
    "C9_SNAPSHOT_PATH": C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": C9_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN008_FEATURE_RUNNER), "exec"), _generated)

Campaign010FeatureError = _generated["Campaign010FeatureError"]
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
    "MAXIMUM_WITHIN_HALF_ADJACENT_PAIRS",
    "MINIMUM_POSITIVE_UNION_PAIRS",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
