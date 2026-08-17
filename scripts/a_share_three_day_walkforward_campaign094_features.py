#!/usr/bin/env python3
"""Build Campaign094's frozen range-local-peak clock-dispersion snapshot."""

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
FACTOR_NAME = "intraday_range_local_peak_clock_dispersion_236p"
FACTOR_FORMULA = (
    "within each 120-bar half set q_i=log(high_i/low_i), mark strict interior "
    "local peaks q_i>q_i-1 and q_i>q_i+1 for i=1..118, map x_i=i/119, "
    "require at least two peaks, compute population Var(x) separately in each "
    "half, and return their arithmetic mean"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
INTERIOR_COUNT_PER_HALF = 118
INTERIOR_OPPORTUNITY_COUNT = 236
CLOCK_DENOMINATOR = 119.0
MINIMUM_PEAKS_PER_HALF = 2
MAXIMUM_SCORE = 0.25


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
    ("Campaign093", "Campaign094"),
    ("campaign093", "campaign094"),
    ("campaign_093", "campaign_094"),
    ("wf093", "wf094"),
    ("intraday_close_transition_range_quadratic_efficiency_238p", FACTOR_NAME),
    (
        "a_share_three_day_walkforward_campaign092_features as c88",
        "a_share_three_day_walkforward_campaign093_features as c88",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_092_feature_snapshot_binding_20260807.json",
        "docs/a_share_three_day_walkforward_campaign_093_feature_snapshot_binding_20260807.json",
    ),
    (
        "campaign092_terminal_numeric_comparator",
        "campaign093_terminal_numeric_comparator",
    ),
    (
        "ce1752e170f6690e2b501f14964736792b6e13e6619e4be53fd9f640bda621b2",
        "c79c7ee277401f140bd075756658bfc5533ddcf191a20c4dc5e63808a50cbe27",
    ),
    (
        "c0f50dd19cfb983f08998fbafa80b9661872afc78074e806eefc8e5282019225",
        "87fc3886a1b4bf8c3d09e3cd86f229f09df2c2de4d87aaca8290f7f728ce15cf",
    ),
    (
        "0a6a79e05eb12c0303ba1c186d31adeca0d45abdea48b9de50101cde2523a57b",
        "e9efe53051038628c9e7a1822be374a9052ce6d5b7c6a012d4c2212e286a03aa",
    ),
    (
        "8e2d23139dbe5f423a5b96fb1230a2f5f0f3c04e3bced33753aa38ac5d7554f8",
        "0e0527d3f4fb5616f3eb7b24554eaa5fa71d354d89131193420cd1634de90fe0",
    ),
    (
        "2c6f6c152802e3f2f51843ed4054a1377eb8c1bd366583221bfbc7c45a0ae931",
        "8f58573bfc2c1e46bc31da2673d17d70c2aa470b112a898ac3ee1868facab233",
    ),
    (
        "06fbfcae04af4ce2a917601876b5047e5ac09f75cf19d17bebc0bca8d9ff019e",
        "69428173fd9a84f7272b56e253b589cb712355ce0b59a05e2a0b0b9576b82e92",
    ),
    (
        "7df85a0b3a75b203661de4d1695d8f75890fdc649efbee7739b4f2241ab93321",
        "bba3e4e71626b0ff2fa3860649da5187ef5c5412879b009f6890e9599ba3cf0b",
    ),
    ("FULL_DEFINITION_COUNT = 124", "FULL_DEFINITION_COUNT = 125"),
    (
        "a77f964349dd9c5d924bb8d6e2000682791cd765ff4b9c5c50576309cf815758",
        "3742401d8d87cbeb3a104545c25c1eb279832915f42dc46f1367dcbdc28f740c",
    ),
    ("COMPARISON_COUNT = 122", "COMPARISON_COUNT = 123"),
    (
        "8e5afb41c25060c7071e713ecc9589a6db8a706da5c441349dc298fca26da390",
        "b92614c1366ec480913854adace1cad0d926a0e89c8bbebca70c81bf486cac3a",
    ),
    ("all_122_numeric_comparators_must_pass", "all_123_numeric_comparators_must_pass"),
    ("numeric_comparator_policy_v36", "numeric_comparator_policy_v37"),
    ("v36", "v37"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    ),
    ("close_transition_count", "interior_local_peak_opportunity_count"),
    (
        "valid_close_transition_range_efficiency_sessions",
        "valid_range_local_peak_clock_dispersion_sessions",
    ),
    (
        "nonpositive_quadratic_mass_sessions",
        "insufficient_strict_local_peak_sessions",
    ),
    ("invalid_ordered_hlc_sessions", "invalid_ordered_hl_sessions"),
    ("zero_close_transition_pairs", "morning_strict_local_peaks"),
    ("positive_close_transition_pairs", "afternoon_strict_local_peaks"),
    ("zero_destination_range_pairs", "zero_range_bars"),
    (
        "close-transition/range quadratic-efficiency",
        "range-local-peak clock-dispersion",
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    '    ("v35", "v37"),',
    '    ("v35", "v37"),\n    ("[0.0, 1.0]", "[0.0, 0.25]"),',
)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign094_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _namespace)  # noqa: S102

