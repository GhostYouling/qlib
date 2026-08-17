#!/usr/bin/env python3
"""Build Campaign095's frozen own-bar close-location entropy snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign093_features.py"
)
BASE_RUNNER_SHA256 = "9e96f59ac747e725e186f4d749ae9b3d8f7108d0409ce26aee6100cf1bb1bef0"
FACTOR_NAME = "intraday_own_bar_close_location_entropy_10b_240m"
FACTOR_FORMULA = (
    "for every positive-range selected bar set x=(log(close)-log(low))/"
    "(log(high)-log(low)), map x to ten fixed equal-width bins with exact "
    "x=1 in bin 9, require at least 120 informative bars, and return "
    "normalized Shannon entropy over the ten counts"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")
SELECTED_BAR_COUNT = 240
BIN_COUNT = 10
MINIMUM_INFORMATIVE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign093 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign093", "Campaign095"),
    ("campaign093", "campaign095"),
    ("campaign_093", "campaign_095"),
    ("wf093", "wf095"),
    ("intraday_close_transition_range_quadratic_efficiency_238p", FACTOR_NAME),
    (
        "a_share_three_day_walkforward_campaign092_features as c88",
        "a_share_three_day_walkforward_campaign094_features_v4 as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_092_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_094_feature_snapshot_binding_20260807.json",
    ),
    ("campaign092_terminal_numeric_comparator", "campaign094_terminal_numeric_comparator"),
    (
        "ce1752e170f6690e2b501f14964736792b6e13e6619e4be53fd9f640bda621b2",
        "195500baf00a6acde553939280cef53ea4303db915cb29746fa3f382001dd9b3",
    ),
    (
        "c0f50dd19cfb983f08998fbafa80b9661872afc78074e806eefc8e5282019225",
        "9cb39096e7f4ba1b1f82b24c55541faf90fdc3d9cfa0c5348b0040c4645be0fc",
    ),
    (
        "0a6a79e05eb12c0303ba1c186d31adeca0d45abdea48b9de50101cde2523a57b",
        "b51f2a4b365652c760838f93ffb3e4cfea69546edfaf39acab972e231bab0939",
    ),
    (
        "8e2d23139dbe5f423a5b96fb1230a2f5f0f3c04e3bced33753aa38ac5d7554f8",
        "38994cc61f350f40a9a85d75a30a6e36831d968416799284413247e8d2cd4b42",
    ),
    (
        "2c6f6c152802e3f2f51843ed4054a1377eb8c1bd366583221bfbc7c45a0ae931",
        "dc5778ad0788ed3bd0cc3fc8980110c5f741be29068f3eccad03144eccadf358",
    ),
    (
        "06fbfcae04af4ce2a917601876b5047e5ac09f75cf19d17bebc0bca8d9ff019e",
        "1f1441e59bcef1cb3d18b0030c640453e2ee762668d05157dec9ca1c0f01c340",
    ),
    (
        "7df85a0b3a75b203661de4d1695d8f75890fdc649efbee7739b4f2241ab93321",
        "37865a7d4c5556ee9a79ba9550f0f05229e3c52bb511d8bd1ac3b1f2525a6b63",
    ),
    ("FULL_DEFINITION_COUNT = 124", "FULL_DEFINITION_COUNT = 126"),
    (
        "a77f964349dd9c5d924bb8d6e2000682791cd765ff4b9c5c50576309cf815758",
        "332d461e2b00bf6645eeb74cd59d3710d63f88b34add8afaadf4807ea712263d",
    ),
    ("COMPARISON_COUNT = 122", "COMPARISON_COUNT = 124"),
    (
        "8e5afb41c25060c7071e713ecc9589a6db8a706da5c441349dc298fca26da390",
        "d05f1cb7b68e950d508f2b0d13b7ef1847904edc6eb10453405917e04ed0e698",
    ),
    ("all_122_numeric_comparators_must_pass", "all_124_numeric_comparators_must_pass"),
    ("numeric_comparator_policy_v36", "numeric_comparator_policy_v38"),
    ("v36", "v38"),
    ("close_transition_count", "selected_bar_count"),
    (
        "valid_close_transition_range_efficiency_sessions",
        "valid_own_bar_close_location_entropy_sessions",
    ),
    (
        "nonpositive_quadratic_mass_sessions",
        "insufficient_informative_close_location_sessions",
    ),
    ("zero_close_transition_pairs", "informative_close_location_bars"),
    ("positive_close_transition_pairs", "zero_range_bars"),
    ("zero_destination_range_pairs", "occupied_close_location_bins"),
    ("endpoint_canonicalized_sessions", "endpoint_close_location_states"),
    (
        "close-transition/range quadratic-efficiency",
        "own-bar close-location fixed-bin entropy",
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign095_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _namespace)  # noqa: S102

_generated = _namespace["_generated"]
Campaign095FeatureError = _namespace["Campaign095FeatureError"]


def load_protocol(
    path: Path = _generated["DEFAULT_PROTOCOL"],
) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != _generated["PROTOCOL_SHA256"]:
        raise Campaign095FeatureError(f"Campaign095 protocol changed: {path}")
    report = _generated["bindings"].validate_record(
        path, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign095FeatureError("Campaign095 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous_path = _generated["C88_SNAPSHOT_MANIFEST"]
    if (
        not previous_path.is_file()
        or _sha256(previous_path) != _generated["C88_SNAPSHOT_MANIFEST_SHA256"]
    ):
        raise Campaign095FeatureError("Campaign095 predecessor snapshot changed")
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    comparisons = _generated["reconstruct_comparisons"]()
    complete = _generated["reconstruct_complete_definitions"]()
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign095_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign095_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == _generated["MECHANISM_AUDIT_SHA256"]
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == _generated["CURRENT_STATE_SHA256"]
        and (chain.get("numeric_comparator_policy_v38") or {}).get("sha256")
        == _generated["NUMERIC_POLICY_SHA256"]
        and (chain.get("campaign094_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == _generated["C88_SNAPSHOT_DATASET_SHA256"]
        and previous.get("dataset_sha256") == _generated["C88_SNAPSHOT_DATASET_SHA256"]
        and previous.get("factor_names") == [_generated["c88"].FACTOR_NAME]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == _generated["IDENTITY_COLUMNS"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("fixed_bin_count") == BIN_COUNT
        and candidate.get("minimum_informative_positive_range_bars")
        == MINIMUM_INFORMATIVE_BARS
        and candidate.get("endpoint_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
            "lower": 0,
            "lower_inclusive": True,
            "upper": 1,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count")
        == _generated["FULL_DEFINITION_COUNT"]
        and unique.get("complete_definition_order_sha256")
        == _generated["FULL_DEFINITION_ORDER_SHA256"]
        and unique.get("numeric_comparator_count") == _generated["COMPARISON_COUNT"]
        and unique.get("numeric_comparator_order_sha256")
        == _generated["COMPARISON_ORDER_SHA256"]
        and unique.get("all_124_numeric_comparators_must_pass") is True
        and len(comparisons) == _generated["COMPARISON_COUNT"]
        and len(complete) == _generated["FULL_DEFINITION_COUNT"]
        and finite.get("trial_id")
        == "wf095_intraday_own_bar_close_location_entropy_10b_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign095FeatureError("Campaign095 protocol semantics changed")
    return spec


def compute_own_bar_close_location_entropy(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Return score, eligibility, states, informative mask, bins, and counts."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign095FeatureError("Campaign095 requires an n-by-240 high array")
    if low.shape != high.shape or close.shape != high.shape:
        raise Campaign095FeatureError("Campaign095 requires matching n-by-240 HLC arrays")
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
    positive_range = high > low
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denominator = np.log(high) - np.log(low)
        states = (np.log(close) - np.log(low)) / denominator
    states[~positive_range] = np.nan
    near_zero = np.isfinite(states) & (np.abs(states) <= ENDPOINT_TOLERANCE)
    near_one = np.isfinite(states) & (np.abs(states - 1.0) <= ENDPOINT_TOLERANCE)
    states[near_zero] = 0.0
    states[near_one] = 1.0
    informative = (
        positive_range
        & np.isfinite(states)
        & (states >= 0.0)
        & (states <= 1.0)
    )
    invalid_positive_range_state = positive_range & ~informative
    bins = np.full(high.shape, -1, dtype=np.int8)
    scaled = np.floor(BIN_COUNT * states[informative]).astype(np.int64)
    scaled[scaled == BIN_COUNT] = BIN_COUNT - 1
    bins[informative] = scaled.astype(np.int8)
    counts = np.column_stack(
        [(bins == index).sum(axis=1, dtype=np.int64) for index in range(BIN_COUNT)]
    )
    informative_counts = counts.sum(axis=1, dtype=np.int64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        probabilities = counts / informative_counts[:, None]
        entropy_terms = np.where(
            counts > 0, probabilities * np.log(probabilities), 0.0
        )
        raw_score = -np.sum(entropy_terms, axis=1, dtype=np.float64) / np.log(
            float(BIN_COUNT)
        )
    support = (
        source_valid
        & ~invalid_positive_range_state.any(axis=1)
        & (informative_counts >= MINIMUM_INFORMATIVE_BARS)
        & np.isfinite(raw_score)
        & (raw_score >= 0.0)
        & (raw_score <= 1.0)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    result[support] = raw_score[support]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, states, informative, bins, counts


def extract_own_bar_close_location_entropy(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign095FeatureError(
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
        "valid_own_bar_close_location_entropy_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "insufficient_informative_close_location_sessions": 0,
        "invalid_ordered_hlc_sessions": 0,
        "informative_close_location_bars": 0,
        "zero_range_bars": 0,
        "occupied_close_location_bins": 0,
        "endpoint_close_location_states": 0,
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
        raise Campaign095FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    session_sizes = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    c86 = _generated["c86"]
    if (
        session_sizes.empty
        or not session_sizes.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign095FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=c86.CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(session_sizes.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign095FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for column in ("high", "low", "close")
    }
    values, eligible, states, informative, _bins, bin_counts = (
        compute_own_bar_close_location_entropy(
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
    informative_counts = informative.sum(axis=1, dtype=np.int64)
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_own_bar_close_location_entropy_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "insufficient_informative_close_location_sessions": int(
            (ordered & (informative_counts < MINIMUM_INFORMATIVE_BARS)).sum()
        ),
        "invalid_ordered_hlc_sessions": int((finite_positive & ~ordered).sum()),
        "informative_close_location_bars": int(
            (informative & ordered[:, None]).sum()
        ),
        "zero_range_bars": int(
            ((arrays["high"] == arrays["low"]) & ordered[:, None]).sum()
        ),
        "occupied_close_location_bins": int(
            ((bin_counts > 0) & ordered[:, None]).sum()
        ),
        "endpoint_close_location_states": int(
            (
                informative
                & ordered[:, None]
                & ((states == 0.0) | (states == 1.0))
            ).sum()
        ),
    }


_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["load_protocol"] = load_protocol
_generated["compute_directional_amount_timing_spread"] = (
    compute_own_bar_close_location_entropy
)
_generated["extract_directional_amount_timing_spread"] = (
    extract_own_bar_close_location_entropy
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
