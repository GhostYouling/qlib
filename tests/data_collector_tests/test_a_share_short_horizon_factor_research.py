"""Offline tests for short-horizon factor research safeguards."""

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_short_horizon_factor_research.py"
SPEC = importlib.util.spec_from_file_location("a_share_short_horizon_factor_research", SCRIPT_PATH)
RESEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RESEARCH
SPEC.loader.exec_module(RESEARCH)


def test_annual_report_dates_and_symbol_mapping():
    assert RESEARCH.annual_report_dates(2023, 2025) == ["2023-12-31", "2024-12-31", "2025-12-31"]
    assert RESEARCH.quarterly_report_dates(2023, 2024) == [
        "2023-03-31",
        "2023-06-30",
        "2023-09-30",
        "2023-12-31",
        "2024-03-31",
        "2024-06-30",
        "2024-09-30",
        "2024-12-31",
    ]
    assert RESEARCH.qlib_symbol("600000") == "SH600000"
    assert RESEARCH.qlib_symbol("300001") == "SZ300001"
    assert RESEARCH.qlib_symbol("200001") is None


def test_quality_join_waits_until_next_trading_day():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    fundamentals = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "report_date": pd.to_datetime(["2023-12-31"]),
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "roe": [8.0],
            "net_profit": [1.0],
            "revenue_yoy": [5.0],
            "profit_yoy": [10.0],
        }
    )
    joined = RESEARCH.attach_quality_asof(market, fundamentals)
    assert not joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30"), "quality_eligible"].item()
    effective = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert effective["quality_eligible"]
    assert effective["quality_effective_date"] == pd.Timestamp("2024-05-06")


def test_fundamental_acceleration_becomes_available_only_with_newer_announcement():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    fundamentals = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000001"],
            "report_date": pd.to_datetime(["2022-12-31", "2023-12-31"]),
            "announcement_date": pd.to_datetime(["2023-04-28", "2024-04-30"]),
            "roe": [8.0, 10.0],
            "net_profit": [1.0, 2.0],
            "revenue_yoy": [5.0, 12.0],
            "profit_yoy": [10.0, 25.0],
        }
    )
    joined = RESEARCH.attach_quality_asof(market, fundamentals)
    before = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    after = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert pd.isna(before["profit_yoy_acceleration"])
    assert after["roe_change"] == pytest.approx(2.0)
    assert after["revenue_yoy_acceleration"] == pytest.approx(7.0)
    assert after["profit_yoy_acceleration"] == pytest.approx(15.0)


def test_quarterly_acceleration_compares_only_the_same_fiscal_quarter():
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 5,
            "report_date": pd.to_datetime(
                ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"]
            ),
            "announcement_date": pd.to_datetime(
                ["2023-04-20", "2023-08-20", "2023-10-20", "2024-03-20", "2024-04-20"]
            ),
            "roe": [2.0, 4.0, 6.0, 8.0, 3.0],
            "net_profit": [1.0, 2.0, 3.0, 4.0, 1.5],
            "revenue_yoy": [10.0, 20.0, 30.0, 40.0, 16.0],
            "profit_yoy": [5.0, 15.0, 25.0, 35.0, 12.0],
        }
    )
    accelerated = RESEARCH.attach_fundamental_accelerations(events)
    latest = accelerated.iloc[-1]
    assert latest["roe_change"] == pytest.approx(1.0)
    assert latest["revenue_yoy_acceleration"] == pytest.approx(6.0)
    assert latest["profit_yoy_acceleration"] == pytest.approx(7.0)


def test_quarterly_snapshot_merge_is_atomic_and_keeps_the_earliest_announcement(tmp_path):
    columns = {
        "instrument": ["SZ000001"],
        "report_date": pd.to_datetime(["2024-03-31"]),
        "roe": [8.0],
        "net_profit": [1.0],
        "revenue_yoy": [10.0],
        "profit_yoy": [12.0],
    }
    first = pd.DataFrame({**columns, "announcement_date": pd.to_datetime(["2024-04-22"])})
    second = pd.DataFrame({**columns, "announcement_date": pd.to_datetime(["2024-04-20"])})
    first_path = tmp_path / "quarterly_first.parquet"
    second_path = tmp_path / "quarterly_second.parquet"
    first.to_parquet(first_path, index=False)
    second.to_parquet(second_path, index=False)
    output = tmp_path / "quarterly_merged.parquet"
    manifest = tmp_path / "quarterly_manifest.json"
    result = RESEARCH.merge_quarterly_fundamentals([first_path, second_path], output, manifest)
    merged = pd.read_parquet(output)
    assert result["report_frequency"] == "quarterly"
    assert result["report_dates"] == ["2024-03-31"]
    assert len(merged) == 1
    assert merged.iloc[0]["announcement_date"] == pd.Timestamp("2024-04-20")


def test_performance_forecast_normalization_keeps_later_notices_as_separate_events():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-20",
            "PREDICT_FINANCE_CODE": "004",
            "ADD_AMP_LOWER": 10.0,
            "ADD_AMP_UPPER": 30.0,
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-25",
            "PREDICT_FINANCE_CODE": "004",
            "ADD_AMP_LOWER": 20.0,
            "ADD_AMP_UPPER": 40.0,
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-25",
            "PREDICT_FINANCE_CODE": "004",
            "ADD_AMP_LOWER": 20.0,
            "ADD_AMP_UPPER": 40.0,
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-25",
            "PREDICT_FINANCE_CODE": "006",
            "ADD_AMP_LOWER": 200.0,
            "ADD_AMP_UPPER": 400.0,
        },
    ]
    normalized = RESEARCH.normalize_performance_forecast_rows(rows, "2024-03-31")
    assert normalized["instrument"].tolist() == ["SZ000001", "SZ000001"]
    assert normalized["forecast_profit_yoy"].tolist() == pytest.approx([20.0, 30.0])
    assert normalized["forecast_profit_yoy_width"].tolist() == pytest.approx([20.0, 20.0])
    assert normalized["forecast_turnaround"].tolist() == pytest.approx([0.0, 0.0])


def test_performance_forecast_normalization_keeps_a_turnaround_without_a_numeric_yoy_range():
    normalized = RESEARCH.normalize_performance_forecast_rows(
        [
            {
                "SECURITY_CODE": "000001",
                "NOTICE_DATE": "2024-04-20",
                "PREDICT_FINANCE_CODE": "004",
                "PREDICT_TYPE": "扭亏",
                "ADD_AMP_LOWER": None,
                "ADD_AMP_UPPER": None,
            }
        ],
        "2024-03-31",
    )
    assert len(normalized) == 1
    assert normalized["forecast_type"].item() == "扭亏"
    assert normalized["forecast_turnaround"].item() == pytest.approx(1.0)
    assert pd.isna(normalized["forecast_profit_yoy"].item())


def test_performance_forecast_join_waits_for_next_session_and_expires_old_events():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-06-10"]),
        }
    )
    forecasts = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "report_date": pd.to_datetime(["2024-03-31"]),
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "forecast_type": ["预增"],
            "forecast_turnaround": [0.0],
            "forecast_profit_yoy": [20.0],
            "forecast_profit_yoy_width": [10.0],
        }
    )
    joined = RESEARCH.attach_performance_forecasts_asof(market, forecasts, max_age_days=30)
    before = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    expired = joined.loc[joined["datetime"] == pd.Timestamp("2024-06-10")].iloc[0]
    assert not before["forecast_available"]
    assert effective["forecast_available"]
    assert effective["forecast_effective_date"] == pd.Timestamp("2024-05-06")
    assert not expired["forecast_available"]


def test_billboard_normalization_aggregates_same_day_reasons_without_future_return_fields():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "TRADE_DATE": "2024-04-30",
            "EXPLANATION": "日涨幅偏离值达到7%的前5只证券",
            "BILLBOARD_NET_AMT": 100.0,
            "BILLBOARD_DEAL_AMT": 200.0,
            "FREE_MARKET_CAP": 1_000.0,
            "D1_CLOSE_ADJCHRATE": 99.0,
        },
        {
            "SECURITY_CODE": "000001",
            "TRADE_DATE": "2024-04-30",
            "EXPLANATION": "日换手率达到20%的前5只证券",
            "BILLBOARD_NET_AMT": -50.0,
            "BILLBOARD_DEAL_AMT": 100.0,
            "FREE_MARKET_CAP": 1_000.0,
            "D1_CLOSE_ADJCHRATE": -99.0,
        },
    ]
    normalized = RESEARCH.normalize_billboard_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.BILLBOARD_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["billboard_net_flow_to_float"] == pytest.approx(0.025)
    assert row["billboard_net_flow_to_deal"] == pytest.approx(0.0)
    assert row["billboard_deal_to_float"] == pytest.approx(0.15)
    assert row["billboard_reason_count"] == pytest.approx(2.0)
    assert "D1_CLOSE_ADJCHRATE" not in normalized.columns


def test_billboard_join_uses_same_close_for_next_open_and_expires_old_events():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "trade_date": pd.to_datetime(["2024-04-30"]),
            "billboard_net_flow_to_float": [0.01],
            "billboard_net_flow_to_deal": [0.20],
            "billboard_deal_to_float": [0.05],
            "billboard_reason_count": [2.0],
        }
    )
    joined = RESEARCH.attach_billboard_events_asof(market, events, max_age_days=3)
    event_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    after_holiday = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert event_day["billboard_available"]
    assert event_day["billboard_effective_date"] == pd.Timestamp("2024-04-30")
    assert event_day["billboard_net_flow_to_deal"] == pytest.approx(0.20)
    assert not after_holiday["billboard_available"]


def test_major_holder_normalization_uses_notice_date_and_explicit_direction_only():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "END_DATE": "2024-01-01",
            "DIRECTION": "增持",
            "CHANGE_NUM_SYMBOL": 100.0,
            "CHANGE_FREE_RATIO": 0.50,
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "END_DATE": "2024-04-28",
            "DIRECTION": "减持",
            "CHANGE_NUM_SYMBOL": -20.0,
            "CHANGE_FREE_RATIO": 0.20,
        },
    ]
    normalized = RESEARCH.normalize_major_holder_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.MAJOR_HOLDER_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["announcement_date"] == pd.Timestamp("2024-04-30")
    assert row["major_holder_net_change_free_ratio"] == pytest.approx(0.30)
    assert row["major_holder_increase_free_ratio"] == pytest.approx(0.50)
    assert row["major_holder_decrease_free_ratio"] == pytest.approx(0.20)
    assert row["major_holder_event_count"] == pytest.approx(2.0)
    assert "END_DATE" not in normalized.columns


def test_major_holder_join_waits_for_next_session_and_expires_old_notices():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "major_holder_net_change_free_ratio": [0.50],
            "major_holder_increase_free_ratio": [0.50],
            "major_holder_decrease_free_ratio": [0.0],
            "major_holder_event_count": [1.0],
        }
    )
    joined = RESEARCH.attach_major_holder_events_asof(market, events, max_age_days=0)
    announcement_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    expired = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-07")].iloc[0]
    assert not announcement_day["major_holder_available"]
    assert effective["major_holder_available"]
    assert effective["major_holder_effective_date"] == pd.Timestamp("2024-05-06")
    assert not expired["major_holder_available"]


def test_block_trade_normalization_weights_premium_and_excludes_forward_returns():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "TRADE_DATE": "2024-04-30",
            "PREMIUM_RATIO": 0.10,
            "DEAL_AMT": 100.0,
            "TURNOVER_RATE": 0.10,
            "CHANGE_RATE_1DAYS": 99.0,
        },
        {
            "SECURITY_CODE": "000001",
            "TRADE_DATE": "2024-04-30",
            "PREMIUM_RATIO": -0.10,
            "DEAL_AMT": 300.0,
            "TURNOVER_RATE": 0.20,
            "CHANGE_RATE_1DAYS": -99.0,
        },
    ]
    normalized = RESEARCH.normalize_block_trade_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.BLOCK_TRADE_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["block_trade_premium_ratio"] == pytest.approx(-0.05)
    assert row["block_trade_turnover_rate"] == pytest.approx(0.30)
    assert row["block_trade_event_count"] == pytest.approx(2.0)
    assert "CHANGE_RATE_1DAYS" not in normalized.columns


def test_block_trade_join_uses_same_close_and_expires_after_calendar_window():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "trade_date": pd.to_datetime(["2024-04-30"]),
            "block_trade_premium_ratio": [-0.05],
            "block_trade_turnover_rate": [0.30],
            "block_trade_event_count": [2.0],
        }
    )
    joined = RESEARCH.attach_block_trade_events_asof(market, events, max_age_days=3)
    event_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    after_holiday = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert event_day["block_trade_available"]
    assert event_day["block_trade_effective_date"] == pd.Timestamp("2024-04-30")
    assert event_day["block_trade_premium_ratio"] == pytest.approx(-0.05)
    assert not after_holiday["block_trade_available"]


