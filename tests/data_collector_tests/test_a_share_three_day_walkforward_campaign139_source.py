from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign139_source as source


def _calendar() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(
        pd.to_datetime(
            [
                "2020-04-20",
                "2020-04-21",
                "2020-04-22",
                "2020-04-23",
                "2020-04-24",
                "2020-04-27",
            ]
        )
    )


def test_latest_strictly_prior_same_period_forecast_is_used() -> None:
    realized = pd.DataFrame(
        {
            "instrument": ["sh600000", "sz000001"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "announcement_date": ["2020-04-20", "2020-04-21"],
            "profit_yoy": [12.0, -5.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "instrument": ["sh600000", "sh600000", "sh600000", "sz000001"],
            "report_date": ["2020-03-31"] * 4,
            "announcement_date": [
                "2020-03-01",
                "2020-04-10",
                "2020-04-21",
                "2020-04-01",
            ],
            "forecast_profit_yoy": [5.0, 10.0, 99.0, -8.0],
        }
    )

    events, quality = source.build_event_frame(forecasts, realized, _calendar())

    assert events["instrument"].tolist() == ["sh600000", "sz000001"]
    assert events["forecast_profit_yoy"].tolist() == [10.0, -8.0]
    assert events["raw_surprise"].tolist() == [2.0, 3.0]
    assert events["effective_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-04-21",
        "2020-04-22",
    ]
    assert events["event_expiry_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-04-24",
        "2020-04-25",
    ]
    assert quality["published_events"] == 2


def test_same_day_or_later_forecast_is_not_eligible() -> None:
    realized = pd.DataFrame(
        {
            "instrument": ["sh600000"],
            "report_date": ["2020-03-31"],
            "announcement_date": ["2020-04-20"],
            "profit_yoy": [12.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "instrument": ["sh600000", "sh600000"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "announcement_date": ["2020-04-20", "2020-04-21"],
            "forecast_profit_yoy": [10.0, 11.0],
        }
    )

    events, quality = source.build_event_frame(forecasts, realized, _calendar())

    assert events.empty
    assert quality["finite_strictly_prior_pairs"] == 0


def test_conflicting_realized_key_fails_closed() -> None:
    realized = pd.DataFrame(
        {
            "instrument": ["sh600000", "sh600000"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "announcement_date": ["2020-04-20", "2020-04-21"],
            "profit_yoy": [12.0, 13.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "instrument": ["sh600000"],
            "report_date": ["2020-03-31"],
            "announcement_date": ["2020-04-01"],
            "forecast_profit_yoy": [10.0],
        }
    )

    with pytest.raises(source.Campaign139SourceError, match="realized event key"):
        source.build_event_frame(forecasts, realized, _calendar())


def test_conflicting_forecast_key_fails_closed() -> None:
    realized = pd.DataFrame(
        {
            "instrument": ["sh600000"],
            "report_date": ["2020-03-31"],
            "announcement_date": ["2020-04-20"],
            "profit_yoy": [12.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "instrument": ["sh600000", "sh600000"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "announcement_date": ["2020-04-01", "2020-04-01"],
            "forecast_profit_yoy": [10.0, 11.0],
        }
    )

    with pytest.raises(source.Campaign139SourceError, match="forecast event key"):
        source.build_event_frame(forecasts, realized, _calendar())


def test_source_metadata_is_bound_without_values() -> None:
    metadata = source.validate_source_metadata()

    assert metadata["forecast_rows"] == 42206
    assert metadata["quality_rows"] == 143776
    assert metadata["forecast_row_groups"] == 1
    assert metadata["quality_row_groups"] == 1
    assert metadata["source_values_read"] is False
    assert metadata["provider_request_issued"] is False
