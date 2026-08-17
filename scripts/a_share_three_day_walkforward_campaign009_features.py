#!/usr/bin/env python3
"""Build and audit the frozen Campaign009 no-return OHLC mechanism.

The byte-bound Campaign008 module supplies only the already-tested checkpoint,
snapshot, coverage, and 31-factor comparison orchestration.  This wrapper
deterministically changes the campaign namespace and replaces the factor
calculation with the independently preregistered within-bar OHLC formula.
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
FACTOR_NAME = "intraday_intrabar_body_range_efficiency_240m"
MECHANISM_AUDIT_SHA256 = (
    "abfbc1d94b6a6272eaedb65a8c9ea8673398da3cb220b30c34997c2fcd45df21"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "7080dae932fa3b35869ea39de1b4e3759ff968629ee20f422e368eb2e0799e19"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "1857176ced53c5515688b4c4b8e0e6e1b5b8332212841e529608169f77496aa7"
)
SNAPSHOT_DATASET_SHA256 = (
    "14fac16f960b84be9ec89c01eea286267bed079c1c17600e94ae2156deac357d"
)
NO_RETURN_AUDIT_SHA256 = (
    "b170574e70cabe2700d90716e852c4c6c0a85714619261cecb5d2d1ef4f70c5e"
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
    ("Campaign008", "Campaign009"),
    ("campaign008", "campaign009"),
    ("campaign_008", "campaign_009"),
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
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
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
    "sum(abs(log(close_i/open_i))) / sum(log(high_i/low_i)) "
    "across the 240 continuous-session bars"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign008 formula block changed")
_source = _source.replace(_old_formula, _new_formula)
_source = _source.replace(
    "MAXIMUM_PAIRS = 236\nMINIMUM_RETAINED_PAIRS = 120",
    "SELECTED_BAR_COUNT = 240\nMINIMUM_POSITIVE_RANGE_BARS = 120",
)
_source = _source.replace(
    'and candidates[0].get("maximum_possible_pairs") == MAXIMUM_PAIRS\n'
    '        and candidates[0].get("minimum_retained_pairs")\n'
    "        == MINIMUM_RETAINED_PAIRS",
    'and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT\n'
    '        and candidates[0].get("minimum_positive_range_bars")\n'
    "        == MINIMUM_POSITIVE_RANGE_BARS",
)
_source = _source.replace(
    'and boundary.get("minute_close_field_read_before_admissibility") is True\n'
    '        and boundary.get("minute_amount_field_read_before_admissibility") is False',
    'and boundary.get("minute_open_high_low_fields_read_before_admissibility") is True\n'
    '        and boundary.get("minute_close_field_read_before_admissibility") is True\n'
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
    'value["source_close_read"] = True\n'
    '            value["source_amount_read"] = False',
    'value["source_open_high_low_read"] = True\n'
    '            value["source_volume_read"] = False\n'
    '            value["source_close_read"] = True\n'
    '            value["source_amount_read"] = False',
)
_source = _source.replace(
    '"minute_close_read": True,\n'
    '        "minute_amount_read": False,',
    '"minute_open_high_low_read": True,\n'
    '        "minute_close_read": True,\n'
    '        "minute_volume_read": False,\n'
    '        "minute_amount_read": False,',
)
_source = _source.replace(
    '"minute_close_read_by_status": True,\n'
    '        "minute_amount_read_by_status": False,',
    '"minute_open_high_low_read_by_status": True,\n'
    '        "minute_close_read_by_status": True,\n'
    '        "minute_volume_read_by_status": False,\n'
    '        "minute_amount_read_by_status": False,',
)

_new_compute = r'''def compute_factor_values(
    *,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen sign-neutral within-bar body/range efficiency."""

    if (
        opens.ndim != 2
        or opens.shape[1] != SELECTED_BAR_COUNT
        or highs.shape != opens.shape
        or lows.shape != opens.shape
        or closes.shape != opens.shape
    ):
        raise Campaign009FeatureError("Campaign009 aligned array shapes are invalid")
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
    ordering = (
        (lows <= opens).all(axis=1)
        & (lows <= closes).all(axis=1)
        & (opens <= highs).all(axis=1)
        & (closes <= highs).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        bodies = np.abs(np.log(closes / opens))
        ranges = np.log(highs / lows)
    positive_range_count = (highs > lows).sum(axis=1)
    body_sum = bodies.sum(axis=1)
    range_sum = ranges.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = body_sum / range_sum
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = (
        finite_positive
        & ordering
        & (positive_range_count >= MINIMUM_POSITIVE_RANGE_BARS)
        & np.isfinite(body_sum)
        & np.isfinite(range_sum)
        & (range_sum > 0.0)
        & finite
        & in_range
    )
    valid_ordered = finite_positive & ordering
    sufficiently_observed = (
        valid_ordered
        & (positive_range_count >= MINIMUM_POSITIVE_RANGE_BARS)
    )
    quality = {
        "base_rows": int(len(opens)),
        "invalid_required_ohlc_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__ohlc_ordering_violation_rows": int(
            (finite_positive & ~ordering).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__fewer_than_120_positive_range_rows": int(
            (valid_ordered & (positive_range_count < MINIMUM_POSITIVE_RANGE_BARS)).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_aggregate_range_rows": int(
            (
                sufficiently_observed
                & (~np.isfinite(range_sum) | (range_sum <= 0.0))
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                sufficiently_observed
                & np.isfinite(range_sum)
                & (range_sum > 0.0)
                & (~np.isfinite(body_sum) | ~finite | ~in_range)
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
    """Validate one source partition and compute the frozen OHLC feature."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign009FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign009FeatureError(
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
        raise Campaign009FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign009FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign009FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign009FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign009FeatureError(
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
        raise Campaign009FeatureError(
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
    "__name__": "a_share_three_day_walkforward_campaign009_features_generated",
}
exec(compile(_source, str(CAMPAIGN008_FEATURE_RUNNER), "exec"), _generated)

Campaign009FeatureError = _generated["Campaign009FeatureError"]
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
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