_generated = _namespace["_generated"]
Campaign094FeatureError = _generated["Campaign094FeatureError"]


def load_protocol(
    path: Path = _generated["DEFAULT_PROTOCOL"],
) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != _generated["PROTOCOL_SHA256"]:
        raise Campaign094FeatureError(f"Campaign094 protocol changed: {path}")
    report = _generated["bindings"].validate_record(
        path, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign094FeatureError("Campaign094 protocol binding failed")
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
        raise Campaign094FeatureError("Campaign094 predecessor snapshot changed")
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    comparisons = _generated["reconstruct_comparisons"]()
    complete = _generated["reconstruct_complete_definitions"]()
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign094_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign094_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == _generated["MECHANISM_AUDIT_SHA256"]
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == _generated["CURRENT_STATE_SHA256"]
        and (chain.get("numeric_comparator_policy_v37") or {}).get("sha256")
        == _generated["NUMERIC_POLICY_SHA256"]
        and (chain.get("campaign093_terminal_numeric_comparator") or {}).get(
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
        and candidate.get("interior_local_peak_opportunity_count")
        == INTERIOR_OPPORTUNITY_COUNT
        and candidate.get("clock_denominator") == int(CLOCK_DENOMINATOR)
        and candidate.get("minimum_strict_local_peaks_per_half")
        == MINIMUM_PEAKS_PER_HALF
        and candidate.get("variance_convention")
        == "float64 population variance with ddof=0 computed separately by half then averaged"
        and candidate.get("valid_range")
        == {
            "lower": 0,
            "lower_inclusive": False,
            "upper": MAXIMUM_SCORE,
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
        and unique.get("all_123_numeric_comparators_must_pass") is True
        and len(comparisons) == _generated["COMPARISON_COUNT"]
        and len(complete) == _generated["FULL_DEFINITION_COUNT"]
        and finite.get("trial_id")
        == "wf094_intraday_range_local_peak_clock_dispersion_236p_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign094FeatureError("Campaign094 protocol semantics changed")
    return spec


_generated["load_protocol"] = load_protocol


def _peak_clock_variance(peaks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    clocks = np.arange(1, HALF_BAR_COUNT - 1, dtype=np.float64) / CLOCK_DENOMINATOR
    counts = peaks.sum(axis=1, dtype=np.int64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        means = np.sum(peaks * clocks[None, :], axis=1, dtype=np.float64) / counts
        centered = np.where(peaks, clocks[None, :] - means[:, None], 0.0)
        variances = np.sum(centered * centered, axis=1, dtype=np.float64) / counts
    return counts, variances


def compute_range_local_peak_clock_dispersion(
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Return score, eligibility, ranges, two peak masks, counts, and variances."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign094FeatureError("Campaign094 requires an n-by-240 high array")
    if low.shape != high.shape:
        raise Campaign094FeatureError(
            "Campaign094 requires matching n-by-240 HL arrays"
        )
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (low <= high).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(high / low)
    morning = ranges[:, :HALF_BAR_COUNT]
    afternoon = ranges[:, HALF_BAR_COUNT:]
    morning_peaks = (morning[:, 1:-1] > morning[:, :-2]) & (
        morning[:, 1:-1] > morning[:, 2:]
    )
    afternoon_peaks = (afternoon[:, 1:-1] > afternoon[:, :-2]) & (
        afternoon[:, 1:-1] > afternoon[:, 2:]
    )
    morning_counts, morning_variances = _peak_clock_variance(morning_peaks)
    afternoon_counts, afternoon_variances = _peak_clock_variance(afternoon_peaks)
    with np.errstate(invalid="ignore", over="ignore"):
        raw_score = (morning_variances + afternoon_variances) / 2.0
    support = (
        source_valid
        & np.isfinite(ranges).all(axis=1)
        & (ranges >= 0.0).all(axis=1)
        & (morning_counts >= MINIMUM_PEAKS_PER_HALF)
        & (afternoon_counts >= MINIMUM_PEAKS_PER_HALF)
        & np.isfinite(raw_score)
        & (raw_score > 0.0)
        & (raw_score <= MAXIMUM_SCORE)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    result[support] = raw_score[support]
    eligible = np.isfinite(result) & (result > 0.0) & (result <= MAXIMUM_SCORE)
    result[~eligible] = np.nan
    counts = np.column_stack((morning_counts, afternoon_counts))
    variances = np.column_stack((morning_variances, afternoon_variances))
    return (
        result,
        eligible,
        ranges,
        morning_peaks,
        afternoon_peaks,
        counts,
        variances,
    )


def extract_range_local_peak_clock_dispersion(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign094FeatureError(
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
        "valid_range_local_peak_clock_dispersion_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "insufficient_strict_local_peak_sessions": 0,
        "invalid_ordered_hl_sessions": 0,
        "morning_strict_local_peaks": 0,
        "afternoon_strict_local_peaks": 0,
        "zero_range_bars": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("high", "low"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign094FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign094FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=c86.CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign094FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for column in ("high", "low")
    }
    values, eligible, ranges, morning_peaks, afternoon_peaks, peak_counts, _ = (
        compute_range_local_peak_clock_dispersion(arrays["high"], arrays["low"])
    )
    finite_positive = np.logical_and.reduce(
        [
            np.isfinite(array).all(axis=1) & (array > 0.0).all(axis=1)
            for array in arrays.values()
        ]
    )
    ordered = finite_positive & (arrays["low"] <= arrays["high"]).all(axis=1)
    insufficient = ordered & (
        (peak_counts[:, 0] < MINIMUM_PEAKS_PER_HALF)
        | (peak_counts[:, 1] < MINIMUM_PEAKS_PER_HALF)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_range_local_peak_clock_dispersion_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "insufficient_strict_local_peak_sessions": int(insufficient.sum()),
        "invalid_ordered_hl_sessions": int((finite_positive & ~ordered).sum()),
        "morning_strict_local_peaks": int((morning_peaks & ordered[:, None]).sum()),
        "afternoon_strict_local_peaks": int((afternoon_peaks & ordered[:, None]).sum()),
        "zero_range_bars": int(((ranges == 0.0) & ordered[:, None]).sum()),
    }


_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["compute_directional_amount_timing_spread"] = (
    compute_range_local_peak_clock_dispersion
)
_generated["extract_directional_amount_timing_spread"] = (
    extract_range_local_peak_clock_dispersion
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
