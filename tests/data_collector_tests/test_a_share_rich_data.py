"""Offline contract tests for credentialed A-share rich-data ingestion."""

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_rich_data.py"
SPEC = importlib.util.spec_from_file_location("a_share_rich_data", SCRIPT_PATH)
RICH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RICH
SPEC.loader.exec_module(RICH)


def test_vendor_symbol_mapping_and_symbol_validation():
    assert RICH.vendor_symbol("600519", "tushare") == "600519.SH"
    assert RICH.vendor_symbol("000001", "jqdata") == "000001.XSHE"
    assert RICH.vendor_symbol("688981", "rqdata") == "688981.XSHG"
    assert RICH.parse_symbols("600519,000001,600519") == ["600519", "000001"]
    with pytest.raises(Exception, match="unsupported A-share code"):
        RICH.parse_symbols("430047")


def test_provider_status_never_returns_credential_values(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "this-is-a-secret")
    availability = RICH.provider_availability("tushare")
    rendered = str(availability)
    assert "this-is-a-secret" not in rendered
    assert availability.missing_environment == ()


def test_canonicalize_minutes_handles_provider_column_names_and_sorts_rows():
    raw = pd.DataFrame(
        {
            "trade_time": ["2026-07-13 09:31:00", "2026-07-13 09:30:00", "2026-07-13 09:30:00"],
            "open": [10.1, 10.0, 10.0],
            "high": [10.2, 10.1, 10.1],
            "low": [10.0, 9.9, 9.9],
            "close": [10.15, 10.05, 10.04],
            "vol": [200, 100, 101],
            "money": [2030, 1005, 1014],
        }
    )
    normalized = RICH.canonicalize_minute_bars(
        raw, "tushare", "600519", dt.date(2026, 7, 13), dt.date(2026, 7, 13)
    )
    assert normalized["datetime"].dt.strftime("%H:%M:%S").tolist() == ["09:30:00", "09:31:00"]
    assert normalized["close"].tolist() == pytest.approx([10.04, 10.15])
    assert normalized["symbol"].tolist() == ["SH600519", "SH600519"]
    assert normalized["amount"].tolist() == pytest.approx([1014.0, 2030.0])


def test_canonicalize_minutes_rejects_invalid_ohlc():
    raw = pd.DataFrame(
        {
            "datetime": ["2026-07-13 09:30:00"],
            "open": [10.0], "high": [9.0], "low": [9.5], "close": [9.8],
            "volume": [100.0], "amount": [1000.0],
        }
    )
    with pytest.raises(RICH.RichDataError, match="invalid minute bars"):
        RICH.canonicalize_minute_bars(raw, "rqdata", "000001", dt.date(2026, 7, 13), dt.date(2026, 7, 13))


def test_minute_acceptance_uses_scale_invariant_daily_price_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", tmp_path / "daily")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:31:00", "2026-07-13 09:32:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1], "high": [10.15, 10.3], "low": [9.8, 10.0], "close": [10.1, 10.1],
            "volume": [1.0, 2.0], "amount": [10.0, 20.0], "provider": ["tushare", "tushare"],
        }
    )
    (tmp_path / "daily").mkdir()
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-13"]), "symbol": ["SH600519"],
            "open": [20.0], "high": [20.6], "low": [19.6], "close": [20.2],
            "volume": [3.0], "amount": [30.0],
        }
    ).to_parquet(tmp_path / "daily" / "sh600519.parquet", index=False)
    report = RICH.minute_acceptance_report(frame)
    assert report["status"] == "automatic_checks_passed_pending_time_alignment"
    assert report["daily_reconciliation"]["days"][0]["inferred_volume_unit"] == "lots"


def test_minute_session_check_rejects_lunch_break_timestamp():
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 12:00:00"]), "symbol": ["SH600519"],
            "open": [10.0], "high": [10.0], "low": [10.0], "close": [10.0], "volume": [1.0], "amount": [10.0],
        }
    )
    assert RICH.minute_session_check(frame)["status"] == "failed"


def test_tushare_minute_request_uses_explicit_session_timestamps(monkeypatch):
    captured = {}

    class FakeTushare:
        @staticmethod
        def pro_bar(**kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(RICH, "_import_tushare", lambda: FakeTushare())
    RICH.fetch_tushare_minutes("600519", dt.date(2026, 7, 13), dt.date(2026, 7, 13), "1m")
    assert captured["start_date"] == "2026-07-13 09:00:00"
    assert captured["end_date"] == "2026-07-13 17:00:00"


def test_validate_range_requires_completed_session_and_large_request_confirmation():
    completed = RICH.latest_completed_session_date()
    with pytest.raises(RICH.RichDataError, match="not a completed"):
        future = completed + dt.timedelta(days=1)
        RICH.validate_range(future, future, False)
    with pytest.raises(RICH.RichDataError, match="allow-large"):
        RICH.validate_range(dt.date(2026, 1, 1), dt.date(2026, 7, 13), False, unit_count=4)


def test_snapshot_write_records_checksum_and_minute_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "metadata" / "runs")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:30:00", "2026-07-13 09:31:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1], "high": [10.1, 10.2], "low": [9.9, 10.0], "close": [10.05, 10.15],
            "volume": [100.0, 200.0], "amount": [1005.0, 2030.0], "provider": ["tushare", "tushare"],
        }
    )
    manifest_path = RICH.write_minute_snapshot("tushare", "1m", dt.date(2026, 7, 13), dt.date(2026, 7, 13), {"600519": frame})
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["prices"] == "raw_unadjusted"
    assert manifest["files"][0]["rows"] == 2
    assert len(manifest["files"][0]["sha256"]) == 64
    assert manifest["files"][0]["daily_summary"][0]["bars"] == 2