def test_margin_financing_normalization_uses_only_same_close_non_outcome_fields():
    rows = [
        {
            "SCODE": "000001",
            "DATE": "2024-04-30",
            "RZJME": 20.0,
            "RZMRE": 100.0,
            "RZYE": 500.0,
            "SZ": 1_000.0,
            "FIN_BALANCE_GR": 2.5,
            "RCHANGE3DCP": 99.0,
            "RCHANGE5DCP": 88.0,
        },
        {
            "SCODE": "159001",  # ETF: excluded by the A-share symbol mapper.
            "DATE": "2024-04-30",
            "RZJME": 100.0,
            "RZMRE": 200.0,
            "RZYE": 500.0,
            "SZ": 1_000.0,
            "FIN_BALANCE_GR": 5.0,
            "RCHANGE10DCP": -99.0,
        },
    ]
    normalized = RESEARCH.normalize_margin_financing_top_flow_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.MARGIN_FINANCING_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["margin_net_buy_to_market_cap"] == pytest.approx(0.02)
    assert row["margin_buy_to_market_cap"] == pytest.approx(0.10)
    assert row["margin_balance_to_market_cap"] == pytest.approx(0.50)
    assert row["margin_financing_balance_growth"] == pytest.approx(2.5)
    assert "RCHANGE3DCP" not in normalized.columns


def test_margin_financing_join_uses_same_close_and_default_zero_age_window():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "trade_date": pd.to_datetime(["2024-04-30"]),
            "margin_net_buy_to_market_cap": [0.02],
            "margin_buy_to_market_cap": [0.10],
            "margin_balance_to_market_cap": [0.50],
            "margin_financing_balance_growth": [2.5],
        }
    )
    joined = RESEARCH.attach_margin_financing_events_asof(market, events)
    event_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    after_holiday = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert event_day["margin_financing_available"]
    assert event_day["margin_financing_effective_date"] == pd.Timestamp("2024-04-30")
    assert event_day["margin_net_buy_to_market_cap"] == pytest.approx(0.02)
    assert not after_holiday["margin_financing_available"]


def test_margin_financing_incremental_merge_replaces_only_refetched_stock_days():
    existing = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000002"],
            "trade_date": pd.to_datetime(["2024-04-29", "2024-04-30"]),
            "margin_net_buy_to_market_cap": [0.01, 0.02],
            "margin_buy_to_market_cap": [0.03, 0.04],
            "margin_balance_to_market_cap": [0.05, 0.06],
            "margin_financing_balance_growth": [1.0, 2.0],
        }
    )
    fetched = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000003"],
            "trade_date": pd.to_datetime(["2024-04-29", "2024-04-30"]),
            "margin_net_buy_to_market_cap": [0.11, 0.12],
            "margin_buy_to_market_cap": [0.13, 0.14],
            "margin_balance_to_market_cap": [0.15, 0.16],
            "margin_financing_balance_growth": [11.0, 12.0],
        }
    )
    merged = RESEARCH.merge_margin_financing_event_frames(existing, fetched)
    assert len(merged) == 3
    assert merged.loc[
        (merged["instrument"] == "SZ000001") & (merged["trade_date"] == pd.Timestamp("2024-04-29")),
        "margin_net_buy_to_market_cap",
    ].item() == pytest.approx(0.11)
    assert "SZ000002" in set(merged["instrument"])


def test_institutional_survey_normalization_uses_notice_date_and_deduplicates_participants():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "RECEIVE_START_DATE": "2024-04-29",
            "RECEIVE_END_DATE": "2024-04-29",
            "SUM": 5,
            "RECEIVE_OBJECT": "not stored",
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "RECEIVE_START_DATE": "2024-04-29",
            "RECEIVE_END_DATE": "2024-04-29",
            "SUM": 5,
            "RECEIVE_OBJECT": "also not stored",
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "RECEIVE_START_DATE": "2024-04-30",
            "RECEIVE_END_DATE": None,
            "SUM": 2,
        },
        {
            "SECURITY_CODE": "159001",  # ETF: excluded by the A-share symbol mapper.
            "NOTICE_DATE": "2024-04-30",
            "RECEIVE_START_DATE": "2024-04-30",
            "RECEIVE_END_DATE": "2024-04-30",
            "SUM": 99,
        },
    ]
    normalized = RESEARCH.normalize_institutional_survey_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.INSTITUTIONAL_SURVEY_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["announcement_date"] == pd.Timestamp("2024-04-30")
    assert row["institutional_survey_org_count"] == pytest.approx(7.0)
    assert row["institutional_survey_event_count"] == pytest.approx(2.0)
    assert "RECEIVE_OBJECT" not in normalized.columns


def test_institutional_survey_join_waits_until_strictly_after_notice_date():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "institutional_survey_org_count": [7.0],
            "institutional_survey_event_count": [2.0],
        }
    )
    joined = RESEARCH.attach_institutional_survey_events_asof(market, events, max_age_days=3)
    notice_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert not notice_day["institutional_survey_available"]
    assert effective_day["institutional_survey_available"]
    assert effective_day["institutional_survey_effective_date"] == pd.Timestamp("2024-05-06")
    assert effective_day["institutional_survey_org_count"] == pytest.approx(7.0)


def test_repurchase_plan_normalization_excludes_later_implementation_fields():
    rows = [
        {
            "DIM_SCODE": "000001",
            "DIM_DATE": "2024-04-30",
            "ZSZSX": 1.25,
            "JESX": 100_000_000.0,
            "UPDATEDATE": "2025-01-01",
            "REPURPROGRESS": "006",
            "REPURAMOUNT": 90_000_000.0,
        },
        {"DIM_SCODE": "159001", "DIM_DATE": "2024-04-30", "ZSZSX": 9.0, "JESX": 1.0},
    ]
    normalized = RESEARCH.normalize_repurchase_plan_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.REPURCHASE_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["repurchase_planned_share_ratio"] == pytest.approx(1.25)
    assert row["repurchase_planned_amount"] == pytest.approx(100_000_000.0)
    assert "REPURAMOUNT" not in normalized.columns


def test_repurchase_plan_join_waits_until_strictly_after_announcement_date():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "repurchase_planned_share_ratio": [1.25],
            "repurchase_planned_amount": [100_000_000.0],
        }
    )
    joined = RESEARCH.attach_repurchase_plan_events_asof(market, events, max_age_days=3)
    notice_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert not notice_day["repurchase_available"]
    assert effective_day["repurchase_available"]
    assert effective_day["repurchase_effective_date"] == pd.Timestamp("2024-05-06")
    assert effective_day["repurchase_planned_share_ratio"] == pytest.approx(1.25)


def test_holder_count_normalization_uses_notice_date_and_excludes_price_fields():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "END_DATE": "2024-03-31",
            "HOLD_NOTICE_DATE": "2024-04-30",
            "HOLDER_NUM_CHANGE": -100.0,
            "HOLDER_NUM_RATIO": -5.0,
            "INTERVAL_CHRATE": 99.0,
            "AVG_MARKET_CAP": 123.0,
        },
        {"SECURITY_CODE": "159001", "HOLD_NOTICE_DATE": "2024-04-30", "HOLDER_NUM_CHANGE": 9.0},
    ]
    normalized = RESEARCH.normalize_holder_count_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.HOLDER_COUNT_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["announcement_date"] == pd.Timestamp("2024-04-30")
    assert row["holder_count_change_ratio"] == pytest.approx(-5.0)
    assert row["holder_count_change_absolute"] == pytest.approx(-100.0)
    assert "INTERVAL_CHRATE" not in normalized.columns


def test_holder_count_join_waits_until_strictly_after_notice_date():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "holder_count_change_ratio": [-5.0],
            "holder_count_change_absolute": [-100.0],
        }
    )
    joined = RESEARCH.attach_holder_count_events_asof(market, events, max_age_days=3)
    notice_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert not notice_day["holder_count_available"]
    assert effective_day["holder_count_available"]
    assert effective_day["holder_count_effective_date"] == pd.Timestamp("2024-05-06")
    assert effective_day["holder_count_change_ratio"] == pytest.approx(-5.0)


def test_pledge_normalization_uses_notice_date_and_excludes_current_state_fields():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "PF_NUM": 1_000_000.0,
            "PF_TSR": 0.50,
            "CLOSE_PRICE": 99.0,
            "WARNING_LINE": 1.0,
            "UNFREEZE_STATE": "已解押",
        },
        {
            "SECURITY_CODE": "000001",
            "NOTICE_DATE": "2024-04-30",
            "PF_NUM": 2_000_000.0,
            "PF_TSR": 0.75,
            "TRADE_DATE": "2026-07-13",
        },
        {"SECURITY_CODE": "159001", "NOTICE_DATE": "2024-04-30", "PF_NUM": 9.0},
    ]
    normalized = RESEARCH.normalize_pledge_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.PLEDGE_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["announcement_date"] == pd.Timestamp("2024-04-30")
    assert row["pledge_share_count"] == pytest.approx(3_000_000.0)
    assert row["pledge_total_share_ratio"] == pytest.approx(1.25)
    assert row["pledge_event_count"] == pytest.approx(2.0)
    assert "CLOSE_PRICE" not in normalized.columns


def test_pledge_join_waits_until_strictly_after_notice_date():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "pledge_share_count": [3_000_000.0],
            "pledge_total_share_ratio": [1.25],
            "pledge_event_count": [2.0],
        }
    )
    joined = RESEARCH.attach_pledge_events_asof(market, events, max_age_days=3)
    notice_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert not notice_day["pledge_available"]
    assert effective_day["pledge_available"]
    assert effective_day["pledge_effective_date"] == pd.Timestamp("2024-05-06")
    assert effective_day["pledge_total_share_ratio"] == pytest.approx(1.25)


def test_dividend_plan_normalization_uses_plan_notice_and_excludes_later_fields():
    rows = [
        {
            "SECURITY_CODE": "000001",
            "PLAN_NOTICE_DATE": "2024-04-30",
            "PRETAX_BONUS_RMB": 1.20,
            "BONUS_IT_RATIO": 0.50,
            "ASSIGN_PROGRESS": "实施分配",
            "NOTICE_DATE": "2024-06-01",
            "DIVIDENT_RATIO": 0.99,
            "D10_CLOSE_ADJCHRATE": 88.0,
        },
        {
            "SECURITY_CODE": "000001",
            "PLAN_NOTICE_DATE": "2024-04-30",
            "PRETAX_BONUS_RMB": 0.80,
            "BONUS_IT_RATIO": 0.25,
            "EX_DIVIDEND_DATE": "2024-06-30",
        },
        {"SECURITY_CODE": "159001", "PLAN_NOTICE_DATE": "2024-04-30", "PRETAX_BONUS_RMB": 9.0},
    ]
    normalized = RESEARCH.normalize_dividend_plan_rows(rows)
    assert normalized.columns.tolist() == list(RESEARCH.DIVIDEND_PLAN_EVENT_COLUMNS)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["instrument"] == "SZ000001"
    assert row["announcement_date"] == pd.Timestamp("2024-04-30")
    assert row["dividend_cash_per_ten"] == pytest.approx(2.0)
    assert row["dividend_share_ratio"] == pytest.approx(0.75)
    assert row["dividend_plan_event_count"] == pytest.approx(2.0)
    assert "D10_CLOSE_ADJCHRATE" not in normalized.columns


def test_dividend_plan_join_waits_until_strictly_after_plan_notice_date():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "dividend_cash_per_ten": [2.0],
            "dividend_share_ratio": [0.75],
            "dividend_plan_event_count": [2.0],
        }
    )
    joined = RESEARCH.attach_dividend_plan_events_asof(market, events, max_age_days=3)
    notice_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30")].iloc[0]
    effective_day = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert not notice_day["dividend_plan_available"]
    assert effective_day["dividend_plan_available"]
    assert effective_day["dividend_plan_effective_date"] == pd.Timestamp("2024-05-06")
    assert effective_day["dividend_cash_per_ten"] == pytest.approx(2.0)


def test_billboard_holdout_factor_reverses_only_the_ranked_event_intensity():
    ranked = pd.DataFrame({"billboard_deal_to_float": [0.10, 0.80, float("nan")]})
    result = RESEARCH.add_billboard_holdout_factor(ranked)
    assert result[RESEARCH.BILLBOARD_HOLDOUT_FACTOR].tolist()[:2] == pytest.approx([0.90, 0.20])
    assert pd.isna(result[RESEARCH.BILLBOARD_HOLDOUT_FACTOR].iloc[2])
    with pytest.raises(ValueError, match="requires billboard_deal_to_float"):
        RESEARCH.add_billboard_holdout_factor(pd.DataFrame({"other": [1.0]}))


