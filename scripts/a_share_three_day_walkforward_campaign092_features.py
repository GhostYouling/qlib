#!/usr/bin/env python3
"""Build Campaign092's frozen interbar-gap discovery-share snapshot."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089_features.py"
BASE_RUNNER_SHA256 = "64c0dc5a2331446e9acf57a00411b67bf3543d49104d89cdde07c91e8c2ee407"
FACTOR_NAME = "intraday_interbar_gap_discovery_share_238p"
FACTOR_FORMULA = (
    "within each 120-bar half set g_j=abs(log(open_j/close_j-1)) and "
    "r_j=log(high_j/low_j) on each destination bar, pool 238 pairs, "
    "and return sum(g_j)/(sum(g_j)+sum(r_j))"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")
SELECTED_BAR_COUNT = 240
PAIR_COUNT = 238
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
    ("Campaign089", "Campaign092"),
    ("campaign089", "campaign092"),
    ("campaign_089", "campaign_092"),
    ("wf089", "wf092"),
    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),
    (
        "from scripts import a_share_three_day_walkforward_campaign088_features as c88",
        "from scripts import a_share_three_day_walkforward_campaign091_features as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_088_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_091_feature_snapshot_binding_20260807.json",
    ),
    ("campaign088_terminal_numeric_comparator", "campaign091_terminal_numeric_comparator"),
    ("444e6aecdd82ad8f9ca909063bb42a5bf6453b826067f637e2bc54977d14e1be", "fdab87de6012a2dd5e6f2538905f5ebc5464f3887242ac4a657a8545724500c5"),
    ("837621b6ee61f659e7b82f589758cea43b98143bb3e1f0aa2fbae3b6b3fd74a9", "013460b55e0a3243f60709092de3211e86b59c54cad4f5530bcb936b3044044e"),
    ("985f80fb46c1abdc4dc29f49e3525d292ca5632d67e7448d3f7ff00996ac4a37", "e8dc69caf835dbc31034ab119adfc96b4ebd2c3954081c5d4be1946408298a79"),
    ("5a8f14e6740fa6fabb72b0ef455d173502cfa4c0e1542f808852665afbb2fc35", "734949300e95958b968ce8a9280bbac764ec3be5752d2c3d0f810320574b10c5"),
    ("15a17b1db513901a3a56ac3e39768971a78e9319937c8ac18eb980d362a33064", "5f5fbdffeef54d0d648e8a7d36ffbdc12156142a61472720eae161b29f2cdab3"),
    ("fd244df87c30d273f53e376561d03956c91f326237ae78cb16dc57906a136d41", "1caf67c6b65947e4407f3064f732bf33a7595b9df977c8d62236c321c91e4541"),
    ("022e0bed5b6dc3ea50e069c44aa4e834aeaa6ec65444e87d75287cbeedf3d756", "e179abf89f0ef956e22508c00ca198a6cf612b25700c5b8612f1d3d6d383e6fa"),
    ("FULL_DEFINITION_COUNT = 120", "FULL_DEFINITION_COUNT = 123"),
    ("9f0d70e832e7a1e5a62a312d79441621eda5822ff3de9155edc108409dcdb276", "c83a044523c018cd3bc52bd3f0a4aacea66123ca2a53b5066371594ad7a053e3"),
    ("COMPARISON_COUNT = 118", "COMPARISON_COUNT = 121"),
    ("a83d4485182d4dc6a2173af4c3158a3290939740c5465991a69521fdc65607c2", "23e370e5e18baa7069948012b6999e60253a0502f0733cde7d20b3462149d649"),
    ("all_118_numeric_comparators_must_pass", "all_121_numeric_comparators_must_pass"),
    ("numeric_comparator_policy_v28", "numeric_comparator_policy_v35"),
    ("v28", "v35"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
    ),
    ("selected_close_count", "selected_bar_count"),
    ("total_return_count", "gap_pair_count"),
    ("destination_amount_count", "destination_range_count"),
    (
        'candidate.get("clock_coordinate_denominator") == CLOCK_DENOMINATOR',
        'candidate.get("destination_range_count") == RETURN_COUNT',
    ),
    ("valid_directional_timing_sessions", "valid_interbar_gap_discovery_sessions"),
    ("nonpositive_up_mass_sessions", "nonpositive_gap_range_mass_sessions"),
    ("nonpositive_down_mass_sessions", "invalid_ordered_ohlc_sessions"),
    ("zero_returns", "zero_gap_pairs"),
    ("zero_destination_amounts", "zero_destination_range_pairs"),
    ("[-1.0, 1.0]", "[0.0, 1.0]"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign092_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign092FeatureError = _generated["Campaign092FeatureError"]


def compute_interbar_gap_discovery_share(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, G, R, 238 gaps, and destination ranges."""

    open_ = np.asarray(opens, dtype=np.float64)
    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if open_.ndim != 2 or open_.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign092FeatureError("Campaign092 requires an n-by-240 open array")
    if high.shape != open_.shape or low.shape != open_.shape or close.shape != open_.shape:
        raise Campaign092FeatureError("Campaign092 requires matching n-by-240 OHLC arrays")
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
    previous_closes = np.concatenate((close[:, :119], close[:, 120:239]), axis=1)
    destination_opens = np.concatenate((open_[:, 1:120], open_[:, 121:240]), axis=1)
    destination_highs = np.concatenate((high[:, 1:120], high[:, 121:240]), axis=1)
    destination_lows = np.concatenate((low[:, 1:120], low[:, 121:240]), axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        gaps = np.abs(np.log(destination_opens / previous_closes))
        destination_ranges = np.log(destination_highs / destination_lows)
        gap_mass = np.sum(gaps, axis=1, dtype=np.float64)
        range_mass = np.sum(destination_ranges, axis=1, dtype=np.float64)
        denominator = gap_mass + range_mass
        raw_score = gap_mass / denominator
    support = (
        source_valid
        & np.isfinite(gaps).all(axis=1)
        & (gaps >= 0.0).all(axis=1)
        & np.isfinite(destination_ranges).all(axis=1)
        & (destination_ranges >= 0.0).all(axis=1)
        & np.isfinite(gap_mass)
        & np.isfinite(range_mass)
        & np.isfinite(denominator)
        & (denominator > 0.0)
        & np.isfinite(raw_score)
    )
    result = np.full(len(open_), np.nan, dtype=np.float64)
    candidate = raw_score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    valid_score = np.isfinite(candidate) & (candidate >= 0.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, gap_mass, range_mass, gaps, destination_ranges


def extract_interbar_gap_discovery_share(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign092FeatureError(
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
        "valid_interbar_gap_discovery_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_gap_range_mass_sessions": 0,
        "invalid_ordered_ohlc_sessions": 0,
        "zero_gap_pairs": 0,
        "positive_gap_pairs": 0,
        "zero_destination_range_pairs": 0,
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
        raise Campaign092FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign092FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign092FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column].to_numpy(dtype=np.float64).reshape(
            len(dates), SELECTED_BAR_COUNT
        )
        for column in ("open", "high", "low", "close")
    }
    values, eligible, gap_mass, range_mass, gaps, destination_ranges = (
        compute_interbar_gap_discovery_share(
            arrays["open"], arrays["high"], arrays["low"], arrays["close"]
        )
    )
    finite_positive = np.logical_and.reduce(
        [
            np.isfinite(array).all(axis=1) & (array > 0.0).all(axis=1)
            for array in arrays.values()
        ]
    )
    ordered = (
        finite_positive
        & (arrays["low"] <= arrays["open"]).all(axis=1)
        & (arrays["open"] <= arrays["high"]).all(axis=1)
        & (arrays["low"] <= arrays["close"]).all(axis=1)
        & (arrays["close"] <= arrays["high"]).all(axis=1)
    )
    denominator = gap_mass + range_mass
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_interbar_gap_discovery_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_gap_range_mass_sessions": int(
            (ordered & (~np.isfinite(denominator) | (denominator <= 0.0))).sum()
        ),
        "invalid_ordered_ohlc_sessions": int((finite_positive & ~ordered).sum()),
        "zero_gap_pairs": int(((gaps == 0.0) & ordered[:, None]).sum()),
        "positive_gap_pairs": int(((gaps > 0.0) & ordered[:, None]).sum()),
        "zero_destination_range_pairs": int(
            ((destination_ranges == 0.0) & ordered[:, None]).sum()
        ),
        "endpoint_canonicalized_sessions": int(
            (eligible & ((values == 0.0) | (values == 1.0))).sum()
        ),
    }


_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["compute_directional_amount_timing_spread"] = (
    compute_interbar_gap_discovery_share
)
_generated["extract_directional_amount_timing_spread"] = (
    extract_interbar_gap_discovery_share
)

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
