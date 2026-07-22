"""Offline tests for the fingerprint-bound cleaned Tushare minute research."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "a_share_tushare_cleaned_minute_factor_research.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a_share_tushare_cleaned_minute_factor_research", SCRIPT_PATH
)
RESEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RESEARCH
SPEC.loader.exec_module(RESEARCH)


def test_frozen_preregistration_loads_exactly_four_retained_directions() -> None:
    spec = RESEARCH.load_preregistration()

    assert tuple(item["name"] for item in spec["factors"]) == RESEARCH.FACTOR_NAMES
    assert tuple(item["diagnostic_direction"] for item in spec["factors"]) == (
        "higher",
        "higher",
        "higher",
        "lower",
    )
    assert spec["explicit_exclusion"]["factor"] == "opening_gap_digestion"
    assert (
        spec["post_diagnostic_aggregation_policy"][
            "no_subset_direction_window_threshold_weight_or_aggregation_search"
        ]
        is True
    )
    assert (
        spec["post_diagnostic_aggregation_policy"][
            "same_history_combination_return_evaluation_allowed"
        ]
        is False
    )


def compact_test_spec() -> dict:
    spec = copy.deepcopy(RESEARCH.load_preregistration())
    coverage = spec["coverage_gate_before_forward_returns"]
    coverage["minimum_median_coverage"] = 0.70
    coverage["minimum_p05_coverage"] = 0.70
    coverage["minimum_names_per_factor_cross_section"] = 2
    coverage["minimum_potential_non_overlapping_three_session_cohorts"] = 1
    spec["historical_diagnostic"]["minimum_observed_calendar_years"] = 1
    return spec


def test_factor_specific_eligibility_does_not_drop_other_factors() -> None:
    dates = pd.bdate_range("2025-01-02", periods=8)
    symbols = ["SZ000001", "SZ000002", "SZ000003", "SZ000004"]
    market = pd.DataFrame(
        [
            {
                "datetime": date,
                "instrument": symbol,
                "open": 10.0,
                "close": 10.1,
                "quality_eligible": True,
                "fundamental_quality_eligible": True,
                "listing_seasoning_eligible": True,
                "listing_age_sessions": 100,
            }
            for date in dates
            for symbol in symbols
        ]
    )
    features = pd.DataFrame(
        [
            {
                "trade_date": date,
                "symbol": symbol,
                "late_return_30m": float(position + 1),
                "late_amount_share_30m": float(position + 1) / 10.0,
                "late_vwap_to_day_vwap_30m": float(position + 1) / 100.0,
                "intraday_realized_volatility": float(position + 1),
                "late_return_30m_eligible": True,
                "late_amount_share_30m_eligible": not (
                    date == dates[0] and symbol == symbols[0]
                ),
                "late_vwap_to_day_vwap_30m_eligible": True,
                "intraday_realized_volatility_eligible": True,
            }
            for date in dates
            for position, symbol in enumerate(symbols)
        ]
    )

    ranked, coverage = RESEARCH.attach_factor_specific_scores(
        market, features, compact_test_spec()
    )

    affected = ranked.loc[
        ranked["datetime"].eq(dates[0])
        & ranked["instrument"].astype(str).eq(symbols[0])
    ].iloc[0]
    assert np.isnan(affected["late_amount_share_30m"])
    assert np.isfinite(affected["late_return_30m"])
    assert np.isfinite(affected["late_vwap_to_day_vwap_30m"])
    assert np.isfinite(affected["intraday_realized_volatility"])
    assert coverage["coverage_gate_passed"] is True
    assert (
        coverage["factor_coverage"]["late_amount_share_30m"][
            "quality_and_factor_eligible_rows"
        ]
        == len(features) - 1
    )


def test_lower_realized_volatility_becomes_the_higher_score() -> None:
    dates = pd.bdate_range("2025-01-02", periods=8)
    symbols = ["SZ000001", "SZ000002", "SZ000003", "SZ000004"]
    rows = []
    for date in dates:
        for position, symbol in enumerate(symbols):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "late_return_30m": float(position),
                    "late_amount_share_30m": float(position) / 10.0,
                    "late_vwap_to_day_vwap_30m": float(position) / 100.0,
                    "intraday_realized_volatility": float(position + 1),
                    **{column: True for column in RESEARCH.FACTOR_ELIGIBILITY_COLUMNS},
                }
            )
    features = pd.DataFrame(rows)
    market = pd.DataFrame(
        [
            {
                "datetime": date,
                "instrument": symbol,
                "open": 10.0,
                "close": 10.1,
                "quality_eligible": True,
                "fundamental_quality_eligible": True,
                "listing_seasoning_eligible": True,
                "listing_age_sessions": 100,
            }
            for date in dates
            for symbol in symbols
        ]
    )

    ranked, _ = RESEARCH.attach_factor_specific_scores(
        market, features, compact_test_spec()
    )
    first_date = ranked.loc[ranked["datetime"].eq(dates[0])].set_index("instrument")

    assert first_date.loc[symbols[0], "intraday_realized_volatility"] == pytest.approx(
        1.0
    )
    assert first_date.loc[symbols[-1], "intraday_realized_volatility"] == pytest.approx(
        0.25
    )
    assert first_date.loc[symbols[-1], "late_return_30m"] == pytest.approx(1.0)


def test_consumption_marker_blocks_a_second_historical_read(tmp_path: Path) -> None:
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text(
        json.dumps({"forward_return_fields_read": True}), encoding="utf-8"
    )

    with pytest.raises(RESEARCH.CleanedMinuteResearchError, match="already consumed"):
        RESEARCH.require_unconsumed(tmp_path)
