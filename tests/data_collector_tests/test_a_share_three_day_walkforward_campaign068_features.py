from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign068_features as feature


def test_campaign068_protocol_and_complete_comparator_order_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons(spec)
    assert len(comparisons) == 98
    assert feature._comparison_order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "quarterly_roe_profit_scale_efficiency_gap_2r",
        "score_direction": "higher",
    }
    unique = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert unique["complete_definition_count"] == 99
    assert unique["complete_definition_order_sha256"] == feature.FULL_DEFINITION_ORDER_SHA256
    assert unique["all_98_numeric_comparators_must_pass"] is True


def test_campaign068_rank_gap_formula_and_missing_semantics() -> None:
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


def test_campaign068_same_fiscal_quarter_acceleration_and_strict_availability() -> None:
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            [
                "2019-04-30",
                "2019-05-06",
                "2020-04-30",
                "2020-05-06",
                "2021-04-30",
                "2021-05-06",
            ]
        )
    )
    events = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000", "SH600000"],
            "report_date": pd.to_datetime(
                ["2019-03-31", "2020-03-31", "2021-03-31"]
            ),
            "announcement_date": pd.to_datetime(
                ["2019-04-30", "2020-04-30", "2021-04-30"]
            ),
            "revenue_yoy": [100.0, 120.0, 125.0],
            "profit_yoy": [40.0, 55.0, 50.0],
        }
    )
    prepared = feature.prepare_events(events, calendar)["SH600000"]
    positions, states = prepared
    assert positions.tolist() == [1, 3, 5]
    assert np.isnan(states[0]).all()
    np.testing.assert_allclose(states[1], [15.0, 20.0])
    np.testing.assert_allclose(states[2], [-5.0, 5.0])


def test_campaign068_year_rank_uses_average_ties_for_both_accelerations() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["SH600000", "SZ000001", "SZ000002", "SZ000003"],
            "provider": ["tushare"] * 4,
            "profit_yoy_acceleration": [10.0, 10.0, 20.0, np.nan],
            "revenue_yoy_acceleration": [100.0, 200.0, 200.0, 300.0],
        }
    )
    result = feature.rank_and_gap_year_frame(frame)
    expected_profit = np.array([0.5, 0.5, 1.0, np.nan])
    expected_revenue = np.array([0.25, 0.625, 0.625, 1.0])
    np.testing.assert_allclose(
        result[feature.FACTOR_NAME].to_numpy()[:3],
        expected_profit[:3] - expected_revenue[:3],
    )
    assert result[f"{feature.FACTOR_NAME}_eligible"].tolist() == [
        True,
        True,
        True,
        False,
    ]


def test_campaign068_status_is_read_only_before_build() -> None:
    payload = feature.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
