from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign072_features as c72


def test_campaign072_protocol_and_complete_comparison_order_are_frozen() -> None:
    spec = c72.load_protocol()
    comparisons = c72.reconstruct_comparisons(spec)
    assert len(comparisons) == 102
    assert comparisons[-1] == {
        "name": "quarterly_net_profit_scale_rank",
        "score_direction": "higher",
    }
    assert (
        c72._runtime["_comparison_order_digest"](comparisons)
        == c72.COMPARISON_ORDER_SHA256
    )
    policy = json.loads(
        (
            c72.REPO_ROOT
            / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v6_20260806.json"
        ).read_text(encoding="utf-8")
    )
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 103
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 102


def test_campaign072_strict_next_session_and_independent_forward_fill() -> None:
    calendar = pd.DatetimeIndex(pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-06", "2021-01-07"]))
    events = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "report_date": pd.to_datetime(["2020-09-30", "2020-12-31"]),
            "announcement_date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
            "profit_yoy": [12.0, np.nan],
            "revenue_yoy": [np.nan, 8.0],
        }
    ).loc[:, c72.EVENT_FIELDS]
    prepared = c72.prepare_events(events, calendar)
    positions, states = prepared["SH600000"]
    np.testing.assert_array_equal(positions, np.array([1, 2]))
    assert np.isnan(states[0, 1])
    np.testing.assert_allclose(states[1], np.array([12.0, 8.0]))
    identity = pd.DataFrame(
        {
            "trade_date": calendar,
            "symbol": ["SH600000"] * len(calendar),
            "provider": ["tushare"] * len(calendar),
        }
    )
    attached = c72.attach_states(
        identity,
        symbol="SH600000",
        calendar=calendar,
        events_by_symbol=prepared,
    )
    assert attached.loc[0, list(c72.STATE_FIELDS)].isna().all()
    assert attached.loc[1, "profit_yoy"] == 12.0
    assert np.isnan(attached.loc[1, "revenue_yoy"])
    np.testing.assert_allclose(
        attached.loc[2:, list(c72.STATE_FIELDS)].to_numpy(dtype=float),
        np.array([[12.0, 8.0], [12.0, 8.0]]),
    )


def test_campaign072_raw_minimum_is_ranked_after_combination() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["A", "B", "C", "D"],
            "provider": ["tushare"] * 4,
            "profit_yoy": [100.0, 20.0, 30.0, np.nan],
            "revenue_yoy": [10.0, 40.0, 30.0, 50.0],
        }
    )
    ranked = c72.rank_year_frame(frame)
    values = ranked[c72.FACTOR_NAME].to_numpy(dtype=float)
    np.testing.assert_allclose(values[:3], np.array([1.0 / 3.0, 2.0 / 3.0, 1.0]))
    assert np.isnan(values[3])
    assert ranked[f"{c72.FACTOR_NAME}_eligible"].tolist() == [True, True, True, False]
    assert set(ranked["provider"]) == {"quarterly_quality_pit"}


def test_campaign072_pre_value_boundaries_remain_closed() -> None:
    spec = c72.load_protocol()
    boundary = spec["research_boundary"]
    assert boundary["candidate_or_comparison_values_read_before_this_freeze"] is False
    assert boundary["historical_daily_price_fields_read"] == []
    assert boundary["historical_forward_return_fields_read"] is False
    assert boundary["provider_request_issued"] is False
    assert boundary["candidate49_ledgers_changed"] is False
