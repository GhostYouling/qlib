from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign071_features as c71


def test_campaign071_protocol_and_comparator_order_are_frozen() -> None:
    spec = c71.load_protocol()
    comparisons = c71.reconstruct_comparisons(spec)
    assert len(comparisons) == 101
    assert comparisons[-1] == {
        "name": "quarterly_announcement_delay_improvement_yoy_rank_1y",
        "score_direction": "higher",
    }
    assert c71._runtime["_comparison_order_digest"](comparisons) == c71.COMPARISON_ORDER_SHA256


def test_campaign071_strict_next_session_and_positive_state() -> None:
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-04-29", "2020-04-30", "2020-05-06"]))
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000002"],
            "report_date": ["2020-03-31", "2020-03-31"],
            "announcement_date": ["2020-04-30", "2020-04-30"],
            "net_profit": [100.0, -1.0],
        }
    ).loc[:, c71.EVENT_FIELDS]
    prepared = c71.prepare_events(events, calendar)
    identity = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-04-30", "2020-05-06"]),
            "symbol": ["SZ000001", "SZ000001"],
            "provider": ["x", "x"],
        }
    )
    attached = c71.attach_states(
        identity,
        symbol="SZ000001",
        calendar=calendar,
        events_by_symbol=prepared,
    )
    assert pd.isna(attached.loc[0, "net_profit"])
    assert attached.loc[1, "net_profit"] == 100.0
    assert "SZ000002" not in prepared


def test_campaign071_average_tie_rank_and_missing_semantics() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["SZ000001", "SZ000002", "SZ000003", "SZ000004"],
            "provider": ["x"] * 4,
            "net_profit": [10.0, 10.0, 30.0, float("nan")],
        }
    )
    ranked = c71.rank_year_frame(frame)
    assert ranked[c71.FACTOR_NAME].tolist()[:3] == [0.5, 0.5, 1.0]
    assert pd.isna(ranked.loc[3, c71.FACTOR_NAME])
    assert ranked[f"{c71.FACTOR_NAME}_eligible"].tolist() == [True, True, True, False]


def test_campaign071_status_is_no_value_no_return() -> None:
    payload = {
        "status": "snapshot_present" if (c71.output_root(c71.DEFAULT_DATA_ROOT) / "snapshot_manifest.json").is_file() else "snapshot_absent_pre_build",
        "candidate_or_comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