@pytest.mark.filterwarnings("error::pandas.errors.PerformanceWarning")
def test_rank_factor_frame_excludes_expired_event_values():
    raw_columns = [
        "momentum_1",
        "momentum_2",
        "momentum_3",
        "momentum_5",
        "up_day_ratio_5",
        "momentum_10",
        "momentum_20",
        "momentum_60",
        "trend_ma_5",
        "trend_ma_20",
        "trend_ma_60",
        "volume_surge_1",
        "volume_surge",
        "volume_surge_3",
        "turnover_surge",
        "turnover_surge_3",
        "turnover_surge_1",
        "liquidity_5",
        "free_float_cap_proxy",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "amplitude_1",
        "amplitude_5",
        "gap_1",
        "near_high_10",
        "near_high_20",
        "intraday_strength",
        "close_to_high",
        "close_above_vwap_1",
        "signed_efficiency_ratio_10",
        "return_turnover_correlation_10",
        "signed_volume_pressure_5",
        "roe",
        "revenue_yoy",
        "profit_yoy",
        "quality_age_days",
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
    ]
    frame = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000002"],
            "datetime": pd.to_datetime(["2024-04-30", "2024-04-30"]),
            "quality_eligible": [True, True],
            **{column: [1.0, 2.0] for column in raw_columns},
            "forecast_profit_yoy": [100.0, 20.0],
            "forecast_age_days": [31.0, 1.0],
            "forecast_available": [False, True],
            "billboard_net_flow_to_deal": [0.50, 0.10],
            "billboard_age_days": [4.0, 0.0],
            "billboard_available": [False, True],
            "major_holder_net_change_free_ratio": [0.50, 0.10],
            "major_holder_age_days": [4.0, 0.0],
            "major_holder_available": [False, True],
            "block_trade_premium_ratio": [0.50, 0.10],
            "block_trade_age_days": [4.0, 0.0],
            "block_trade_available": [False, True],
            "margin_net_buy_to_market_cap": [0.50, 0.10],
            "margin_financing_age_days": [1.0, 0.0],
            "margin_financing_available": [False, True],
            "institutional_survey_org_count": [50.0, 10.0],
            "institutional_survey_age_days": [4.0, 0.0],
            "institutional_survey_available": [False, True],
        }
    )
    ranked = RESEARCH.rank_factor_frame(frame)
    expired = ranked.loc[ranked["instrument"] == "SZ000001"].iloc[0]
    active = ranked.loc[ranked["instrument"] == "SZ000002"].iloc[0]
    assert pd.isna(expired["rank_forecast_profit_yoy"])
    assert pd.isna(expired["rank_billboard_net_flow_to_deal"])
    assert pd.isna(expired["rank_major_holder_net_change_free_ratio"])
    assert pd.isna(expired["rank_block_trade_premium_ratio"])
    assert pd.isna(expired["rank_margin_net_buy_to_market_cap"])
    assert pd.isna(expired["rank_institutional_survey_org_count"])
    assert active["rank_forecast_profit_yoy"] == pytest.approx(1.0)
    assert active["rank_billboard_net_flow_to_deal"] == pytest.approx(1.0)
    assert active["rank_major_holder_net_change_free_ratio"] == pytest.approx(1.0)
    assert active["rank_block_trade_premium_ratio"] == pytest.approx(1.0)
    assert active["rank_margin_net_buy_to_market_cap"] == pytest.approx(1.0)
    assert active["rank_institutional_survey_org_count"] == pytest.approx(1.0)
    assert expired["free_float_cap_small"] == pytest.approx(0.5)
    assert active["free_float_cap_small"] == pytest.approx(0.0)
    assert expired["up_day_consistency_5"] == pytest.approx(0.5)
    assert active["up_day_consistency_5"] == pytest.approx(1.0)
    assert expired["signed_volume_pressure_5"] == pytest.approx(0.5)
    assert active["signed_volume_pressure_5"] == pytest.approx(1.0)
    assert expired["close_above_vwap_1"] == pytest.approx(0.5)
    assert active["close_above_vwap_1"] == pytest.approx(1.0)
    assert expired["signed_efficiency_ratio_10"] == pytest.approx(0.5)
    assert active["signed_efficiency_ratio_10"] == pytest.approx(1.0)
    assert expired["return_turnover_correlation_10"] == pytest.approx(0.5)
    assert active["return_turnover_correlation_10"] == pytest.approx(1.0)


def test_winner_uses_development_only():
    summaries = [
        {"candidate": "development_winner", "development_selection_score": 0.20, "test": {"annualized_return": -0.99}},
        {"candidate": "test_winner", "development_selection_score": 0.10, "test": {"annualized_return": 9.99}},
    ]
    assert RESEARCH.choose_winner(summaries) == "development_winner"


def test_no_development_candidate_is_selected_when_every_policy_score_is_missing():
    summaries = [
        {"candidate": "one", "selection_scores": {"positive_year_stability_mdd20": None}},
        {"candidate": "two", "selection_scores": {"positive_year_stability_mdd20": None}},
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability_mdd20") is None


def test_stability_selection_prefers_the_best_worst_development_year_without_test_metrics():
    summaries = [
        {
            "candidate": "pooled_only",
            "development_selection_score": 0.30,
            "selection_scores": {"positive_year_stability": 0.01},
            "test": {"net_cumulative_return": 9.0},
        },
        {
            "candidate": "stable",
            "development_selection_score": 0.10,
            "selection_scores": {"positive_year_stability": 0.03},
            "test": {"net_cumulative_return": -9.0},
        },
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability") == "stable"


def test_regime_ranking_uses_development_score_only_and_keeps_unqualified_rules_last():
    summaries = [
        (
            "always",
            {
                "selection_scores": {"positive_year_stability_mdd20": 0.01},
                "test": {"net_cumulative_return": -9.0},
            },
        ),
        (
            "breadth_5_above_20",
            {
                "selection_scores": {"positive_year_stability_mdd20": 0.03},
                "test": {"net_cumulative_return": -99.0},
            },
        ),
        (
            "breadth_20_positive",
            {
                "selection_scores": {"positive_year_stability_mdd20": None},
                "test": {"net_cumulative_return": 99.0},
            },
        ),
    ]
    ranked = RESEARCH.rank_regimes_by_development(summaries, "positive_year_stability_mdd20")
    assert [item[0] for item in ranked] == ["breadth_5_above_20", "always", "breadth_20_positive"]


def test_basket_overlap_summary_counts_common_dates_and_pairwise_similarity():
    left = {"2025-01-01": {"A", "B", "C"}, "2025-01-06": {"D", "E", "F"}}
    right = {"2025-01-01": {"A", "B", "G"}, "2025-01-06": {"D", "E", "F"}, "2025-01-09": {"X", "Y", "Z"}}
    metrics = RESEARCH.basket_overlap_metrics(left, right)
    assert metrics["common_signal_dates"] == 2
    assert metrics["mean_jaccard"] == pytest.approx(0.75)
    assert metrics["exact_basket_rate"] == pytest.approx(0.5)
    assert metrics["any_overlap_rate"] == pytest.approx(1.0)


def test_basket_correlation_uses_only_trailing_close_known_returns():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 3,
            "instrument": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
            "close": [100.0, 110.0, 99.0, 108.9, 100.0, 120.0, 96.0, 115.2, 100.0, 90.0, 99.0, 89.1],
        }
    )
    rows = RESEARCH.basket_correlation_rows(scored, {"2025-01-07": {"A", "B", "C"}}, lookback_days=3)
    row = rows.iloc[0]
    assert row["valid_return_days"] == 3
    assert row["mean_pairwise_correlation"] == pytest.approx(-1.0 / 3.0)
    assert row["max_pairwise_correlation"] == pytest.approx(1.0)
    summary = RESEARCH.summarize_basket_correlation(
        rows, pd.DataFrame({"signal_date": dates[-1:], "net_return": [-0.02]}), lookback_days=3
    )
    assert summary["basket_count"] == 1
    assert summary["valid_correlation_basket_count"] == 1
    with pytest.raises(ValueError, match="at least two"):
        RESEARCH.basket_correlation_rows(scored, {"2025-01-07": {"A", "B"}}, lookback_days=1)


def test_diversified_topk_skips_highly_correlated_name_and_requires_a_complete_basket():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 3,
            "instrument": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
            "close": [100.0, 110.0, 99.0, 108.9, 98.01, 100.0, 120.0, 96.0, 115.2, 92.16, 100.0, 90.0, 99.0, 89.1, 98.01],
            "score": [0.9] * 5 + [0.8] * 5 + [0.7] * 5,
        }
    )
    selected, statuses = RESEARCH.select_diversified_topk(
        scored,
        hold_days=1,
        topk=2,
        regime_filter="always",
        max_pairwise_correlation=0.5,
        correlation_lookback=2,
        candidate_pool=3,
    )
    latest_signal = dates[2]
    assert statuses.loc[statuses["datetime"] == latest_signal, "diversification_basket_formed"].item()
    assert set(selected.loc[selected["datetime"] == latest_signal, "instrument"]) == {"A", "C"}
    assert not statuses.loc[statuses["datetime"] == dates[0], "diversification_basket_formed"].item()
    with pytest.raises(ValueError, match="between -1 and 1"):
        RESEARCH.select_diversified_topk(scored, 1, 2, "always", 1.1, 2, 3)


def test_selection_risk_gates_require_close_known_low_volatility_and_low_range_ranks():
    frame = pd.DataFrame(
        {
            "volatility_low_20": [0.10, 0.30, 0.50],
            "amplitude_low": [0.50, 0.30, 0.60],
        }
    )
    assert RESEARCH.apply_selection_risk_gates(frame, 0.20, None).index.tolist() == [1, 2]
    assert RESEARCH.apply_selection_risk_gates(frame, None, 0.40).index.tolist() == [0, 2]
    assert RESEARCH.apply_selection_risk_gates(frame, 0.20, 0.40).index.tolist() == [2]
    with pytest.raises(ValueError, match="between zero and one"):
        RESEARCH.apply_selection_risk_gates(frame, 1.01, None)


def test_selected_basket_trade_details_uses_next_open_and_scheduled_exit_close():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 2,
            "instrument": ["A"] * 4 + ["B"] * 4,
            "open": [10.0, 10.0, 11.0, 12.0, 20.0, 20.0, 19.0, 18.0],
            "close": [10.0, 10.5, 11.0, 12.0, 20.0, 19.5, 19.0, 18.0],
            "score": [0.9] * 4 + [0.8] * 4,
        }
    )
    details = RESEARCH.selected_basket_trade_details(
        scored, {"2025-01-02": {"A", "B"}}, hold_days=2, open_cost=0.0, close_cost=0.0
    )
    assert details["instrument"].tolist() == ["A", "B"]
    assert details["entry_date"].tolist() == [pd.Timestamp("2025-01-03")] * 2
    assert details["exit_date"].tolist() == [pd.Timestamp("2025-01-06")] * 2
    assert details["entry_gap_return"].tolist() == pytest.approx([0.0, 0.0])
    assert details.loc[details["instrument"] == "A", "net_return"].item() == pytest.approx(0.10)
    assert details.loc[details["instrument"] == "B", "net_return"].item() == pytest.approx(-0.05)


def test_entry_gap_cap_holds_cash_for_the_entire_incomplete_topk_cohort():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    rows = []
    for instrument, opening_prices in {
        "A": [10.0, 10.0, 10.0, 10.0],
        "B": [10.0, 10.0, 10.0, 10.0],
        "C": [10.0, 11.0, 10.0, 10.0],
    }.items():
        for date, opening_price in zip(dates, opening_prices):
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": opening_price,
                    "close": 10.0,
                    "score": {"A": 0.9, "B": 0.8, "C": 0.7}[instrument],
                }
            )
    rounds, _ = RESEARCH.evaluate_candidate(
        pd.DataFrame(rows),
        RESEARCH.Candidate("entry_gap_test", "test", {"quality_score": 1.0}),
        hold_days=1,
        topk=3,
        open_cost=0.0,
        close_cost=0.0,
        development_end="2025-12-31",
        max_entry_gap=0.04,
    )
    assert rounds["entry_gap_basket_formed"].tolist() == [False, True]
    assert rounds["holdings"].tolist() == [0, 3]
    assert rounds["net_return"].tolist() == pytest.approx([0.0, 0.0])
    with pytest.raises(ValueError, match="strictly between zero and one"):
        RESEARCH.validate_entry_gap_cap(0.0)


def test_missing_future_quote_remains_as_a_cash_cohort_instead_of_being_dropped():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    rows = []
    for instrument in ("A", "B", "C"):
        for date in dates:
            if instrument == "C" and date == pd.Timestamp("2025-01-03"):
                continue
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": 10.0,
                    "close": 10.0,
                    "score": {"A": 0.9, "B": 0.8, "C": 0.7}[instrument],
                }
            )
    rounds, _ = RESEARCH.evaluate_candidate(
        pd.DataFrame(rows),
        RESEARCH.Candidate("missing_quote_test", "test", {"quality_score": 1.0}),
        hold_days=1,
        topk=3,
        open_cost=0.0,
        close_cost=0.0,
        development_end="2025-12-31",
    )
    assert rounds["market_data_basket_formed"].tolist() == [False]
    assert rounds["holdings"].tolist() == [0]
    assert rounds["net_return"].tolist() == pytest.approx([0.0])


def test_human_report_includes_no_eligible_pressure_scans_without_creating_a_winner():
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        no_eligible_studies=[
            {
                "run_id": "long-history",
                "candidate_library": "v4_freshness",
                "candidate_count": 176,
                "selection_policy": "positive_year_stability_mdd20",
            }
        ],
    )
    assert "未产生合格候选的压力扫描" in report
    assert "long-history" in report
    assert "无合格候选" in report


