from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign069_features as feature


def _frame(values: list[float], eligible: list[bool]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * len(values)),
            "symbol": [f"SH{600000 + index:06d}" for index in range(len(values))],
            "provider": ["eastmoney_quarterly_quality"] * len(values),
            feature.FACTOR_NAME: values,
            f"{feature.FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, list(feature.OUTPUT_COLUMNS)]


def test_campaign069_protocol_and_all_99_comparators_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons(spec)
    assert len(comparisons) == 99
    assert feature._comparison_order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "quarterly_profit_revenue_acceleration_rank_gap_2r",
        "score_direction": "higher",
    }
    unique = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert unique["complete_definition_count"] == 100
    assert unique["complete_definition_order_sha256"] == feature.FULL_DEFINITION_ORDER_SHA256
    assert unique["all_99_numeric_comparators_must_pass"] is True


def test_campaign069_rank_gap_formula_and_signed_value_semantics() -> None:
    values, eligible = feature.compute_gap_values(
        np.array(
            [
                [1.0, 0.25],
                [0.20, 0.80],
                [0.50, 0.50],
                [np.nan, 0.40],
            ]
        )
    )
    assert eligible.tolist() == [True, True, True, False]
    np.testing.assert_allclose(values[:3], [0.75, -0.60, 0.0])
    assert np.isnan(values[3])
    assert feature.validate_value_semantics(
        _frame([-1.0, -0.25, 0.0, 0.75, 1.0, np.nan], [True] * 5 + [False])
    ) == (6, 5)


def test_campaign069_signed_verifier_rejects_range_or_missingness_mismatch() -> None:
    with pytest.raises(feature.Campaign069FeatureError):
        feature.validate_value_semantics(_frame([-1.01], [True]))
    with pytest.raises(feature.Campaign069FeatureError):
        feature.validate_value_semantics(_frame([1.01], [True]))
    with pytest.raises(feature.Campaign069FeatureError):
        feature.validate_value_semantics(_frame([0.0], [False]))
    with pytest.raises(feature.Campaign069FeatureError):
        feature.validate_value_semantics(_frame([np.nan], [True]))


def test_campaign069_strict_next_session_and_independent_state_forward_fill() -> None:
    calendar = pd.DatetimeIndex(
        pd.to_datetime(["2020-04-30", "2020-05-06", "2020-05-07", "2020-05-08"])
    )
    events = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "report_date": pd.to_datetime(["2020-03-31", "2020-06-30"]),
            "announcement_date": pd.to_datetime(["2020-04-30", "2020-05-06"]),
            "roe": [10.0, np.nan],
            "profit_yoy": [np.nan, 20.0],
        }
    )
    positions, states = feature.prepare_events(events, calendar)["SH600000"]
    assert positions.tolist() == [1, 2]
    assert np.isnan(states[0, 0])
    assert states[0, 1] == 10.0
    np.testing.assert_allclose(states[1], [20.0, 10.0])

    identity = pd.DataFrame(
        {
            "trade_date": calendar,
            "symbol": ["SH600000"] * 4,
            "provider": ["tushare"] * 4,
        }
    )
    attached = feature.attach_states(
        identity,
        symbol="SH600000",
        calendar=calendar,
        events_by_symbol={"SH600000": (positions, states)},
    )
    assert attached.loc[0, ["profit_yoy", "roe"]].isna().all()
    assert np.isnan(attached.loc[1, "profit_yoy"])
    assert attached.loc[1, "roe"] == 10.0
    np.testing.assert_allclose(attached.loc[2:, ["profit_yoy", "roe"]], [[20.0, 10.0], [20.0, 10.0]])


def test_campaign069_daily_ranks_use_exact_common_finite_cross_section() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["SH600000", "SZ000001", "SZ000002", "SZ000003"],
            "provider": ["tushare"] * 4,
            "profit_yoy": [10.0, 10.0, 20.0, np.nan],
            "roe": [100.0, 200.0, 200.0, 300.0],
        }
    )
    result = feature.rank_and_gap_year_frame(frame)
    expected_profit = np.array([0.5, 0.5, 1.0, np.nan])
    expected_roe = np.array([1.0 / 3.0, 5.0 / 6.0, 5.0 / 6.0, np.nan])
    np.testing.assert_allclose(
        result[feature.FACTOR_NAME].to_numpy()[:3],
        expected_profit[:3] - expected_roe[:3],
    )
    assert result[f"{feature.FACTOR_NAME}_eligible"].tolist() == [
        True,
        True,
        True,
        False,
    ]


def test_campaign069_status_is_read_only_before_build() -> None:
    payload = feature.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
