#!/usr/bin/env python3
"""Build Campaign091's frozen directional intrabar range-mass snapshot."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089_features.py"
BASE_RUNNER_SHA256 = "64c0dc5a2331446e9acf57a00411b67bf3543d49104d89cdde07c91e8c2ee407"
FACTOR_NAME = "intraday_directional_range_mass_imbalance_240m"
FACTOR_FORMULA = (
    "on exactly 240 standard bars set r_i=log(high_i/low_i) and "
    "b_i=log(close_i/open_i), then return (U-D)/(U+D), where U and D "
    "are range mass on strictly positive and strictly negative bodies"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")
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
    ("Campaign089", "Campaign091"),
    ("campaign089", "campaign091"),
    ("campaign_089", "campaign_091"),
    ("wf089", "wf091"),
    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),
    (
        "from scripts import a_share_three_day_walkforward_campaign088_features as c88",
        "from scripts import a_share_three_day_walkforward_campaign090_features as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_088_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_090_feature_snapshot_binding_20260807.json",
    ),
    ("campaign088_terminal_numeric_comparator", "campaign090_terminal_numeric_comparator"),
    ("444e6aecdd82ad8f9ca909063bb42a5bf6453b826067f637e2bc54977d14e1be", "d9e9ca112dc47211f0fcf983752d73c421adff1789a0873b1b95feaeaaba368b"),
    ("837621b6ee61f659e7b82f589758cea43b98143bb3e1f0aa2fbae3b6b3fd74a9", "5aa5c5dda110ddfddfd002d43fab684156a8516f7f89e669f8dfe88eca69af1a"),
    ("985f80fb46c1abdc4dc29f49e3525d292ca5632d67e7448d3f7ff00996ac4a37", "46e1856a031b5e8ae1c805eb0e52076e3d16de60ac07d6f073730b21579a9a69"),
    ("5a8f14e6740fa6fabb72b0ef455d173502cfa4c0e1542f808852665afbb2fc35", "cb5db190487c4af6060e5b6b9fd5d4c109f1fc439d815b87cf8d0c43448b5b97"),
    ("15a17b1db513901a3a56ac3e39768971a78e9319937c8ac18eb980d362a33064", "c2d34eed453c3bcce072088b05e9f5703f33e544641f39707e4cbdd75a54c455"),
    ("fd244df87c30d273f53e376561d03956c91f326237ae78cb16dc57906a136d41", "c065e81f4eec91b214a3e1f69d8e15e567fac5bd879e173c5b985777ab4ba2ed"),
    ("022e0bed5b6dc3ea50e069c44aa4e834aeaa6ec65444e87d75287cbeedf3d756", "d1da6b2c1d059038e473c55a15c76ba2efaf1a282d5a6bec1f302cd37a76ca31"),
    ("FULL_DEFINITION_COUNT = 120", "FULL_DEFINITION_COUNT = 122"),
    ("9f0d70e832e7a1e5a62a312d79441621eda5822ff3de9155edc108409dcdb276", "1ed99d450143370e1b810e8fbb03e6e84882256c53fc035a9fef4e234a956d7f"),
    ("COMPARISON_COUNT = 118", "COMPARISON_COUNT = 120"),
    ("a83d4485182d4dc6a2173af4c3158a3290939740c5465991a69521fdc65607c2", "5354d5ca8d26f890239e07ddc0eca1242723644af0fdd06ec7a76a15cb5b01f7"),
    ("all_118_numeric_comparators_must_pass", "all_120_numeric_comparators_must_pass"),
    ("numeric_comparator_policy_v28", "numeric_comparator_policy_v32"),
    ("v28", "v32"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
    ),
    ("RETURN_COUNT = 238", "RETURN_COUNT = 240"),
    ("selected_close_count", "selected_bar_count"),
    ("total_return_count", "range_bar_count"),
    ("destination_amount_count", "body_sign_count"),
    ("candidate.get(\"clock_coordinate_denominator\") == CLOCK_DENOMINATOR", "candidate.get(\"body_sign_count\") == SELECTED_BAR_COUNT"),
    ("valid_directional_timing_sessions", "valid_directional_range_mass_sessions"),
    ("nonpositive_up_mass_sessions", "nonpositive_directional_range_mass_sessions"),
    ("nonpositive_down_mass_sessions", "invalid_ordered_ohlc_sessions"),
    ("zero_returns", "zero_body_bars"),
    ("zero_destination_amounts", "endpoint_canonicalized_sessions"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign091_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign091FeatureError = _generated["Campaign091FeatureError"]


def compute_directional_range_mass_imbalance(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, U, D, log ranges, and log bodies."""

    open_ = np.asarray(opens, dtype=np.float64)
    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if open_.ndim != 2 or open_.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign091FeatureError("Campaign091 requires an n-by-240 open array")
    if high.shape != open_.shape or low.shape != open_.shape or close.shape != open_.shape:
        raise Campaign091FeatureError("Campaign091 requires matching n-by-240 OHLC arrays")
    source_valid = (
        np.isfinite(open_).all(axis=1)
        & np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (open_ > 0.0).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
        & (low <= open_).all(axis=1)
        & (open_ <= high).all(axis=1)
        & (low <= close).all(axis=1)
        & (close <= high).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(high / low)
        bodies = np.log(close / open_)
        up_mass = np.sum(np.where(bodies > 0.0, ranges, 0.0), axis=1, dtype=np.float64)
        down_mass = np.sum(np.where(bodies < 0.0, ranges, 0.0), axis=1, dtype=np.float64)
        denominator = up_mass + down_mass
        raw_score = (up_mass - down_mass) / denominator
    support = (
        source_valid
        & np.isfinite(ranges).all(axis=1)
        & (ranges >= 0.0).all(axis=1)
        & np.isfinite(bodies).all(axis=1)
        & np.isfinite(up_mass)
        & np.isfinite(down_mass)
        & np.isfinite(denominator)
        & (denominator > 0.0)
        & np.isfinite(raw_score)
    )
    result = np.full(len(open_), np.nan, dtype=np.float64)
    candidate = raw_score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    candidate[np.abs(candidate + 1.0) <= ENDPOINT_TOLERANCE] = -1.0
    valid_score = np.isfinite(candidate) & (candidate >= -1.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= -1.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, up_mass, down_mass, ranges, bodies


def extract_directional_range_mass_imbalance(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign091FeatureError(
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
        "valid_directional_range_mass_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_directional_range_mass_sessions": 0,
        "invalid_ordered_ohlc_sessions": 0,
        "zero_body_bars": 0,
        "up_body_bars": 0,
        "down_body_bars": 0,
        "zero_range_bars": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("open", "high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign091FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign091FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "open", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=c86.CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign091FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column].to_numpy(dtype=np.float64).reshape(
            len(dates), SELECTED_BAR_COUNT
        )
        for column in ("open", "high", "low", "close")
    }
    values, eligible, up_mass, down_mass, ranges, bodies = (
        compute_directional_range_mass_imbalance(
            arrays["open"], arrays["high"], arrays["low"], arrays["close"]
        )
    )
    finite_positive = np.logical_and.reduce(
        [np.isfinite(array).all(axis=1) & (array > 0.0).all(axis=1) for array in arrays.values()]
    )
    ordered = (
        finite_positive
        & (arrays["low"] <= arrays["open"]).all(axis=1)
        & (arrays["open"] <= arrays["high"]).all(axis=1)
        & (arrays["low"] <= arrays["close"]).all(axis=1)
        & (arrays["close"] <= arrays["high"]).all(axis=1)
    )
    denominator = up_mass + down_mass
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_directional_range_mass_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_directional_range_mass_sessions": int(
            (ordered & (~np.isfinite(denominator) | (denominator <= 0.0))).sum()
        ),
        "invalid_ordered_ohlc_sessions": int((finite_positive & ~ordered).sum()),
        "zero_body_bars": int(((bodies == 0.0) & ordered[:, None]).sum()),
        "up_body_bars": int(((bodies > 0.0) & ordered[:, None]).sum()),
        "down_body_bars": int(((bodies < 0.0) & ordered[:, None]).sum()),
        "zero_range_bars": int(((ranges == 0.0) & ordered[:, None]).sum()),
        "endpoint_canonicalized_sessions": int(
            (eligible & ((values == -1.0) | (values == 0.0) | (values == 1.0))).sum()
        ),
    }


_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["compute_directional_amount_timing_spread"] = compute_directional_range_mass_imbalance
_generated["extract_directional_amount_timing_spread"] = extract_directional_range_mass_imbalance

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
