from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign084_features as feature


def test_campaign084_protocol_and_complete_orders_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons(spec)
    definitions = feature.reconstruct_complete_definitions()
    assert len(comparisons) == 113
    assert len(definitions) == 115
    assert (
        feature._comparison_order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    )
    assert (
        feature._comparison_order_digest(definitions)
        == feature.FULL_DEFINITION_ORDER_SHA256
    )
    assert comparisons[-1] == {
        "name": "intraday_close_frontier_innovation_share_238p",
        "score_direction": "higher",
    }
    unique = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert unique["all_113_numeric_comparators_must_pass"] is True
    assert spec["candidate"]["campaign083_factor_used_or_combined"] is False


def test_campaign084_floor_formula_and_missing_semantics() -> None:
    values, eligible = feature.compute_floor_values(
        np.array(
            [
                [1.0, 0.25],
                [0.20, 0.80],
                [0.50, 0.50],
                [np.nan, 0.40],
                [0.0, 0.80],
                [1.01, 0.80],
            ]
        )
    )
    assert eligible.tolist() == [True, True, True, False, False, False]
    np.testing.assert_allclose(values[:3], [0.25, 0.20, 0.50])
    assert np.isnan(values[3:]).all()


def test_campaign084_floor_requires_exactly_two_rank_columns() -> None:
    with pytest.raises(feature.Campaign084FeatureError):
        feature.compute_floor_values(np.ones((3, 3)))


def test_campaign084_same_fiscal_quarter_acceleration_and_strict_availability() -> None:
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
            "report_date": pd.to_datetime(["2019-03-31", "2020-03-31", "2021-03-31"]),
            "announcement_date": pd.to_datetime(
                ["2019-04-30", "2020-04-30", "2021-04-30"]
            ),
            "profit_yoy": [40.0, 55.0, 50.0],
        }
    )
    positions, states = feature.prepare_events(events, calendar)["SH600000"]
    assert positions.tolist() == [1, 3, 5]
    np.testing.assert_allclose(states[:, 0], [40.0, 55.0, 50.0])
    assert np.isnan(states[0, 1])
    np.testing.assert_allclose(states[1:, 1], [15.0, -5.0])


def test_campaign084_year_rank_uses_common_finite_universe_and_average_ties() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["SH600000", "SZ000001", "SZ000002", "SZ000003"],
            "provider": ["tushare"] * 4,
            "profit_yoy": [10.0, 10.0, 20.0, 30.0],
            "profit_yoy_acceleration": [100.0, 200.0, 200.0, np.nan],
        }
    )
    result = feature.rank_and_floor_year_frame(frame)
    expected_level = np.array([0.5, 0.5, 1.0])
    expected_acceleration = np.array([1.0 / 3.0, 5.0 / 6.0, 5.0 / 6.0])
    np.testing.assert_allclose(
        result[feature.FACTOR_NAME].to_numpy()[:3],
        np.minimum(expected_level, expected_acceleration),
    )
    assert result[f"{feature.FACTOR_NAME}_eligible"].tolist() == [
        True,
        True,
        True,
        False,
    ]
    assert np.isnan(result[feature.FACTOR_NAME].iloc[3])


def test_campaign084_partition_value_semantics_fail_closed() -> None:
    valid = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
            "symbol": ["SH600000", "SH600000"],
            "provider": ["eastmoney_quarterly_quality"] * 2,
            feature.FACTOR_NAME: [0.25, np.nan],
            f"{feature.FACTOR_NAME}_eligible": [True, False],
        }
    ).loc[:, feature.OUTPUT_COLUMNS]
    assert feature.validate_value_semantics(valid) == (2, 1)
    invalid = valid.copy()
    invalid.loc[0, feature.FACTOR_NAME] = 0.0
    with pytest.raises(feature.Campaign084FeatureError):
        feature.validate_value_semantics(invalid)


def test_campaign084_status_is_read_only_before_build() -> None:
    payload = feature.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
