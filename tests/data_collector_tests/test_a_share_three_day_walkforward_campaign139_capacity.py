from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign139_capacity as capacity
from scripts import a_share_three_day_walkforward_campaign139_formula as formula


def _calendar() -> pd.DatetimeIndex:
    return pd.date_range("2020-04-20", periods=12, freq="B")


def test_expand_live_events_uses_calendar_and_calendar_day_expiry() -> None:
    events = pd.DataFrame(
        {
            "effective_date": ["2020-04-20", "2020-04-24"],
            "event_expiry_date": ["2020-04-23", "2020-04-27"],
            "instrument": ["sh600000", "sz000001"],
            "provider": ["eastmoney", "eastmoney"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "raw_surprise": [2.0, 3.0],
        }
    )

    expanded = capacity.expand_live_events(events, _calendar())

    first = expanded.loc[expanded["symbol"] == "sh600000", "trade_date"]
    second = expanded.loc[expanded["symbol"] == "sz000001", "trade_date"]
    assert first.dt.strftime("%Y-%m-%d").tolist() == [
        "2020-04-20",
        "2020-04-21",
        "2020-04-22",
        "2020-04-23",
    ]
    assert second.dt.strftime("%Y-%m-%d").tolist() == [
        "2020-04-24",
        "2020-04-27",
    ]


def test_quality_listing_gate_precedes_average_tie_ranking() -> None:
    events = pd.DataFrame(
        {
            "effective_date": ["2020-04-20"] * 3,
            "event_expiry_date": ["2020-04-23"] * 3,
            "instrument": ["sh600000", "sz000001", "sz000002"],
            "provider": ["eastmoney"] * 3,
            "report_date": ["2020-03-31"] * 3,
            "raw_surprise": [1.0, 1.0, 3.0],
        }
    )
    keys = pd.DataFrame(
        {
            "trade_date": ["2020-04-20", "2020-04-20"],
            "symbol": ["sh600000", "sz000002"],
        }
    )

    candidate = capacity.candidate_signal_frame(events, keys, _calendar())

    assert candidate["symbol"].tolist() == ["sh600000", "sz000002"]
    assert candidate[formula.FACTOR_NAME].tolist() == [0.5, 1.0]


def test_capacity_grid_is_fixed_every_three_signal_sessions() -> None:
    calendar = pd.date_range("2020-01-02", periods=12, freq="B")
    rows = []
    for date in calendar:
        for index in range(6):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": f"sh60{index:04d}",
                    "provider": "eastmoney",
                    "raw_surprise": float(index),
                    formula.FACTOR_NAME: (index + 1) / 6,
                }
            )
    candidate = pd.DataFrame(rows)

    metrics = capacity.capacity_metrics(candidate, calendar)

    assert metrics["non_overlapping_grid_dates"] == 3
    assert metrics["potential_complete_cohorts"] == 3
    assert metrics["cohorts_by_year"]["2020"] == 3
    assert metrics["capacity_gate_passed_before_comparator_values"] is False


def test_static_metadata_is_no_value_and_source_bound() -> None:
    metadata = capacity.validate_static_metadata()

    assert metadata["source_rows"] == 37185
    assert metadata["source_values_read"] is False
    assert metadata["candidate_values_read"] is False
    assert metadata["comparator_values_read"] is False
    assert metadata["provider_request_issued"] is False
