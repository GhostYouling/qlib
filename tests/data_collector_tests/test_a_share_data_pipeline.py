"""Focused offline tests for the A-share ingestion pipeline."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd


PIPELINE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_data_pipeline.py"
SPEC = importlib.util.spec_from_file_location("a_share_data_pipeline", PIPELINE_PATH)
PIPELINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = PIPELINE
SPEC.loader.exec_module(PIPELINE)


def test_board_classification_and_qlib_symbols():
    assert PIPELINE.classify_board("600519") == "main"
    assert PIPELINE.classify_board("002594") == "main"
    assert PIPELINE.classify_board("300750") == "chinext"
    assert PIPELINE.classify_board("688981") == "star"
    assert PIPELINE.classify_board("430047") is None
    assert PIPELINE.classify_board("900901") is None
    assert PIPELINE.qlib_symbol("600519") == "SH600519"
    assert PIPELINE.qlib_symbol("300750") == "SZ300750"


def test_parse_daily_bars_calculates_vwap_without_network(monkeypatch):
    client = PIPELINE.EastmoneyClient(delay=0)
    monkeypatch.setattr(
        client,
        "_get_json",
        lambda urls, params: {
            "data": {
                "klines": [
                    "2026-07-10,10,10.5,10.8,9.8,1000,1020000,10,5,0.5,1.2",
                    "2026-07-13,10.5,10.2,10.7,10.1,0,0,1,-2.86,-0.3,0",
                ]
            }
        },
    )
    instrument = PIPELINE.Instrument("SH600519", "600519", "测试", "main", None, None, None, False)
    data = client.daily_bars(instrument, PIPELINE.parse_date("2026-07-01"), PIPELINE.parse_date("2026-07-13"), "qfq")
    assert list(data["symbol"].unique()) == ["SH600519"]
    assert data.loc[data["date"] == pd.Timestamp("2026-07-10"), "vwap"].iloc[0] == 10.2
    assert pd.isna(data.loc[data["date"] == pd.Timestamp("2026-07-13"), "vwap"].iloc[0])


def test_merge_and_save_bars_keeps_refreshed_row(tmp_path):
    target = tmp_path / "sh600519.parquet"
    initial = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-10"]),
            "symbol": ["SH600519"],
            "open": [10.0],
            "high": [10.3],
            "low": [9.9],
            "close": [10.1],
            "volume": [100.0],
            "amount": [101000.0],
            "vwap": [10.1],
            "change": [0.1],
            "pct_chg": [1.0],
            "turnover": [1.0],
        }
    )
    refreshed = initial.copy()
    refreshed.loc[0, "close"] = 10.2
    combined = PIPELINE.merge_and_save_bars(target, initial)
    combined = PIPELINE.merge_and_save_bars(target, refreshed)
    assert len(combined) == 1
    assert pd.read_parquet(target)["close"].iloc[0] == 10.2


def test_latest_completed_session_date_avoids_live_and_weekend_bars():
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-13 15:29").to_pydatetime()).isoformat() == "2026-07-10"
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-13 15:30").to_pydatetime()).isoformat() == "2026-07-13"
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-12 17:00").to_pydatetime()).isoformat() == "2026-07-10"


def test_merge_and_save_bars_prunes_provisional_tail(tmp_path):
    target = tmp_path / "sh600519.parquet"
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-10", "2026-07-13"]),
            "symbol": ["SH600519", "SH600519"],
            "open": [10.0, 10.1],
            "high": [10.3, 10.4],
            "low": [9.9, 10.0],
            "close": [10.1, 10.2],
            "volume": [100.0, 101.0],
            "amount": [101000.0, 103020.0],
            "vwap": [10.1, 10.2],
            "change": [0.1, 0.1],
            "pct_chg": [1.0, 1.0],
            "turnover": [1.0, 1.0],
        }
    )
    merged = PIPELINE.merge_and_save_bars(target, data, end=PIPELINE.parse_date("2026-07-10"))
    assert merged["date"].dt.date.astype(str).tolist() == ["2026-07-10"]


def test_invalid_price_mask_rejects_negative_qfq_artifacts():
    bars = pd.DataFrame(
        {
            "open": [10.0, -0.1, 10.0],
            "high": [10.5, 0.2, 9.0],
            "low": [9.8, -0.2, 9.5],
            "close": [10.2, 0.1, 9.7],
        }
    )
    assert PIPELINE.invalid_price_mask(bars).tolist() == [False, True, True]
