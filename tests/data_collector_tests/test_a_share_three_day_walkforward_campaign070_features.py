from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign070_features as feature


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000", "SH600000", "SZ000001", "SZ000001"],
            "report_date": [
                "2019-03-31",
                "2020-03-31",
                "2021-03-31",
                "2019-03-31",
                "2020-03-31",
            ],
            "announcement_date": [
                "2019-04-30",
                "2020-04-20",
                "2021-05-15",
                "2019-04-20",
                "2020-04-20",
            ],
        }
    ).loc[:, feature.EVENT_FIELDS]


def test_protocol_and_complete_numeric_order_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons(spec)
    assert len(comparisons) == 100
    assert comparisons[-2:] == [
        {
            "name": "quarterly_profit_revenue_acceleration_rank_gap_2r",
            "score_direction": "higher",
        },
        {
            "name": "quarterly_profit_growth_roe_transition_gap_2r",
            "score_direction": "higher",
        },
    ]
    assert (
        feature._runtime["_comparison_order_digest"](comparisons)
        == feature.COMPARISON_ORDER_SHA256
    )
    unique = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert unique["complete_definition_count"] == 101
    assert unique["all_100_numeric_comparators_must_pass"] is True


def test_exact_same_quarter_yoy_delay_improvement() -> None:
    result = feature.compute_improvement_events(_events())
    a = result.loc[result["instrument"].eq("SH600000")].reset_index(drop=True)
    b = result.loc[result["instrument"].eq("SZ000001")].reset_index(drop=True)
    assert np.isnan(a.loc[0, "improvement_days"])
    assert a.loc[1, "improvement_days"] == 10.0
    assert a.loc[2, "improvement_days"] == -25.0
    assert np.isnan(b.loc[0, "improvement_days"])
    assert b.loc[1, "improvement_days"] == 0.0


def test_strict_next_session_activation_and_cross_section_rank() -> None:
    calendar = pd.DatetimeIndex(
        pd.to_datetime(["2020-04-20", "2020-04-21", "2020-04-22"])
    )
    by_symbol = feature.prepare_events(_events(), calendar)
    pieces = []
    for symbol in ("SH600000", "SZ000001"):
        identity = pd.DataFrame(
            {
                "trade_date": calendar,
                "symbol": symbol,
                "provider": "tushare",
            }
        )
        pieces.append(
            feature.attach_states(
                identity,
                symbol=symbol,
                calendar=calendar,
                events_by_symbol=by_symbol,
            )
        )
    attached = pd.concat(pieces, ignore_index=True)
    on_announcement = attached.loc[attached["trade_date"].eq(pd.Timestamp("2020-04-20"))]
    assert on_announcement["improvement_days"].isna().all()
    ranked = feature.rank_improvement_year_frame(attached)
    next_day = ranked.loc[ranked["trade_date"].eq(pd.Timestamp("2020-04-21"))]
    values = dict(zip(next_day["symbol"], next_day[feature.FACTOR_NAME], strict=True))
    assert values == {"SH600000": 1.0, "SZ000001": 0.5}


def test_invalid_quarter_end_fails_closed() -> None:
    events = _events()
    events.loc[0, "report_date"] = "2019-04-01"
    try:
        feature.compute_improvement_events(events)
    except feature.Campaign070FeatureError as exc:
        assert "Q-DEC" in str(exc)
    else:
        raise AssertionError("invalid fiscal quarter escaped")


def test_status_is_no_value_and_no_return() -> None:
    payload = feature.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
    json.dumps(payload, sort_keys=True)