def test_strict_stability_policy_requires_a_development_drawdown_at_or_above_minus_twenty_percent():
    assert RESEARCH.stability_score_with_drawdown_cap(0.02, -0.20) == pytest.approx(0.02)
    assert RESEARCH.stability_score_with_drawdown_cap(0.02, -0.200001) is None
    assert RESEARCH.stability_score_with_drawdown_cap(None, -0.05) is None
    summaries = [
        {
            "candidate": "too_much_drawdown",
            "selection_scores": {"positive_year_stability_mdd20": None},
            "test": {"net_cumulative_return": 9.0},
        },
        {
            "candidate": "risk_capped",
            "selection_scores": {"positive_year_stability_mdd20": 0.01},
            "test": {"net_cumulative_return": -9.0},
        },
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability_mdd20") == "risk_capped"


def test_walk_forward_fold_selects_only_on_completed_training_cohorts():
    def rounds(training_return: float, test_return: float) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "signal_date": pd.to_datetime(["2019-06-03", "2020-06-01", "2021-06-01", "2020-12-30"]),
                "exit_date": pd.to_datetime(["2019-06-05", "2020-06-03", "2021-06-03", "2021-01-05"]),
                "net_return": [training_return, training_return, test_return, 0.50],
                "gross_return": [training_return, training_return, test_return, 0.50],
                "holdings": [3, 3, 3, 3],
            }
        )

    fold, selected_test_rounds = RESEARCH.walk_forward_fold_result(
        {
            "train_winner": rounds(0.10, -0.10),
            "test_winner_only": rounds(0.05, 0.90),
        },
        train_start=pd.Timestamp("2019-01-01"),
        train_end=pd.Timestamp("2020-12-31"),
        test_start=pd.Timestamp("2021-01-01"),
        test_end=pd.Timestamp("2021-12-31"),
        hold_days=3,
        selection_policy="positive_year_stability_mdd20",
    )
    assert fold["winner_selected_on_training_only"] == "train_winner"
    assert fold["eligible_candidate_count"] == 2
    assert fold["winner_training"]["rounds"] == 2
    assert fold["test"]["net_cumulative_return"] == pytest.approx(-0.10)
    assert selected_test_rounds["signal_date"].tolist() == [pd.Timestamp("2021-06-01")]


def test_positive_year_stability_requires_every_development_year_to_be_positive():
    assert RESEARCH.positive_year_stability_score([0.03, 0.01], -0.08) == pytest.approx(-0.03)
    assert RESEARCH.positive_year_stability_score([0.03, -0.01, 0.08], -0.08) is None
    assert RESEARCH.positive_year_stability_score([0.03], -0.08) is None
    assert RESEARCH.positive_year_stability_score([0.03, 0.01], None) is None


def test_close_loss_cap_uses_the_first_breaching_daily_close_without_reallocating():
    trades = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000002"],
            "entry_date": pd.to_datetime(["2025-01-02", "2025-01-02"]),
            "exit_date": pd.to_datetime(["2025-01-06", "2025-01-06"]),
            "entry_open": [100.0, 100.0],
            "planned_exit_close": [101.0, 99.0],
        }
    )
    quotes = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 3 + ["SZ000002"] * 3,
            "datetime": pd.to_datetime(
                ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-02", "2025-01-03", "2025-01-06"]
            ),
            "close": [98.0, 94.0, 101.0, 96.0, 97.0, 99.0],
        }
    )
    capped = RESEARCH.apply_close_loss_cap(trades, quotes, 0.05)
    first, second = capped.itertuples(index=False)
    assert first.close_loss_cap_triggered
    assert first.actual_exit_date == pd.Timestamp("2025-01-03")
    assert first.actual_exit_close == pytest.approx(94.0)
    assert not second.close_loss_cap_triggered
    assert second.actual_exit_date == pd.Timestamp("2025-01-06")
    assert second.actual_exit_close == pytest.approx(99.0)
    uncapped = RESEARCH.apply_close_loss_cap(trades, quotes, None)
    assert not uncapped["close_loss_cap_triggered"].any()
    with pytest.raises(ValueError, match="strictly between zero and one"):
        RESEARCH.apply_close_loss_cap(trades, quotes, 0.0)


def test_candidate_lookup_rejects_unrecorded_factor_mix():
    assert RESEARCH.candidate_by_name("quality_trend_pullback").weights["momentum_10"] == 0.25
    assert RESEARCH.candidate_by_name("expanded_multi_horizon_q25_profit").weights["quality_profit"] == 0.25
    with pytest.raises(ValueError, match="unknown candidate"):
        RESEARCH.candidate_by_name("made_up_factor_mix")


def test_candidate_library_contains_exactly_one_hundred_predeclared_strategies():
    candidates = RESEARCH.CANDIDATES
    assert len(candidates) == 100
    assert len({candidate.name for candidate in candidates}) == 100
    assert len(RESEARCH.BASELINE_CANDIDATES) == 5
    assert len(RESEARCH.EXPANDED_SIGNAL_BLUEPRINTS) == 19
    assert len(RESEARCH.QUALITY_OVERLAYS) == 5
    assert all(sum(candidate.weights.values()) == pytest.approx(1.0) for candidate in candidates)


def test_v2_microstructure_library_is_versioned_and_keeps_v1_intact():
    v1 = RESEARCH.candidate_library("v1")
    v2 = RESEARCH.candidate_library("v2_microstructure")
    assert len(v1) == 100
    assert len(v2) == 150
    assert tuple(candidate.name for candidate in v2[:100]) == tuple(candidate.name for candidate in v1)
    assert RESEARCH.candidate_by_name("expanded_v2_micro_reversal_1_q05_composite", "v2_microstructure").weights[
        "reversal_1"
    ] == pytest.approx(0.304)
    assert RESEARCH.candidate_library_fingerprint(v1) != RESEARCH.candidate_library_fingerprint(v2)
    with pytest.raises(ValueError, match="unknown candidate_library"):
        RESEARCH.candidate_library("unrecorded")


def test_v3_quality_grid_is_a_nonduplicating_systematic_extension_of_v2():
    v2 = RESEARCH.candidate_library("v2_microstructure")
    v3 = RESEARCH.candidate_library("v3_quality_grid")
    additions = v3[len(v2) :]
    assert len(v3) == 170
    assert len(additions) == 20
    assert tuple(candidate.name for candidate in v3[: len(v2)]) == tuple(candidate.name for candidate in v2)
    assert {candidate.weights.get("quality_revenue") for candidate in additions if "quality_revenue" in candidate.weights} == {
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
    }
    v2_signatures = {tuple(sorted(candidate.weights.items())) for candidate in v2}
    assert all(tuple(sorted(candidate.weights.items())) not in v2_signatures for candidate in additions)
    assert RESEARCH.candidate_by_name("expanded_v3_quiet_long_trend_q10_growth", "v3_quality_grid").weights[
        "trend_ma_60"
    ] == pytest.approx(0.27)


def test_v4_freshness_library_adds_close_known_disclosure_age_weight_variants():
    v3 = RESEARCH.candidate_library("v3_quality_grid")
    v4 = RESEARCH.candidate_library("v4_freshness")
    additions = v4[len(v3) :]
    assert len(v4) == 176
    assert len(additions) == 6
    assert tuple(candidate.name for candidate in v4[: len(v3)]) == tuple(candidate.name for candidate in v3)
    candidate = RESEARCH.candidate_by_name("expanded_v4_quiet_long_trend_q15_revenue_f10", "v4_freshness")
    assert candidate.weights["quality_revenue"] == pytest.approx(0.15)
    assert candidate.weights["quality_freshness"] == pytest.approx(0.10)
    assert candidate.weights["trend_ma_60"] == pytest.approx(0.225)


def test_v5_defensive_library_systematically_adds_low_volatility_and_low_range_variants():
    v4 = RESEARCH.candidate_library("v4_freshness")
    v5 = RESEARCH.candidate_library("v5_defensive")
    additions = v5[len(v4) :]
    assert len(v5) == 206
    assert len(additions) == 30
    assert tuple(candidate.name for candidate in v5[: len(v4)]) == tuple(candidate.name for candidate in v4)
    assert {candidate.name.split("_q", 1)[0] for candidate in additions} == {
        "expanded_v5_defensive_low_volatility",
        "expanded_v5_defensive_low_range",
        "expanded_v5_defensive_dual_risk",
    }
    assert {candidate.weights.get("quality_roe") for candidate in additions if "quality_roe" in candidate.weights} == {
        0.10,
        0.15,
    }
    low_volatility = RESEARCH.candidate_by_name("expanded_v5_defensive_low_volatility_q15_revenue", "v5_defensive")
    dual_risk = RESEARCH.candidate_by_name("expanded_v5_defensive_dual_risk_q10_growth", "v5_defensive")
    assert low_volatility.weights["volatility_low_20"] == pytest.approx(0.17)
    assert dual_risk.weights["volatility_low_20"] == pytest.approx(0.18)
    assert dual_risk.weights["amplitude_low"] == pytest.approx(0.162)


def test_v6_soft_risk_library_adds_close_pullback_and_short_reversal_without_hard_gates():
    v5 = RESEARCH.candidate_library("v5_defensive")
    v6 = RESEARCH.candidate_library("v6_soft_risk")
    additions = v6[len(v5) :]
    assert len(v6) == 246
    assert len(additions) == 40
    assert tuple(candidate.name for candidate in v6[: len(v5)]) == tuple(candidate.name for candidate in v5)
    assert {candidate.name.split("_q", 1)[0] for candidate in additions} == {
        "expanded_v6_soft_close_pullback_defensive",
        "expanded_v6_soft_short_reversal_defensive",
        "expanded_v6_soft_close_pullback_low_volatility",
        "expanded_v6_soft_short_reversal_low_volatility",
    }
    pullback = RESEARCH.candidate_by_name("expanded_v6_soft_close_pullback_defensive_q15_revenue", "v6_soft_risk")
    reversal = RESEARCH.candidate_by_name("expanded_v6_soft_short_reversal_defensive_q10_roe", "v6_soft_risk")
    assert pullback.weights["close_pullback"] == pytest.approx(0.1105)
    assert reversal.weights["reversal_1"] == pytest.approx(0.117)
    assert all(math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9) for candidate in additions)


def test_v7_reversion_ic_library_adds_a_diagnostic_only_quality_gate_mode():
    v6 = RESEARCH.candidate_library("v6_soft_risk")
    v7 = RESEARCH.candidate_library("v7_reversion_ic")
    additions = v7[len(v6) :]
    assert len(v7) == 258
    assert len(additions) == 12
    assert tuple(candidate.name for candidate in v7[: len(v6)]) == tuple(candidate.name for candidate in v6)
    assert {
        candidate.name.replace("_gate_only", "").replace("_q05_growth", "").replace("_q10_composite", "")
        for candidate in additions
    } == {
        "expanded_v7_reversal_dry_gap_pullback",
        "expanded_v7_reversal_dry_gap",
        "expanded_v7_gap_dry_reversal",
        "expanded_v7_quiet_reversal_pullback",
    }
    gate_only = RESEARCH.candidate_by_name("expanded_v7_reversal_dry_gap_gate_only", "v7_reversion_ic")
    growth = RESEARCH.candidate_by_name("expanded_v7_reversal_dry_gap_q05_growth", "v7_reversion_ic")
    assert "quality_score" not in gate_only.weights
    assert "quality_growth" not in gate_only.weights
    assert growth.weights["quality_growth"] == pytest.approx(0.05)
    assert gate_only.weights["reversal_5"] == pytest.approx(0.45)
    assert all(math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9) for candidate in additions)


def test_factor_diagnostic_uses_non_overlapping_rank_ic_and_topk_spread():
    dates = pd.to_datetime(["2025-01-02"] * 5 + ["2025-01-07"] * 5)
    forward_returns = pd.DataFrame(
        {
            "signal_date": dates,
            "instrument": [f"S{index}" for index in range(10)],
            "forward_gross_return": [0.01, 0.02, 0.03, 0.04, 0.05, 0.02, 0.03, 0.04, 0.05, 0.06],
            "good": [0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.2, 0.3, 0.4, 0.5],
            "bad": [0.5, 0.4, 0.3, 0.2, 0.1, 0.5, 0.4, 0.3, 0.2, 0.1],
        }
    )
    summaries = RESEARCH.summarize_factor_diagnostics(
        forward_returns,
        ["good", "bad"],
        hold_days=3,
        topk=1,
        open_cost=0.0,
        close_cost=0.0,
    )
    by_factor = {item["factor"]: item for item in summaries}
    assert by_factor["good"]["cohorts"] == 2
    assert by_factor["good"]["mean_rank_ic"] == pytest.approx(1.0)
    assert by_factor["good"]["positive_rank_ic_rate"] == pytest.approx(1.0)
    assert by_factor["good"]["mean_top_minus_bottom_gross_return"] == pytest.approx(0.04)
    assert by_factor["good"]["mean_forward_gross_return_by_factor_quintile"] == {
        "1": pytest.approx(0.015),
        "2": pytest.approx(0.025),
        "3": pytest.approx(0.035),
        "4": pytest.approx(0.045),
        "5": pytest.approx(0.055),
    }
    assert by_factor["good"]["topk"]["net_cumulative_return"] == pytest.approx((1.05 * 1.06) - 1.0)
    assert by_factor["bad"]["mean_rank_ic"] == pytest.approx(-1.0)


