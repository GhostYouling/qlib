#!/usr/bin/env python3
"""Build Campaign090's frozen intraday range-clock-center snapshot."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089_features.py"
BASE_RUNNER_SHA256 = "64c0dc5a2331446e9acf57a00411b67bf3543d49104d89cdde07c91e8c2ee407"
FACTOR_NAME = "intraday_range_clock_center_240m"
FACTOR_FORMULA = (
    "on exactly 240 standard bars set r_i=log(high_i/low_i), x_i=i/239, "
    "and return sum(x_i*r_i)/sum(r_i) with strictly positive total range mass"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
SELECTED_BAR_COUNT = 240
ENDPOINT_TOLERANCE = 1e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign089 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign089", "Campaign090"),
    ("campaign089", "campaign090"),
    ("campaign_089", "campaign_090"),
    ("wf089", "wf090"),
    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),
    (
        "campaign_090_feature_implementation_freeze_20260807.json",
        "campaign_090_feature_implementation_freeze_v2_20260807.json",
    ),
    (
        "from scripts import a_share_three_day_walkforward_campaign088_features as c88",
        "from scripts import a_share_three_day_walkforward_campaign089_features as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_088_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_089_feature_snapshot_binding_20260807.json",
    ),
    (
        "campaign088_terminal_numeric_comparator",
        "campaign089_terminal_numeric_comparator",
    ),
    (
        "444e6aecdd82ad8f9ca909063bb42a5bf6453b826067f637e2bc54977d14e1be",
        "4b08b70625483f8d43795d2173108b72fa09f418abbd74aa143354ef1c5487cc",
    ),
    (
        "837621b6ee61f659e7b82f589758cea43b98143bb3e1f0aa2fbae3b6b3fd74a9",
        "0a550ef4e0bba078b7c876190ad4ab21c64f23154fc63ef06fc435fdaab8ed87",
    ),
    (
        "985f80fb46c1abdc4dc29f49e3525d292ca5632d67e7448d3f7ff00996ac4a37",
        "9ee27e671a56307be59ac70dd4e127ee9369b27c24c54ab9ec45512345d0d478",
    ),
    (
        "5a8f14e6740fa6fabb72b0ef455d173502cfa4c0e1542f808852665afbb2fc35",
        "dad79c5ed34158aa3b044875782ab6e96e622d4df737a5361aa0966081eb183c",
    ),
    (
        "15a17b1db513901a3a56ac3e39768971a78e9319937c8ac18eb980d362a33064",
        "3d7fc48e6cbe0fae14300ba9d09004f72e0d11a9570c59f4550fa9c42f0f478a",
    ),
    (
        "fd244df87c30d273f53e376561d03956c91f326237ae78cb16dc57906a136d41",
        "3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204",
    ),
    (
        "022e0bed5b6dc3ea50e069c44aa4e834aeaa6ec65444e87d75287cbeedf3d756",
        "c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a",
    ),
    ("FULL_DEFINITION_COUNT = 120", "FULL_DEFINITION_COUNT = 121"),
    (
        "9f0d70e832e7a1e5a62a312d79441621eda5822ff3de9155edc108409dcdb276",
        "2f3dcd13f68a38d9386f803cc6514c78d4902bcd94e41f6b4aae6a4d567fade0",
    ),
    ("COMPARISON_COUNT = 118", "COMPARISON_COUNT = 119"),
    (
        "a83d4485182d4dc6a2173af4c3158a3290939740c5465991a69521fdc65607c2",
        "3b5fc3bb4c82a29cd3768f7457a75095dc6fc50c410dd74e2720569be6c57b4b",
    ),
    ("all_118_numeric_comparators_must_pass", "all_119_numeric_comparators_must_pass"),
    ("v28", "v30"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    ),
    ("RETURN_COUNT = 238", "RETURN_COUNT = 240"),
    ("CLOCK_DENOMINATOR = 237", "CLOCK_DENOMINATOR = 239"),
    ("selected_close_count", "selected_bar_count"),
    ("total_return_count", "range_bar_count"),
    ("destination_amount_count", "range_bar_count"),
    ("valid_directional_timing_sessions", "valid_range_clock_center_sessions"),
    ("nonpositive_up_mass_sessions", "nonpositive_total_range_sessions"),
    ("nonpositive_down_mass_sessions", "invalid_ordered_range_sessions"),
    ("zero_returns", "zero_range_bars"),
    ("zero_destination_amounts", "endpoint_canonicalized_sessions"),
    ("[-1.0, 1.0]", "[0.0, 1.0]"),
    ("(-1.0, 1.0)", "(0.0, 1.0)"),
    ("values >= -1.0", "values >= 0.0"),
    ("candidate >= -1.0", "candidate >= 0.0"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign090_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign090FeatureError = _generated["Campaign090FeatureError"]


def compute_range_clock_center(
    highs: np.ndarray, lows: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, total range mass, and bar range matrix."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign090FeatureError("Campaign090 requires an n-by-240 high array")
    if low.ndim != 2 or low.shape != high.shape:
        raise Campaign090FeatureError("Campaign090 requires matching n-by-240 lows")
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (high >= low).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(high / low)
        totals = np.sum(ranges, axis=1, dtype=np.float64)
        clock = np.arange(SELECTED_BAR_COUNT, dtype=np.float64) / 239.0
        raw_score = np.sum(ranges * clock, axis=1, dtype=np.float64) / totals
    support = (
        source_valid
        & np.isfinite(ranges).all(axis=1)
        & (ranges >= 0.0).all(axis=1)
        & np.isfinite(totals)
        & (totals > 0.0)
        & np.isfinite(raw_score)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    candidate = raw_score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    valid_score = np.isfinite(candidate) & (candidate >= 0.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, totals, ranges


def extract_range_clock_center(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign090FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_range_clock_center_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_total_range_sessions": 0,
        "invalid_ordered_range_sessions": 0,
        "zero_range_bars": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign090FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)["minute_code"].nunique()
    c86 = _generated["c86"]
    if (
        counts.empty
        or not counts.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign090FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign090FeatureError(f"continuous minute grid changed for {symbol}")
    highs = continuous["high"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    lows = continuous["low"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    values, eligible, totals, ranges = compute_range_clock_center(highs, lows)
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordered = finite_positive & (highs >= lows).all(axis=1)
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_range_clock_center_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_total_range_sessions": int(
            (ordered & (~np.isfinite(totals) | (totals <= 0.0))).sum()
        ),
        "invalid_ordered_range_sessions": int((finite_positive & ~ordered).sum()),
        "zero_range_bars": int(((ranges == 0.0) & ordered[:, None]).sum()),
        "endpoint_canonicalized_sessions": int(
            (eligible & ((values == 0.0) | (values == 1.0))).sum()
        ),
    }


_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["compute_directional_amount_timing_spread"] = compute_range_clock_center
_generated["extract_directional_amount_timing_spread"] = extract_range_clock_center

DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE = _generated["DEFAULT_IMPLEMENTATION_FREEZE"]
PROTOCOL_SHA256 = _generated["PROTOCOL_SHA256"]
MECHANISM_AUDIT_SHA256 = _generated["MECHANISM_AUDIT_SHA256"]
CURRENT_STATE_SHA256 = _generated["CURRENT_STATE_SHA256"]
NUMERIC_POLICY_SHA256 = _generated["NUMERIC_POLICY_SHA256"]
FULL_DEFINITION_COUNT = _generated["FULL_DEFINITION_COUNT"]
FULL_DEFINITION_ORDER_SHA256 = _generated["FULL_DEFINITION_ORDER_SHA256"]
COMPARISON_COUNT = _generated["COMPARISON_COUNT"]
COMPARISON_ORDER_SHA256 = _generated["COMPARISON_ORDER_SHA256"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
TEST_PATH = _generated["TEST_PATH"]
c85 = _generated["c85"]
c86 = _generated["c86"]
bindings = _generated["bindings"]
load_protocol = _generated["load_protocol"]
reconstruct_comparisons = _generated["reconstruct_comparisons"]
reconstruct_complete_definitions = _generated["reconstruct_complete_definitions"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]
_comparison_order_digest = _generated["_comparison_order_digest"]
_json_digest = _generated["_json_digest"]


if __name__ == "__main__":
    raise SystemExit(main())
