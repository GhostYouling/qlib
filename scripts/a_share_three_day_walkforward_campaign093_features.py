#!/usr/bin/env python3
"""Build Campaign093's frozen close-transition/range efficiency snapshot."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign092_features.py"
)
BASE_RUNNER_SHA256 = "7c951f408d99a15244b952e3ef12816f2d464fc9878b206107ea953ec3678d52"
FACTOR_NAME = "intraday_close_transition_range_quadratic_efficiency_238p"
FACTOR_FORMULA = (
    "within each 120-bar half set c_j=log(close_j/close_j-1) and "
    "h_j=log(high_j/low_j) on each destination bar, pool 238 pairs, "
    "and return sum(c_j^2)/(sum(c_j^2)+sum(h_j^2))"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")
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
    raise RuntimeError("frozen Campaign092 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign092", "Campaign093"),
    ("campaign092", "campaign093"),
    ("campaign_092", "campaign_093"),
    ("wf092", "wf093"),
    ("intraday_interbar_gap_discovery_share_238p", FACTOR_NAME),
    (
        "a_share_three_day_walkforward_campaign091_features as c88",
        "a_share_three_day_walkforward_campaign092_features as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_091_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_092_feature_snapshot_binding_20260807.json",
    ),
    (
        "campaign091_terminal_numeric_comparator",
        "campaign092_terminal_numeric_comparator",
    ),
    (
        "fdab87de6012a2dd5e6f2538905f5ebc5464f3887242ac4a657a8545724500c5",
        "ce1752e170f6690e2b501f14964736792b6e13e6619e4be53fd9f640bda621b2",
    ),
    (
        "013460b55e0a3243f60709092de3211e86b59c54cad4f5530bcb936b3044044e",
        "c0f50dd19cfb983f08998fbafa80b9661872afc78074e806eefc8e5282019225",
    ),
    (
        "e8dc69caf835dbc31034ab119adfc96b4ebd2c3954081c5d4be1946408298a79",
        "0a6a79e05eb12c0303ba1c186d31adeca0d45abdea48b9de50101cde2523a57b",
    ),
    (
        "734949300e95958b968ce8a9280bbac764ec3be5752d2c3d0f810320574b10c5",
        "8e2d23139dbe5f423a5b96fb1230a2f5f0f3c04e3bced33753aa38ac5d7554f8",
    ),
    (
        "5f5fbdffeef54d0d648e8a7d36ffbdc12156142a61472720eae161b29f2cdab3",
        "2c6f6c152802e3f2f51843ed4054a1377eb8c1bd366583221bfbc7c45a0ae931",
    ),
    (
        "1caf67c6b65947e4407f3064f732bf33a7595b9df977c8d62236c321c91e4541",
        "06fbfcae04af4ce2a917601876b5047e5ac09f75cf19d17bebc0bca8d9ff019e",
    ),
    (
        "e179abf89f0ef956e22508c00ca198a6cf612b25700c5b8612f1d3d6d383e6fa",
        "7df85a0b3a75b203661de4d1695d8f75890fdc649efbee7739b4f2241ab93321",
    ),
    ("FULL_DEFINITION_COUNT = 123", "FULL_DEFINITION_COUNT = 124"),
    (
        "c83a044523c018cd3bc52bd3f0a4aacea66123ca2a53b5066371594ad7a053e3",
        "a77f964349dd9c5d924bb8d6e2000682791cd765ff4b9c5c50576309cf815758",
    ),
    ("COMPARISON_COUNT = 121", "COMPARISON_COUNT = 122"),
    (
        "23e370e5e18baa7069948012b6999e60253a0502f0733cde7d20b3462149d649",
        "8e5afb41c25060c7071e713ecc9589a6db8a706da5c441349dc298fca26da390",
    ),
    ("all_121_numeric_comparators_must_pass", "all_122_numeric_comparators_must_pass"),
    ("numeric_comparator_policy_v35", "numeric_comparator_policy_v36"),
    ("v35", "v36"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "high", "low", "close")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
    ),
    ("gap_pair_count", "close_transition_count"),
    (
        "valid_interbar_gap_discovery_sessions",
        "valid_close_transition_range_efficiency_sessions",
    ),
    ("nonpositive_gap_range_mass_sessions", "nonpositive_quadratic_mass_sessions"),
    ("invalid_ordered_ohlc_sessions", "invalid_ordered_hlc_sessions"),
    ("zero_gap_pairs", "zero_close_transition_pairs"),
    ("positive_gap_pairs", "positive_close_transition_pairs"),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    '    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),',
    '    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),\n'
    '    ("directional amount-timing-spread", '
    '"close-transition/range quadratic-efficiency"),',
)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign093_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _namespace)  # noqa: S102

_generated = _namespace["_generated"]
Campaign093FeatureError = _namespace["Campaign093FeatureError"]


def compute_close_transition_range_quadratic_efficiency(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, Q, H, 238 close transitions, and ranges."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign093FeatureError("Campaign093 requires an n-by-240 high array")
    if low.shape != high.shape or close.shape != high.shape:
        raise Campaign093FeatureError(
            "Campaign093 requires matching n-by-240 HLC arrays"
        )
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
        & (low <= close).all(axis=1)
        & (close <= high).all(axis=1)
    )
    previous_closes = np.concatenate((close[:, :119], close[:, 120:239]), axis=1)
    destination_closes = np.concatenate((close[:, 1:120], close[:, 121:240]), axis=1)
    destination_highs = np.concatenate((high[:, 1:120], high[:, 121:240]), axis=1)
    destination_lows = np.concatenate((low[:, 1:120], low[:, 121:240]), axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        transitions = np.log(destination_closes / previous_closes)
        destination_ranges = np.log(destination_highs / destination_lows)
        transition_quadratic_mass = np.sum(
            transitions * transitions, axis=1, dtype=np.float64
        )
        range_quadratic_mass = np.sum(
            destination_ranges * destination_ranges, axis=1, dtype=np.float64
        )
        denominator = transition_quadratic_mass + range_quadratic_mass
        raw_score = transition_quadratic_mass / denominator
    support = (
        source_valid
        & np.isfinite(transitions).all(axis=1)
        & np.isfinite(destination_ranges).all(axis=1)
        & (destination_ranges >= 0.0).all(axis=1)
        & np.isfinite(transition_quadratic_mass)
        & (transition_quadratic_mass >= 0.0)
        & np.isfinite(range_quadratic_mass)
        & (range_quadratic_mass >= 0.0)
        & np.isfinite(denominator)
        & (denominator > 0.0)
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
    return (
        result,
        eligible,
        transition_quadratic_mass,
        range_quadratic_mass,
        transitions,
        destination_ranges,
    )


def extract_close_transition_range_quadratic_efficiency(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign093FeatureError(
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
        "valid_close_transition_range_efficiency_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_quadratic_mass_sessions": 0,
        "invalid_ordered_hlc_sessions": 0,
        "zero_close_transition_pairs": 0,
        "positive_close_transition_pairs": 0,
        "zero_destination_range_pairs": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign093FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    c86 = _generated["c86"]
    if (
        counts.empty
        or not counts.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign093FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=c86.CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign093FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for column in ("high", "low", "close")
    }
    values, eligible, q_mass, h_mass, transitions, destination_ranges = (
        compute_close_transition_range_quadratic_efficiency(
            arrays["high"], arrays["low"], arrays["close"]
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
        & (arrays["low"] <= arrays["close"]).all(axis=1)
        & (arrays["close"] <= arrays["high"]).all(axis=1)
    )
    denominator = q_mass + h_mass
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_close_transition_range_efficiency_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_quadratic_mass_sessions": int(
            (ordered & (~np.isfinite(denominator) | (denominator <= 0.0))).sum()
        ),
        "invalid_ordered_hlc_sessions": int((finite_positive & ~ordered).sum()),
        "zero_close_transition_pairs": int(
            ((transitions == 0.0) & ordered[:, None]).sum()
        ),
        "positive_close_transition_pairs": int(
            ((np.abs(transitions) > 0.0) & ordered[:, None]).sum()
        ),
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
    compute_close_transition_range_quadratic_efficiency
)
_generated["extract_directional_amount_timing_spread"] = (
    extract_close_transition_range_quadratic_efficiency
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