def test_pure_factor_aggregation_reproduces_the_diagnostic_topk_timing_and_costs():
    dates = pd.date_range("2025-01-02", periods=5, freq="B")
    rows = []
    for date_position, date in enumerate(dates):
        for instrument_position in range(6):
            rows.append(
                {
                    "datetime": date,
                    "instrument": f"S{instrument_position}",
                    "open": 100.0,
                    # Each signal's one-day exit has the same increasing
                    # return ordering as the close-known factor ranks.
                    "close": 100.0 if date_position == 0 else 100.0 + instrument_position,
                    "quality_eligible": True,
                    "amplitude_low": (instrument_position + 1) / 6.0,
                }
            )
    ranked = pd.DataFrame(rows)
    forward_returns = RESEARCH.forward_factor_return_frame(ranked, hold_days=1)
    diagnostic = RESEARCH.summarize_factor_diagnostics(
        forward_returns,
        ["amplitude_low"],
        hold_days=1,
        topk=3,
        open_cost=0.001,
        close_cost=0.002,
    )[0]
    candidate = RESEARCH.Candidate(
        name="pure_amplitude_low",
        description="Pure-factor timing parity check.",
        weights={"amplitude_low": 1.0},
    )
    _, aggregate = RESEARCH.evaluate_candidate(
        RESEARCH.score_candidate(ranked, candidate),
        candidate,
        hold_days=1,
        topk=3,
        open_cost=0.001,
        close_cost=0.002,
        development_end=dates[-1].date().isoformat(),
        regime_filter="always",
    )
    assert aggregate["development"]["rounds"] == diagnostic["topk"]["rounds"]
    assert aggregate["development"]["net_cumulative_return"] == pytest.approx(
        diagnostic["topk"]["net_cumulative_return"]
    )
    assert aggregate["development"]["max_drawdown"] == pytest.approx(diagnostic["topk"]["max_drawdown"])


def test_factor_diagnostic_catalog_includes_unused_close_known_technical_fields():
    expected = {
        "momentum_3",
        "reversal_3",
        "turnover_surge",
        "liquidity_5",
        "volatility_target_20",
        "gap_reversal",
        "drawdown_20",
        "intraday_strength",
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
        "free_float_cap_small",
        "up_day_consistency_5",
        "signed_volume_pressure_5",
        "close_above_vwap_1",
        "signed_efficiency_ratio_10",
        "return_turnover_correlation_10",
    }
    assert expected.issubset(RESEARCH.FACTOR_DIAGNOSTIC_COLUMNS)
    assert expected.issubset(RESEARCH.EXPLORATORY_DIAGNOSTIC_FACTORS)
    assert RESEARCH.SIGNED_EFFICIENCY_RATIO_10_EXPRESSION == (
        "($close/Ref($close, 10) - 1)/Sum(Abs($close/Ref($close, 1) - 1), 10)"
    )
    assert RESEARCH.RETURN_TURNOVER_CORRELATION_10_EXPRESSION == (
        "Corr($close/Ref($close, 1) - 1, $turnover, 10)"
    )


def test_factor_stability_decision_requires_positive_rank_ic_in_every_observed_year():
    stable = {
        "factor": "amplitude_low",
        "cohorts": 240,
        "mean_rank_ic": 0.03,
        "positive_rank_ic_rate": 0.56,
        "mean_top_minus_bottom_gross_return": 0.004,
        "by_signal_year": {
            str(year): {"mean_rank_ic": 0.01 + year * 0.0}
            for year in range(2019, 2024)
        },
    }
    decision = RESEARCH.factor_stability_decision(
        stable, minimum_calendar_years=5, minimum_cohorts=200
    )
    assert decision["passed"]
    assert decision["observed_calendar_years"] == ["2019", "2020", "2021", "2022", "2023"]

    unstable = {
        **stable,
        "by_signal_year": {**stable["by_signal_year"], "2021": {"mean_rank_ic": -0.001}},
    }
    rejected = RESEARCH.factor_stability_decision(
        unstable, minimum_calendar_years=5, minimum_cohorts=200
    )
    assert not rejected["passed"]
    assert "non-positive annual mean Rank IC: 2021" in rejected["failures"]


def test_factor_stability_audits_are_retained_without_strategy_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_factor_stability_audit.json").write_text(
        json.dumps(
            {
                "run_id": "factor-stability",
                "status": "completed",
                "input_diagnostic": {"run_id": "factor-diagnostic"},
                "policy": {"minimum_calendar_years": 5, "minimum_cohorts": 200},
                "factor_decisions": [
                    {"factor": "amplitude_low", "passed": True},
                    {"factor": "reversal_10", "passed": False},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_factor_stability_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, factor_stability_audits=audits
    )
    assert "开发期因子稳定性审计" in report
    assert "amplitude_low" in report
    assert "绝不自动选股" in report


def test_factor_topk_viability_requires_drawdown_and_annual_portfolio_stability():
    summary = {
        "factor": "amplitude_low",
        "cohorts": 240,
        "mean_rank_ic": 0.03,
        "positive_rank_ic_rate": 0.56,
        "mean_top_minus_bottom_gross_return": 0.004,
        "by_signal_year": {
            str(year): {"mean_rank_ic": 0.01, "topk_net_cumulative_return": 0.05}
            for year in range(2019, 2024)
        },
        "topk": {"rounds": 240, "net_cumulative_return": 0.50, "max_drawdown": -0.15, "median_holdings": 3},
    }
    assert RESEARCH.factor_topk_viability_decision(summary)["passed"]
    rejected = RESEARCH.factor_topk_viability_decision(
        {**summary, "topk": {**summary["topk"], "max_drawdown": -0.21}}
    )
    assert not rejected["passed"]
    assert "TopK maximum drawdown worse than -20%" in rejected["failures"]


def test_factor_topk_viability_audits_are_retained_without_strategy_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_factor_topk_viability_audit.json").write_text(
        json.dumps(
            {
                "run_id": "topk-viability",
                "status": "completed",
                "input_diagnostic": {"run_id": "factor-diagnostic"},
                "factor_decisions": [{"factor": "amplitude_low", "passed": False}],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_factor_topk_viability_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, factor_topk_viability_audits=audits
    )
    assert "单因子 Top‑3 组合可行性审计" in report
    assert "| topk-viability | factor-diagnostic | 1 | 无 |" in report


def test_v8_ten_day_reversal_grid_is_small_predeclared_and_does_not_rewrite_v7():
    assert len(RESEARCH.V7_CANDIDATES) == 258
    additions = RESEARCH.V8_TEN_DAY_REVERSION_CANDIDATES
    assert len(additions) == 12
    assert len(RESEARCH.candidate_library("v8_reversal_10_ic")) == 12
    assert all(candidate.name.startswith("expanded_v8_reversal_10_") for candidate in additions)
    gate_only = RESEARCH.candidate_by_name("expanded_v8_reversal_10_dry_gap_gate_only", "v8_reversal_10_ic")
    growth = RESEARCH.candidate_by_name("expanded_v8_reversal_10_dry_gap_q05_growth", "v8_reversal_10_ic")
    assert gate_only.weights["reversal_10"] == pytest.approx(0.45)
    assert "quality_growth" not in gate_only.weights
    assert growth.weights["quality_growth"] == pytest.approx(0.05)
    assert all(math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9) for candidate in additions)


def test_v9_compression_reversal_grid_is_small_predeclared_and_keeps_v8_immutable():
    assert len(RESEARCH.V8_TEN_DAY_REVERSION_CANDIDATES) == 12
    additions = RESEARCH.V9_COMPRESSION_REVERSION_CANDIDATES
    assert len(additions) == 12
    assert len(RESEARCH.candidate_library("v9_compression_reversal_ic")) == 12
    assert all(candidate.name.startswith("expanded_v9_") for candidate in additions)
    dual = RESEARCH.candidate_by_name(
        "expanded_v9_reversal_10_dual_compression_gate_only", "v9_compression_reversal_ic"
    )
    pure = RESEARCH.candidate_by_name(
        "expanded_v9_quiet_dual_compression_q10_composite", "v9_compression_reversal_ic"
    )
    assert dual.weights["reversal_10"] == pytest.approx(0.35)
    assert dual.weights["amplitude_low"] == pytest.approx(0.20)
    assert pure.weights["quality_score"] == pytest.approx(0.10)
    assert all(math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9) for candidate in additions)


def test_overlap_candidate_references_support_explicit_cross_library_comparisons():
    references = RESEARCH.overlap_candidate_references(
        None,
        None,
        [
            "v2_microstructure:expanded_v2_quiet_long_trend_q15_growth",
            "v3_quality_grid:expanded_v3_quiet_long_trend_q15_revenue",
        ],
    )
    assert [item[0] for item in references] == [
        "v2_microstructure:expanded_v2_quiet_long_trend_q15_growth",
        "v3_quality_grid:expanded_v3_quiet_long_trend_q15_revenue",
    ]
    assert [item[1] for item in references] == ["v2_microstructure", "v3_quality_grid"]
    legacy = RESEARCH.overlap_candidate_references(
        ["expanded_v2_quiet_long_trend_q10_roe", "expanded_v2_quiet_long_trend_q15_growth"],
        "v2_microstructure",
        None,
    )
    assert [item[0] for item in legacy] == [
        "expanded_v2_quiet_long_trend_q10_roe",
        "expanded_v2_quiet_long_trend_q15_growth",
    ]
    with pytest.raises(ValueError, match="either --candidate"):
        RESEARCH.overlap_candidate_references(
            ["expanded_v2_quiet_long_trend_q10_roe"],
            "v2_microstructure",
            ["v3_quality_grid:expanded_v3_quiet_long_trend_q15_revenue"],
        )


def test_candidate_overlap_loader_preserves_cross_library_summary(tmp_path):
    payload = {
        "run_id": "cross-library",
        "status": "completed",
        "candidate_libraries": ["v2_microstructure", "v3_quality_grid"],
        "candidates": [{}, {}],
        "data": {"calendar_start": "2023-01-03", "calendar_end": "2026-07-13"},
        "pairwise_overlap": [
            {"mean_jaccard": 0.5, "cohort_net_return_correlation": 0.75},
        ],
    }
    (tmp_path / "cross_candidate_overlap_audit.json").write_text(json.dumps(payload), encoding="utf-8")
    summary = RESEARCH.load_candidate_overlap_audits(tmp_path)
    assert summary == [
        {
            "run_id": "cross-library",
            "candidate_count": 2,
            "candidate_libraries": "v2_microstructure, v3_quality_grid",
            "calendar_start": "2023-01-03",
            "calendar_end": "2026-07-13",
            "test_period_used_for_pair_assessment": False,
            "pair_count": 1,
            "mean_jaccard": 0.5,
            "maximum_return_correlation": 0.75,
            "path": str((tmp_path / "cross_candidate_overlap_audit.json").resolve()),
        }
    ]


def test_overlap_audit_discloses_post_development_observations():
    assert not RESEARCH.overlap_uses_post_development_observations("2025-12-31", "2025-12-31")
    assert RESEARCH.overlap_uses_post_development_observations("2026-01-05", "2025-12-31")


def test_iteration_registry_is_append_only_and_uses_a_predeclared_test_gate(tmp_path):
    winner = {
        "candidate": "expanded_reversal_trend_20_q25_profit",
        "development_selection_score": 0.12,
        "development": {"rounds": 100, "net_cumulative_return": 0.25, "max_drawdown": -0.10},
        "test": {"rounds": 24, "net_cumulative_return": 0.05, "max_drawdown": -0.08},
    }
    iteration = RESEARCH.build_iteration_record(
        run_id="iteration-one",
        label="hold_3d_top_20",
        strategy={"holding_period_trading_days": 3, "topk": 20},
        study_path=tmp_path / "study.json",
        winner=winner,
        candidate_count=100,
        data={"calendar_end": "2026-07-13"},
    )
    assert iteration["promotion"]["status"] == "passed_initial_test"
    assert not iteration["selection"]["test_metrics_used_for_selection"]
    registry_path = tmp_path / "strategy_registry.json"
    RESEARCH.append_strategy_registry(registry_path, iteration)
    with pytest.raises(ValueError, match="already contains"):
        RESEARCH.append_strategy_registry(registry_path, iteration)
    stored = json.loads(registry_path.read_text(encoding="utf-8"))
    assert stored["iterations"][0]["candidate_library"]["count"] == 100


def test_initial_test_gate_rejects_short_or_loss_making_test_periods():
    passed, failures = RESEARCH.initial_test_gate(
        {"rounds": 19, "net_cumulative_return": -0.01, "max_drawdown": -0.21}
    )
    assert not passed
    assert len(failures) == 3


def test_top_three_requires_three_valid_members_instead_of_an_impossible_floor_of_five():
    assert RESEARCH.minimum_required_holdings(3) == 3
    assert RESEARCH.minimum_required_holdings(4) == 4
    assert RESEARCH.minimum_required_holdings(10) == 8
    with pytest.raises(ValueError, match="topk must be positive"):
        RESEARCH.minimum_required_holdings(0)


def test_research_only_iteration_cannot_be_promoted_even_if_its_historical_test_passes(tmp_path):
    winner = {
        "candidate": "expanded_trend_ma_confirmation_q20_composite",
        "development_selection_score": 0.12,
        "development": {"rounds": 100, "net_cumulative_return": 0.25, "max_drawdown": -0.10},
        "test": {"rounds": 24, "net_cumulative_return": 0.05, "max_drawdown": -0.08},
    }
    iteration = RESEARCH.build_iteration_record(
        run_id="historical-diagnostic",
        label="top3-historical",
        strategy={"holding_period_trading_days": 3, "topk": 3},
        study_path=tmp_path / "study.json",
        winner=winner,
        candidate_count=100,
        data={"calendar_end": "2026-07-13"},
        promotion_eligible=False,
    )
    assert iteration["promotion"]["status"] == "research_only_not_promoted"
    assert not iteration["promotion"]["eligible_for_promotion"]
    assert "not eligible for promotion" in iteration["promotion"]["failures"][-1]


def test_market_breadth_regime_filter_is_close_known_and_validated():
    frame = pd.DataFrame(
        {
            "market_breadth_5": [-0.01, 0.01, 0.02, 0.01],
            "market_breadth_20": [-0.02, 0.02, 0.01, -0.02],
        }
    )
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_positive").index.tolist() == [1, 2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_20_positive").index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_above_20").index.tolist() == [0, 2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_and_20_positive").index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_positive_and_above_20").index.tolist() == [2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_above_20_and_20_positive").index.tolist() == [2]
    with pytest.raises(ValueError, match="unknown regime_filter"):
        RESEARCH.apply_regime_filter(frame, "not_a_regime")


def test_market_risk_state_regimes_require_close_known_trailing_thresholds():
    frame = pd.DataFrame(
        {
            "market_breadth_20": [0.01, 0.01, 0.01, -0.01],
            "market_volatility_20": [0.03, 0.01, 0.02, 0.01],
            "market_volatility_20_trailing_p75": [float("nan"), 0.02, 0.02, 0.02],
            "market_volatility_20_trailing_p50": [float("nan"), 0.015, 0.015, 0.015],
            "market_return_dispersion_1": [0.01, 0.03, 0.02, 0.01],
            "market_return_dispersion_1_trailing_p75": [float("nan"), 0.02, 0.02, 0.02],
            "market_above_ma20_fraction": [0.8, 0.4, 0.7, 0.9],
        }
    )
    assert RESEARCH.apply_regime_filter(
        frame, "breadth_20_positive_and_volatility_below_trailing_p75"
    ).index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(
        frame, "breadth_20_positive_and_volatility_below_trailing_p50"
    ).index.tolist() == [1]
    assert RESEARCH.apply_regime_filter(
        frame, "breadth_20_positive_and_dispersion_below_trailing_p75"
    ).index.tolist() == [2]
    assert RESEARCH.apply_regime_filter(
        frame, "breadth_20_positive_and_above_ma20_majority"
    ).index.tolist() == [0, 2]
    assert RESEARCH.apply_regime_filter(
        frame, "breadth_20_positive_and_volatility_below_trailing_p75_and_above_ma20_majority"
    ).index.tolist() == [2]


def test_market_state_thresholds_exclude_the_current_close_from_their_history():
    dates = pd.date_range("2025-01-01", periods=61, freq="B")
    frame = pd.DataFrame(
        {
            "datetime": dates,
            "momentum_1": [0.01] * 61,
            "momentum_5": [0.02] * 61,
            "momentum_20": [0.03] * 61,
            "volatility_20": [0.01] * 60 + [0.99],
            "trend_ma_20": [0.01] * 61,
        }
    )
    state = RESEARCH.market_state_frame(frame, pd.Series(True, index=frame.index))
    latest = state.iloc[-1]
    assert latest["market_volatility_20"] == pytest.approx(0.99)
    assert latest["market_volatility_20_trailing_p75"] == pytest.approx(0.01)
    assert latest["market_volatility_20_trailing_p50"] == pytest.approx(0.01)


def test_return_metrics_exposes_state_activity_without_dropping_cash_cohorts():
    rounds = pd.DataFrame(
        {
            "net_return": [0.01, 0.0, -0.02, 0.0],
            "gross_return": [0.011, 0.0, -0.019, 0.0],
            "holdings": [3, 0, 3, 0],
            "regime_active": [True, False, True, False],
        }
    )
    metrics = RESEARCH.return_metrics(rounds, hold_days=3)
    assert metrics["rounds"] == 4
    assert metrics["traded_rounds"] == 2
    assert metrics["traded_round_rate"] == pytest.approx(0.5)
    assert metrics["regime_active_rounds"] == 2
    assert metrics["regime_active_rate"] == pytest.approx(0.5)


def test_execution_plan_refuses_an_inactive_regime_screen(tmp_path):
    screen_path = tmp_path / "inactive_screen.json"
    screen_path.write_text(json.dumps({"execution_allowed": False, "top_candidates": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="regime is inactive"):
        RESEARCH.run_execution_plan(SimpleNamespace(screen_path=str(screen_path)))


def test_paper_settlement_waits_for_future_sessions_and_applies_research_costs():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"]))
    instruments = [f"SZ00000{number}" for number in range(1, 6)]
    signal = {
        "signal_id": "iteration:2026-01-01",
        "signal_date": "2026-01-01",
        "strategy": {"holding_period_trading_days": 3, "open_cost": 0.001, "close_cost": 0.002},
        "top_candidates": [{"instrument": instrument} for instrument in instruments],
    }
    quotes = pd.DataFrame(
        [
            {"datetime": calendar[1], "instrument": instrument, "open": 10.0, "close": 10.0}
            for instrument in instruments
        ]
        + [
            {"datetime": calendar[3], "instrument": instrument, "open": 11.0, "close": 11.0}
            for instrument in instruments
        ]
    )
    settlement = RESEARCH.paper_settlement(signal, calendar, quotes)
    assert settlement is not None
    assert settlement["entry_date"] == "2026-01-02"
    assert settlement["exit_date"] == "2026-01-06"
    assert settlement["holdings"] == 5
    assert settlement["net_return"] == pytest.approx((1 - 0.001) * 1.1 * (1 - 0.002) - 1)
    assert RESEARCH.paper_settlement(signal, calendar[:3], quotes) is None


def test_promoted_iteration_selects_the_latest_passed_record(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "iterations": [
                    {"iteration_id": "failed", "promotion": {"status": "research_only_not_promoted"}},
                    {"iteration_id": "passed", "promotion": {"status": "passed_initial_test"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert RESEARCH.promoted_iteration(registry_path)["iteration_id"] == "passed"
    assert RESEARCH.promoted_iteration(registry_path, "passed")["iteration_id"] == "passed"


def test_paper_monitor_requires_an_explicit_unseen_start_date():
    with pytest.raises(ValueError, match="requires --not-before"):
        RESEARCH.run_paper_monitor(SimpleNamespace())


def test_close_below_vwap_is_isolated_from_historical_factor_catalogs():
    ranked = pd.DataFrame({"close_above_vwap_1": [0.1, 0.5, 0.9]})
    prospective = RESEARCH.add_prospective_vwap_reversal_factor(ranked)
    assert prospective["close_below_vwap_1"].tolist() == pytest.approx([0.9, 0.5, 0.1])
    assert RESEARCH.PROSPECTIVE_VWAP_FACTOR not in RESEARCH.FACTOR_DIAGNOSTIC_COLUMNS
    assert all(
        RESEARCH.PROSPECTIVE_VWAP_FACTOR not in candidate.weights
        for library in RESEARCH.CANDIDATE_LIBRARIES.values()
        for candidate in library
    )


def test_prospective_vwap_registration_requires_a_genuinely_unseen_start_and_is_append_only(tmp_path):
    path = tmp_path / "prospective_registry.json"
    source = {
        "run_id": "source-diagnostic",
        "path": "/immutable/source.json",
        "sha256": "abc123",
        "factor_catalog": ["close_above_vwap_1"],
        "calendar_end": "2025-12-31",
    }
    with pytest.raises(ValueError, match="cannot precede"):
        RESEARCH.append_prospective_vwap_registration(
            path,
            not_before="2026-07-13",
            latest_observed="2026-07-12",
            source=source,
        )
    with pytest.raises(ValueError, match="strictly later"):
        RESEARCH.append_prospective_vwap_registration(
            path,
            not_before="2026-07-14",
            latest_observed="2026-07-14",
            source=source,
        )
    registry = RESEARCH.append_prospective_vwap_registration(
        path,
        not_before="2026-07-14",
        latest_observed="2026-07-13",
        source=source,
    )
    registration = registry["registrations"][0]
    assert registration["factor"] == "close_below_vwap_1"
    assert registration["not_before"] == "2026-07-14"
    assert registration["latest_observed_at_registration"] == "2026-07-13"
    assert registration["strategy"] == {
        "holding_period_trading_days": 3,
        "topk": 3,
        "open_cost": 0.00012,
        "close_cost": 0.00062,
        "signal_timing": "signal at close; enter next local session open; exit third local session close",
        "rebalance_rule": "non-overlapping three-session grid anchored at the first local session on or after not_before",
    }
    serialized = json.dumps(registration)
    assert "historical_backtest" not in serialized
    assert "inverse_metrics" not in serialized
    with pytest.raises(ValueError, match="already contains"):
        RESEARCH.append_prospective_vwap_registration(
            path,
            not_before="2026-07-14",
            latest_observed="2026-07-13",
            source=source,
        )


def test_prospective_vwap_source_record_is_bound_to_the_isolated_failed_diagnostic(tmp_path):
    path = tmp_path / "source.json"
    payload = {
        "run_id": RESEARCH.PROSPECTIVE_VWAP_SOURCE_RUN_ID,
        "status": "completed",
        "factor_catalog": [RESEARCH.PROSPECTIVE_VWAP_SOURCE_FACTOR],
        "data": {"calendar_end": "2025-12-31", "test_period_used_for_factor_design": False},
        "ranking_by_development_rank_ic": [
            {"factor": RESEARCH.PROSPECTIVE_VWAP_SOURCE_FACTOR, "mean_rank_ic": -0.02}
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    source = RESEARCH.prospective_vwap_source_record(path)
    assert source["run_id"] == RESEARCH.PROSPECTIVE_VWAP_SOURCE_RUN_ID
    assert source["calendar_end"] == "2025-12-31"
    assert source["sha256"] == RESEARCH.file_sha256(path)
    payload["ranking_by_development_rank_ic"][0]["mean_rank_ic"] = 0.01
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="negative direction"):
        RESEARCH.prospective_vwap_source_record(path)


def test_prospective_vwap_rebalance_grid_is_non_overlapping():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17"]))
    assert RESEARCH.prospective_rebalance_due(
        calendar, not_before="2026-07-14", as_of="2026-07-14", hold_days=3
    )
    assert not RESEARCH.prospective_rebalance_due(
        calendar, not_before="2026-07-14", as_of="2026-07-15", hold_days=3
    )
    assert not RESEARCH.prospective_rebalance_due(
        calendar, not_before="2026-07-14", as_of="2026-07-16", hold_days=3
    )
    assert RESEARCH.prospective_rebalance_due(
        calendar, not_before="2026-07-14", as_of="2026-07-17", hold_days=3
    )


def test_prospective_vwap_monitor_does_not_touch_a_ledger_before_the_registered_date(tmp_path, monkeypatch):
    registry_path = tmp_path / "prospective_registry.json"
    ledger_path = tmp_path / "prospective_ledger.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "registrations": [
                    {
                        "registration_id": RESEARCH.PROSPECTIVE_VWAP_REGISTRATION_ID,
                        "factor": RESEARCH.PROSPECTIVE_VWAP_FACTOR,
                        "not_before": "2026-07-14",
                        "latest_observed_at_registration": "2026-07-13",
                        "strategy": {"holding_period_trading_days": 3, "topk": 3},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(RESEARCH, "latest_provider_date", lambda *_: pd.Timestamp("2026-07-13"))
    monkeypatch.setattr(
        RESEARCH,
        "local_trading_calendar",
        lambda *_args, **_kwargs: pytest.fail("calendar must not load before not_before"),
    )
    result = RESEARCH.run_prospective_vwap_monitor(
        SimpleNamespace(
            provider_uri=str(tmp_path / "provider"),
            prospective_registry_path=str(registry_path),
            prospective_ledger_path=str(ledger_path),
            registration_id=None,
        )
    )
    assert result["status"] == "not_started"
    assert result["ledger_written"] is False
    assert not ledger_path.exists()


def test_prospective_vwap_monitor_never_backfills_a_missed_signal_date(tmp_path, monkeypatch):
    registry_path = tmp_path / "prospective_registry.json"
    ledger_path = tmp_path / "prospective_ledger.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "registrations": [
                    {
                        "registration_id": RESEARCH.PROSPECTIVE_VWAP_REGISTRATION_ID,
                        "factor": RESEARCH.PROSPECTIVE_VWAP_FACTOR,
                        "not_before": "2026-07-14",
                        "latest_observed_at_registration": "2026-07-13",
                        "strategy": {"holding_period_trading_days": 3, "topk": 3},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(RESEARCH, "latest_provider_date", lambda *_: pd.Timestamp("2026-07-15"))
    monkeypatch.setattr(
        RESEARCH,
        "local_trading_calendar",
        lambda *_args, **_kwargs: pd.DatetimeIndex(
            pd.to_datetime(["2026-07-13", "2026-07-14", "2026-07-15"])
        ),
    )
    monkeypatch.setattr(
        RESEARCH,
        "run_prospective_vwap_screen",
        lambda *_args, **_kwargs: pytest.fail("a missed 2026-07-14 signal must not be reconstructed"),
    )
    result = RESEARCH.run_prospective_vwap_monitor(
        SimpleNamespace(
            provider_uri=str(tmp_path / "provider"),
            prospective_registry_path=str(registry_path),
            prospective_ledger_path=str(ledger_path),
            registration_id=None,
        )
    )
    assert result["status"] == "completed"
    assert result["signal_due"] is False
    assert result["new_signal"] is None
    assert result["ledger_written"] is False
    assert not ledger_path.exists()


def test_development_only_iteration_can_be_explicitly_registered_for_separate_forward_observation(tmp_path):
    iteration = {
        "iteration_id": "v2-development-only",
        "strategy": {"candidate_library": "v2_microstructure"},
        "selection": {"winner": "expanded_v2_quiet_long_trend_q20_composite"},
        "data": {"calendar_end": "2025-12-31", "development_end": "2025-12-31"},
        "initial_test": {"rounds": 0},
        "promotion": {"status": "research_only_not_promoted"},
    }
    registry_path = tmp_path / "strategy_registry.json"
    registry_path.write_text(json.dumps({"schema_version": 1, "iterations": [iteration]}), encoding="utf-8")
    selected = RESEARCH.research_observation_iteration(registry_path, "v2-development-only")
    shadow_path = tmp_path / "shadow_observations.json"
    plan = RESEARCH.append_shadow_observation(
        shadow_path, iteration=selected, not_before="2026-07-14"
    )
    assert plan["observations"][0]["candidate"] == "expanded_v2_quiet_long_trend_q20_composite"
    assert plan["observations"][0]["not_before"] == "2026-07-14"
    with pytest.raises(ValueError, match="already contains"):
        RESEARCH.append_shadow_observation(shadow_path, iteration=selected, not_before="2026-07-14")


def test_shadow_observation_refuses_an_iteration_with_a_historical_test_window(tmp_path):
    registry_path = tmp_path / "strategy_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "iterations": [
                    {
                        "iteration_id": "historical-diagnostic",
                        "data": {"calendar_end": "2026-07-13", "development_end": "2025-12-31"},
                        "initial_test": {"rounds": 38},
                        "promotion": {"status": "research_only_not_promoted"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no historical test window"):
        RESEARCH.research_observation_iteration(registry_path, "historical-diagnostic")


def test_shadow_suspension_preserves_registration_and_monitor_skips_it(tmp_path, monkeypatch):
    plan_path = tmp_path / "shadow_observations.json"
    plan_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "observations": [
                    {"iteration_id": "pending-review", "candidate": "candidate", "not_before": "2026-07-14"}
                ],
            }
        ),
        encoding="utf-8",
    )
    suspension_path = tmp_path / "suspensions.json"
    suspended = RESEARCH.append_shadow_suspension(
        suspension_path, iteration_id="pending-review", reason="metric correction review"
    )
    assert suspended["suspensions"][0]["iteration_id"] == "pending-review"
    with pytest.raises(ValueError, match="already suspended"):
        RESEARCH.append_shadow_suspension(
            suspension_path, iteration_id="pending-review", reason="duplicate"
        )
    monkeypatch.setattr(RESEARCH, "run_paper_monitor", lambda *_: pytest.fail("suspended observation was monitored"))
    result = RESEARCH.run_shadow_monitor(
        SimpleNamespace(
            shadow_registry_path=str(plan_path),
            shadow_suspension_registry_path=str(suspension_path),
            shadow_ledger_path=str(tmp_path / "shadow_ledger.json"),
        )
    )
    assert result["observations"] == [
        {
            "status": "suspended",
            "iteration_id": "pending-review",
            "candidate": "candidate",
            "reason": "metric correction review",
        }
    ]


def test_research_report_renders_registry_and_only_counts_settled_paper_returns():
    registry = {
        "iterations": [
            {
                "label": "three_day_cycle",
                "strategy": {"holding_period_trading_days": 3, "topk": 10, "regime_filter": "breadth_5_above_20"},
                "selection": {"winner": "candidate", "development": {"net_cumulative_return": 0.1}},
                "initial_test": {"net_cumulative_return": 0.02, "max_drawdown": -0.05},
                "promotion": {"status": "passed_initial_test"},
            }
        ]
    }
    ledger = {
        "signals": [{"signal_id": "settled"}, {"signal_id": "pending"}],
        "settlements": [{"signal_id": "settled", "net_return": 0.03}],
    }
    report = RESEARCH.render_three_day_research_report(registry, ledger)
    assert "three_day_cycle" in report
    assert "已记录信号：2 笔；已结算：1 笔；待结算：1 笔。" in report
    assert "已结算纸面累计净收益：+3.00%" in report


def test_research_report_keeps_post_development_factor_evidence_separate():
    prospective_registry = {
        "registrations": [
            {
                "registration_id": "future-vwap",
                "factor": "close_below_vwap_1",
                "not_before": "2026-07-14",
                "source_diagnostic": {"run_id": "failed-direct-factor"},
            }
        ]
    }
    prospective_ledger = {
        "signals": [
            {"signal_id": "settled", "registration_id": "future-vwap"},
            {"signal_id": "pending", "registration_id": "future-vwap"},
        ],
        "settlements": [{"signal_id": "settled", "net_return": 0.02}],
    }
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        prospective_factor_registry=prospective_registry,
        prospective_factor_ledger=prospective_ledger,
    )
    assert "事后形成因子的纯前瞻观察" in report
    assert "future-vwap" in report
    assert "已结算前瞻累计净收益：+2.00%" in report
    assert "禁止历史反向回测" in report


def test_walk_forward_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_walk_forward_selection_audit.json").write_text(
        json.dumps(
            {
                "run_id": "walk-forward-v2",
                "status": "completed",
                "candidate_library": {"id": "v2_microstructure", "count": 150},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "protocol": {"first_test_year": 2021, "last_test_year": 2025},
                "folds": [
                    {"winner_selected_on_training_only": "candidate"},
                    {"winner_selected_on_training_only": None},
                ],
                "aggregate_selected_out_of_sample": {"net_cumulative_return": 0.12, "max_drawdown": -0.08},
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_walk_forward_selection_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, walk_forward_selection_audits=audits
    )
    assert "滚动候选选择审计" in report
    assert "walk-forward-v2" in report
    assert "1/2" in report
    assert "不能自动晋级或替换前瞻候选" in report


def test_selection_multiplicity_audit_uses_development_only_and_retains_report_record(tmp_path):
    dates = pd.bdate_range("2024-01-02", periods=20)

    def write_candidate(path, candidate, development_return, test_return):
        cohorts = [
            {
                "signal_date": date.date().isoformat(),
                "segment": "development",
                "net_return": development_return,
                "holdings": 3,
            }
            for date in dates
            if candidate != "alternate" or date != dates[-2]
        ]
        cohorts.append(
            {
                "signal_date": "2025-01-02",
                "segment": "test",
                "net_return": test_return,
                "holdings": 3,
            }
        )
        path.write_text(json.dumps({"candidate": candidate, "cohorts": cohorts}), encoding="utf-8")

    winner_path = tmp_path / "winner.json"
    alternate_path = tmp_path / "alternate.json"
    write_candidate(winner_path, "winner", 0.01, -0.99)
    # This large test-period return must not influence the development-only winner.
    write_candidate(alternate_path, "alternate", 0.002, 0.90)
    study_path = tmp_path / "study.json"
    study_path.write_text(
        json.dumps(
            {
                "run_id": "saved-sweep",
                "winner_selected_on_development_only": "winner",
                "ranking_by_development": [
                    {"candidate": "winner", "path": str(winner_path)},
                    {"candidate": "alternate", "path": str(alternate_path)},
                ],
            }
        ),
        encoding="utf-8",
    )

    selection_input = RESEARCH.load_selection_multiplicity_input(study_path)
    assert selection_input.candidates == ("winner", "alternate")
    assert selection_input.net_returns.shape == (20, 2)
    assert not selection_input.observed[-2, 1]
    assert selection_input.net_returns[-2, 1] == 0.0
    bootstrap = RESEARCH.selection_multiplicity_bootstrap(
        selection_input, hold_days=3, replicates=100, block_cohorts=3, seed=1
    )
    assert bootstrap["winner"] == "winner"
    assert bootstrap["winner_resample_frequency"] == 1.0
    assert bootstrap["global_null_max_score_p_value"] == pytest.approx(1 / 101)

    result = RESEARCH.run_selection_multiplicity_audit(
        SimpleNamespace(
            study=str(study_path),
            experiment_root=str(tmp_path),
            hold_days=3,
            bootstrap_replicates=100,
            block_cohorts=3,
            seed=1,
        )
    )
    audit = json.loads(Path(result["audit_path"]).read_text(encoding="utf-8"))
    assert audit["data"]["test_period_used"] is False
    audits = RESEARCH.load_selection_multiplicity_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, selection_multiplicity_audits=audits
    )
    assert "候选选择多重尝试审计" in report
    assert "绝不读取测试期" in report
    assert "winner" in report


def test_selection_multiplicity_infers_legacy_drawdown_only_for_historical_reproduction():
    returns = RESEARCH.np.array(
        [
            [-0.10, 0.005],
            [0.08, 0.005],
            [0.08, 0.005],
            [0.08, 0.005],
        ]
    )
    observed = RESEARCH.np.ones_like(returns, dtype=bool)
    legacy_scores = RESEARCH.pooled_return_drawdown_scores(
        returns, 3, observed, include_initial_equity=False
    )
    selection_input = RESEARCH.SelectionMultiplicityInput(
        study={
            "ranking_by_development": [
                {"candidate": "legacy-winner", "development_selection_score": float(legacy_scores[0])},
                {"candidate": "other", "development_selection_score": float(legacy_scores[1])},
            ]
        },
        candidates=("legacy-winner", "other"),
        signal_dates=pd.bdate_range("2024-01-02", periods=4),
        net_returns=returns,
        holdings=RESEARCH.np.ones_like(returns),
        observed=observed,
    )
    convention = RESEARCH.infer_selection_score_drawdown_convention(selection_input, hold_days=3)
    assert convention["drawdown_convention"] == "legacy_post_first_cohort_high_water"
    assert not convention["include_initial_equity"]
    assert convention["stored_scores_verified"]
    assert RESEARCH.pooled_return_drawdown_scores(returns, 3, observed)[0] < legacy_scores[0]


def test_limit_like_event_mask_uses_distinct_main_and_chinext_hurdles():
    frame = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ300001", "SZ300002", "SZ000002"],
            "momentum_1": [0.096, 0.196, 0.194, 0.12],
            "close_to_high": [0.996, 0.999, 0.999, 0.994],
        }
    )
    assert RESEARCH.limit_like_event_mask(frame).tolist() == [True, True, False, False]


def test_limit_like_event_rounds_select_turnover_ranked_complete_next_open_basket():
    dates = pd.bdate_range("2024-01-02", periods=6)
    rows = []
    for position, date in enumerate(dates):
        for instrument, turnover in (
            ("SZ000001", 2.0),
            ("SZ000002", 4.0),
            ("SZ000003", 3.0),
            ("SZ300001", 5.0),
        ):
            is_event = position == 0 and instrument != "SZ300001"
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": 10.0,
                    "close": 11.0 if position == 3 else 10.0,
                    "momentum_1": 0.10 if is_event else 0.01,
                    "close_to_high": 0.999 if is_event else 0.98,
                    "turnover_surge_1": turnover,
                    "quality_eligible": True,
                }
            )
    rounds, status = RESEARCH.limit_like_event_rounds(
        pd.DataFrame(rows), hold_days=3, topk=3, open_cost=0.0, close_cost=0.0
    )
    assert status == {
        "eligible_rebalance_cohorts": 1,
        "event_rebalance_cohorts": 1,
        "complete_executable_cohorts": 1,
        "discarded_incomplete_or_unquoted_event_cohorts": 0,
    }
    assert len(rounds) == 1
    assert rounds.iloc[0]["holdings"] == 3
    assert rounds.iloc[0]["gross_return"] == pytest.approx(0.10)
    assert rounds.iloc[0]["net_return"] == pytest.approx(0.10)
    assert "fewer than 200 executable event cohorts" in RESEARCH.limit_like_event_decision(rounds, 3)["failures"]


def test_limit_like_event_audits_are_retained_without_strategy_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_limit_like_event_audit.json").write_text(
        json.dumps(
            {
                "run_id": "limit-like",
                "status": "completed",
                "data": {
                    "calendar_start": "2019-01-02",
                    "calendar_end": "2025-12-31",
                    "event_rebalance_cohorts": 220,
                    "test_period_used": False,
                },
                "result": {
                    "passed": False,
                    "performance": {"rounds": 205, "net_cumulative_return": -0.02, "max_drawdown": -0.22},
                },
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_limit_like_event_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, limit_like_event_audits=audits
    )
    assert "限价样强势收盘事件审计" in report
    assert "limit-like" in report
    assert "不通过（停止）" in report


def test_quarterly_profit_acceleration_event_uses_only_newly_effective_positive_reports():
    dates = pd.bdate_range("2024-05-06", periods=6)
    rows = []
    for position, date in enumerate(dates):
        for instrument, acceleration in (
            ("SZ000001", 2.0),
            ("SZ000002", 5.0),
            ("SZ000003", 3.0),
            ("SZ000004", -4.0),
        ):
            newly_effective = position == 0 and instrument != "SZ000004"
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": 10.0,
                    "close": 11.0 if position == 3 else 10.0,
                    "quality_eligible": True,
                    "quality_effective_date": date if newly_effective else dates[0] - pd.Timedelta(days=1),
                    "profit_yoy_acceleration": acceleration,
                }
            )
    rounds, status = RESEARCH.quarterly_profit_acceleration_event_rounds(
        pd.DataFrame(rows), hold_days=3, topk=3, open_cost=0.0, close_cost=0.0
    )
    assert status == {
        "eligible_rebalance_cohorts": 1,
        "event_rebalance_cohorts": 1,
        "complete_executable_cohorts": 1,
        "discarded_incomplete_or_unquoted_event_cohorts": 0,
    }
    assert len(rounds) == 1
    assert rounds.iloc[0]["holdings"] == 3
    assert rounds.iloc[0]["net_return"] == pytest.approx(0.10)


def test_quarterly_profit_acceleration_event_audits_are_retained_without_strategy_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_quarterly_profit_acceleration_event_audit.json").write_text(
        json.dumps(
            {
                "run_id": "quarterly-acceleration",
                "status": "completed",
                "data": {
                    "calendar_start": "2019-01-02",
                    "calendar_end": "2025-12-31",
                    "event_rebalance_cohorts": 240,
                    "test_period_used": False,
                },
                "result": {
                    "passed": True,
                    "performance": {"rounds": 205, "net_cumulative_return": 0.12, "max_drawdown": -0.15},
                },
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_quarterly_profit_acceleration_event_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, quarterly_profit_acceleration_event_audits=audits
    )
    assert "季度利润加速公告事件审计" in report
    assert "quarterly-acceleration" in report
    assert "通过（仍不可直接选股）" in report


def test_research_report_marks_non_promotable_historical_diagnostics():
    registry = {
        "iterations": [
            {
                "label": "historical-top3",
                "strategy": {"holding_period_trading_days": 3, "topk": 3},
                "selection": {"winner": "candidate", "development": {}},
                "initial_test": {},
                "promotion": {
                    "status": "research_only_not_promoted",
                    "eligible_for_promotion": False,
                },
            }
        ]
    }
    assert "历史诊断，不可晋级" in RESEARCH.render_three_day_research_report(registry, {"signals": [], "settlements": []})


def test_regime_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T152638Z_regime_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T152638Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_regime_selected_on_development_only": None,
                "ranking_by_development": [
                    {"development_selection_score": None},
                    {"development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_regime_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, regime_audits=audits
    )
    assert "市场状态审计" in report
    assert "defensive_candidate" in report
    assert "无合格状态（0/2）" in report
    assert "不能回写既有策略" in report


def test_model_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T190000Z_model_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T190000Z",
                "status": "completed",
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2026-07-13"},
                "protocol": {"development_start": "2023-01-01", "development_end": "2025-12-31"},
                "winner_configuration_selected_on_development_only": None,
                "ranking_by_development": [
                    {"configuration": "ridge", "development_selection_score": None},
                    {"configuration": "lgbm_shallow", "development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_model_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, model_audits=audits
    )
    assert "三日滚动模型审计" in report
    assert "无合格模型（0/2）" in report


def test_loss_cap_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T160011Z_loss_cap_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T160011Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_close_loss_cap_selected_on_development_only": None,
                "ranking_by_development": [
                    {"close_loss_cap": None, "development_selection_score": None},
                    {"close_loss_cap": 0.05, "development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_loss_cap_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, loss_cap_audits=audits
    )
    assert "收盘损失上限审计" in report
    assert "defensive_candidate" in report
    assert "无合格损失上限（0/2）" in report
    assert "原三日周期内保持现金" in report


def test_entry_gap_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T164955Z_entry_gap_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T164955Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2026-07-13"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_max_entry_gap_selected_on_development_only": None,
                "has_development_qualified_entry_gap": False,
                "ranking_by_development": [
                    {"max_entry_gap": None, "development_selection_score": None},
                    {"max_entry_gap": 0.02, "development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_entry_gap_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, entry_gap_audits=audits
    )
    assert "次日开盘跳空审计" in report
    assert "defensive_candidate" in report
    assert "无合格跳空上限（0/2）" in report


def test_factor_diagnostics_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260714T000000Z_factor_diagnostic.json").write_text(
        json.dumps(
            {
                "run_id": "factor-diagnostic",
                "status": "completed",
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "ranking_by_development_rank_ic": [
                    {"factor": "reversal_1", "mean_rank_ic": 0.03125},
                    {"factor": "momentum_20", "mean_rank_ic": 0.01},
                ],
            }
        ),
        encoding="utf-8",
    )
    diagnostics = RESEARCH.load_factor_diagnostics(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, factor_diagnostics=diagnostics
    )
    assert "开发期单因子三日预测诊断" in report
    assert "reversal_1" in report
    assert "0.0312" in report


def test_billboard_holdouts_are_retained_as_non_promotable_event_evidence(tmp_path):
    (tmp_path / "billboard_event_factor_holdout.json").write_text(
        json.dumps(
            {
                "run_id": "billboard-holdout",
                "status": "completed",
                "hypothesis": {
                    "factor": "billboard_low_deal_to_float",
                    "development_diagnostic_run_id": "development-only",
                },
                "data": {"holdout_start": "2026-01-01", "holdout_end": "2026-07-13"},
                "result": {
                    "cohorts": 12,
                    "mean_rank_ic": 0.04,
                    "mean_top_minus_bottom_gross_return": 0.01,
                },
                "supportive_holdout_association": True,
            }
        ),
        encoding="utf-8",
    )
    holdouts = RESEARCH.load_event_factor_holdouts(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, event_factor_holdouts=holdouts
    )
    assert "事件因子留出期验证" in report
    assert "billboard_low_deal_to_float" in report
    assert "方向一致（仍不可晋级）" in report


def test_correlation_audits_record_full_windows_and_unqualified_diversification(tmp_path):
    (tmp_path / "old_basket_correlation_audit.json").write_text(
        json.dumps({"status": "completed", "correlation_summary": {}}), encoding="utf-8"
    )
    (tmp_path / "full_basket_correlation_audit.json").write_text(
        json.dumps(
            {
                "run_id": "full-window",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "correlation_summary": {
                    "required_return_days": 20,
                    "valid_correlation_basket_count": 12,
                    "max_pairwise_correlation_p90": 0.68,
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "20260713T161805Z_diversification_audit.json").write_text(
        json.dumps(
            {
                "run_id": "diversification",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_max_pairwise_correlation_selected_on_development_only": None,
                "has_development_qualified_diversification_cap": False,
                "ranking_by_development": [
                    {"development_selection_score": None},
                    {"development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    correlation_audits = RESEARCH.load_basket_correlation_audits(tmp_path)
    diversification_audits = RESEARCH.load_diversification_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        basket_correlation_audits=correlation_audits,
        diversification_audits=diversification_audits,
    )
    assert len(correlation_audits) == 1
    assert "篮子相关性审计" in report
    assert "0.68" in report
    assert "相关性分散化审计" in report
    assert "无合格上限（0/2）" in report


def test_research_report_labels_development_only_preregistration_for_forward_observation():
    registry = {
        "iterations": [
            {
                "label": "v2-development-only",
                "strategy": {"holding_period_trading_days": 3, "topk": 3},
                "data": {"calendar_end": "2025-12-31", "development_end": "2025-12-31"},
                "selection": {"winner": "candidate", "development": {}},
                "initial_test": {"rounds": 0},
                "promotion": {"status": "research_only_not_promoted", "eligible_for_promotion": False},
            }
        ]
    }
    assert "开发期预登记，前瞻观察" in RESEARCH.render_three_day_research_report(
        registry, {"signals": [], "settlements": []}
    )


def test_research_report_keeps_shadow_observation_results_separate():
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        {
            "signals": [{"signal_id": "shadow"}],
            "settlements": [{"signal_id": "shadow", "net_return": 0.02}],
        },
    )
    assert "研究候选前瞻纸面观察" in report
    assert "已结算纸面累计净收益：+2.00%" in report


def test_shadow_observation_report_breaks_out_each_candidate_instead_of_pooling_them():
    shadow_registry = {
        "observations": [
            {
                "iteration_id": "first",
                "candidate": "candidate_one",
                "candidate_library": "v2_microstructure",
                "not_before": "2026-07-14",
            },
            {
                "iteration_id": "second",
                "candidate": "candidate_two",
                "candidate_library": "v2_microstructure",
                "not_before": "2026-07-14",
            },
        ]
    }
    shadow_ledger = {
        "signals": [
            {"signal_id": "first:2026-07-14", "iteration_id": "first"},
            {"signal_id": "second:2026-07-14", "iteration_id": "second"},
        ],
        "settlements": [{"signal_id": "first:2026-07-14", "net_return": 0.03}],
    }
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, shadow_ledger, shadow_registry
    )
    assert "candidate_one" in report
    assert "candidate_two" in report
    assert "| first | candidate_one | v2_microstructure | 2026-07-14 | 前瞻观察中 | 1 | 1 | 0 | +3.00% |" in report
    assert "| second | candidate_two | v2_microstructure | 2026-07-14 | 前瞻观察中 | 1 | 0 | 1 | — |" in report


def test_current_st_names_are_excluded_from_screen_by_default():
    screen = pd.DataFrame({"instrument": ["SZ000001", "SZ000002"]})
    metadata = {"SZ000001": {"is_st": False}, "SZ000002": {"is_st": True}}
    assert RESEARCH.filter_st_candidates(screen, metadata, include_st=False)["instrument"].tolist() == ["SZ000001"]
    assert len(RESEARCH.filter_st_candidates(screen, metadata, include_st=True)) == 2


def test_return_metrics_include_cost_adjusted_cumulative_return():
    rounds = pd.DataFrame(
        {
            "net_return": [0.10, -0.05],
            "gross_return": [0.11, -0.04],
            "holdings": [30, 28],
        }
    )
    metrics = RESEARCH.return_metrics(rounds, hold_days=5)
    assert metrics["rounds"] == 2
    assert round(metrics["net_cumulative_return"], 6) == round(1.10 * 0.95 - 1.0, 6)
    assert metrics["max_drawdown"] < 0


def test_return_metrics_counts_a_first_cohort_loss_as_drawdown():
    rounds = pd.DataFrame(
        {
            "net_return": [-0.10, 0.05],
            "gross_return": [-0.09, 0.06],
            "holdings": [3, 3],
        }
    )
    metrics = RESEARCH.return_metrics(rounds, hold_days=3)
    assert metrics["max_drawdown"] == pytest.approx(-0.10)


def test_a_share_fee_rules_apply_user_commission_and_sell_stamp_duty():
    rules = RESEARCH.AShareExecutionRules()
    buy = RESEARCH.a_share_trade_fees(10_000.0, "buy", rules)
    sell = RESEARCH.a_share_trade_fees(10_000.0, "sell", rules)
    assert buy == {"commission": 1.0, "transfer_fee": 0.2, "stamp_duty": 0.0, "total": 1.2}
    assert sell == {"commission": 1.0, "transfer_fee": 0.2, "stamp_duty": 5.0, "total": 6.2}


def test_board_lot_plan_skips_unaffordable_name_without_reallocating_cash():
    rules = RESEARCH.AShareExecutionRules()
    candidates = [
        {"rank": 1, "instrument": "SZ300972", "name": "万辰集团", "reference_close": 192.28},
        {"rank": 2, "instrument": "SZ300043", "name": "星辉娱乐", "reference_close": 4.81},
        {"rank": 3, "instrument": "SZ300251", "name": "光线传媒", "reference_close": 11.80},
    ]
    plan = RESEARCH.plan_lot_orders(candidates, 100_000.0, rules)
    high_price, star, light = plan["orders"]
    assert high_price["status"] == "skipped_insufficient_budget_for_one_lot"
    assert star["quantity"] == 1000
    assert light["quantity"] == 400
    assert plan["summary"]["planned_candidates"] == 2
    assert plan["summary"]["actual_gross_exposure"] < 0.15
    assert plan["summary"]["unused_pilot_budget"] > 0
