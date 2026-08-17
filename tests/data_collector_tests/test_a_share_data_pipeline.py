"""Focused offline tests for the A-share ingestion pipeline."""

import importlib.util
import os
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest


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


def test_data_root_command_prints_resolved_root_without_scanning(capsys):
    args = PIPELINE.build_parser().parse_args(["data-root"])

    assert args.func(args) == 0
    assert capsys.readouterr().out.strip() == str(PIPELINE.DATA_ROOT)


def test_data_root_command_honors_process_override(tmp_path):
    configured = tmp_path / "activated-tushare-root"
    environment = os.environ.copy()
    environment["QLIB_A_SHARE_DATA_ROOT"] = str(configured)

    completed = subprocess.run(
        [sys.executable, str(PIPELINE_PATH), "data-root"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.stdout.strip() == str(configured.resolve())
    assert completed.stderr == ""


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


def test_merge_and_save_bars_restores_missing_symbol_without_changing_identity(tmp_path):
    target = tmp_path / "sh600519.parquet"
    recovered = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-13"]),
            "open": [10.0], "high": [10.3], "low": [9.9], "close": [10.1],
            "volume": [100.0], "amount": [101000.0], "vwap": [10.1],
            "change": [0.1], "pct_chg": [1.0], "turnover": [1.0],
        }
    )
    merged = PIPELINE.merge_and_save_bars(target, recovered)
    assert merged["symbol"].tolist() == ["SH600519"]
    assert pd.read_parquet(target)["symbol"].tolist() == ["SH600519"]


def test_merge_and_save_bars_rejects_conflicting_symbol(tmp_path):
    target = tmp_path / "sh600519.parquet"
    conflicting = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-13"]), "symbol": ["SZ000001"],
            "open": [10.0], "high": [10.3], "low": [9.9], "close": [10.1],
            "volume": [100.0], "amount": [101000.0], "vwap": [10.1],
            "change": [0.1], "pct_chg": [1.0], "turnover": [1.0],
        }
    )
    try:
        PIPELINE.merge_and_save_bars(target, conflicting)
    except PIPELINE.PipelineError as exc:
        assert "inconsistent with SH600519" in str(exc)
    else:
        raise AssertionError("conflicting source identity must be rejected")


def test_latest_completed_session_date_avoids_live_and_weekend_bars():
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-13 15:29").to_pydatetime()).isoformat() == "2026-07-10"
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-13 15:30").to_pydatetime()).isoformat() == "2026-07-13"
    assert PIPELINE.latest_completed_session_date(pd.Timestamp("2026-07-12 17:00").to_pydatetime()).isoformat() == "2026-07-10"
    utc_before_close = pd.Timestamp("2026-07-13 07:29", tz="UTC").to_pydatetime()
    utc_at_close = pd.Timestamp("2026-07-13 07:30", tz="UTC").to_pydatetime()
    assert PIPELINE.latest_completed_session_date(utc_before_close).isoformat() == "2026-07-10"
    assert PIPELINE.latest_completed_session_date(utc_at_close).isoformat() == "2026-07-13"


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


def test_point_in_time_prices_chain_close_known_returns_and_restore_raw_prices():
    bars = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"]),
            "symbol": ["SH600519"] * 3,
            "pct_chg": [0.0, 0.0, 10.0],
            "amount": [100000.0, 90000.0, 110000.0],
            "turnover": [1.0, 1.0, 1.0],
            "raw_open": [10.0, 9.0, 9.9],
            "raw_high": [10.2, 9.2, 10.1],
            "raw_low": [9.8, 8.8, 9.8],
            "raw_close": [10.0, 9.0, 9.9],
            "raw_volume": [100.0, 100.0, 100.0],
            "raw_vwap": [10.0, 9.0, 9.9],
            "price_basis": [PIPELINE.POINT_IN_TIME_PRICE_BASIS] * 3,
            "daily_source": ["eastmoney"] * 3,
        }
    )
    adjusted = PIPELINE.rebuild_point_in_time_prices(bars)
    assert adjusted["close"].tolist() == [10.0, 10.0, 11.0]
    assert (adjusted["close"] / adjusted["factor"]).tolist() == [10.0, 9.0, 9.9]
    assert adjusted["vwap"].between(adjusted["low"] - 0.011, adjusted["high"] + 0.011).all()
    assert not any(PIPELINE.price_basis_quality_counts(adjusted).values())


def test_baostock_blank_suspension_return_uses_close_known_preclose():
    source = pd.DataFrame(
        {
            "close": [10.0, 10.0, 11.0],
            "preclose": [None, 10.0, 10.0],
            "pctChg": [None, None, 10.0],
        }
    )
    assert PIPELINE.fill_baostock_pct_chg(source).tolist() == [0.0, 0.0, 10.0]


def test_baostock_unresolvable_noninitial_return_remains_missing():
    source = pd.DataFrame(
        {
            "close": [10.0, 10.5],
            "preclose": [None, None],
            "pctChg": [None, None],
        }
    )
    filled = PIPELINE.fill_baostock_pct_chg(source)
    assert filled.iloc[0] == 0.0
    assert pd.isna(filled.iloc[1])


def test_source_vwap_outside_ohlc_is_preserved_but_quarantined_from_research():
    bars = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01"]),
            "symbol": ["SZ300001"],
            "pct_chg": [0.0],
            "amount": [0.0],
            "turnover": [1.0],
            "raw_open": [10.0],
            "raw_high": [10.1],
            "raw_low": [9.9],
            "raw_close": [10.0],
            "raw_volume": [100.0],
            "raw_vwap": [0.0],
            "price_basis": [PIPELINE.POINT_IN_TIME_PRICE_BASIS],
            "daily_source": ["baostock"],
        }
    )
    adjusted = PIPELINE.rebuild_point_in_time_prices(bars)
    assert adjusted.loc[0, "raw_vwap"] == 0.0
    assert pd.isna(adjusted.loc[0, "vwap"])
    counts = PIPELINE.price_basis_quality_counts(adjusted)
    assert counts["source_vwap_quarantined_rows"] == 1
    assert counts["source_vwap_unquarantined_rows"] == 0


def test_quarantine_vwap_command_rewrites_only_the_research_field(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    metadata_dir = tmp_path / "metadata"
    raw_dir.mkdir()
    bars = pd.DataFrame(
        {
            "raw_low": [9.9],
            "raw_high": [10.1],
            "raw_volume": [100.0],
            "raw_vwap": [0.0],
            "vwap": [0.0],
            "amount": [0.0],
        }
    )
    path = raw_dir / "sz300001.parquet"
    bars.to_parquet(path, index=False)
    monkeypatch.setattr(PIPELINE, "RAW_DIR", raw_dir)
    monkeypatch.setattr(PIPELINE, "METADATA_DIR", metadata_dir)
    monkeypatch.setattr(PIPELINE, "LOCK_PATH", tmp_path / "pipeline.lock")
    assert PIPELINE.run_quarantine_source_vwap(object()) == 0
    repaired = pd.read_parquet(path)
    assert repaired.loc[0, "raw_vwap"] == 0.0
    assert pd.isna(repaired.loc[0, "vwap"])
    assert len(list((metadata_dir / "repairs").glob("*_vwap_quarantine.json"))) == 1


def test_point_in_time_merge_rejects_legacy_mix_but_force_full_replaces_it(tmp_path):
    target = tmp_path / "sh600519.parquet"
    legacy = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-05-29"]), "symbol": ["SH600519"],
            "open": [1.0], "high": [1.1], "low": [0.9], "close": [1.0],
            "volume": [100.0], "amount": [100000.0], "vwap": [10.0],
            "change": [0.0], "pct_chg": [0.0], "turnover": [1.0],
        }
    )
    legacy.to_parquet(target, index=False)
    point_in_time = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01"]), "symbol": ["SH600519"],
            "pct_chg": [0.0], "amount": [100000.0], "turnover": [1.0],
            "raw_open": [10.0], "raw_high": [10.1], "raw_low": [9.9], "raw_close": [10.0],
            "raw_volume": [100.0], "raw_vwap": [10.0],
            "price_basis": [PIPELINE.POINT_IN_TIME_PRICE_BASIS],
            "daily_source": ["eastmoney"],
        }
    )
    point_in_time = PIPELINE.rebuild_point_in_time_prices(point_in_time)
    try:
        PIPELINE.merge_and_save_bars(target, point_in_time)
    except PIPELINE.PipelineError as exc:
        assert "--force-full --adjust point_in_time" in str(exc)
    else:
        raise AssertionError("legacy and point-in-time rows must not be mixed")
    replaced = PIPELINE.merge_and_save_bars(target, point_in_time, replace_existing=True)
    assert replaced["price_basis"].eq(PIPELINE.POINT_IN_TIME_PRICE_BASIS).all()
    assert replaced["factor"].eq(1.0).all()


def test_sync_source_defaults_to_the_single_existing_provider(tmp_path):
    raw_dir = tmp_path / "daily"
    raw_dir.mkdir()
    pd.DataFrame({"daily_source": ["baostock", "baostock"]}).to_parquet(
        raw_dir / "sh600519.parquet",
        index=False,
    )
    assert (
        PIPELINE.resolve_sync_daily_source(
            None,
            force_full=False,
            raw_dir=raw_dir,
        )
        == "baostock"
    )
    assert (
        PIPELINE.resolve_sync_daily_source(
            "baostock",
            force_full=True,
            raw_dir=raw_dir,
        )
        == "baostock"
    )


def test_sync_rejects_an_in_place_provider_switch_even_with_force_full(tmp_path):
    raw_dir = tmp_path / "daily"
    raw_dir.mkdir()
    pd.DataFrame({"daily_source": ["baostock"]}).to_parquet(
        raw_dir / "sh600519.parquet",
        index=False,
    )
    for force_full in (False, True):
        with pytest.raises(
            PIPELINE.PipelineError,
            match="in-place daily source switch",
        ):
            PIPELINE.resolve_sync_daily_source(
                "eastmoney",
                force_full=force_full,
                raw_dir=raw_dir,
            )


def test_incremental_sync_rejects_mixed_or_legacy_source_files(tmp_path):
    raw_dir = tmp_path / "daily"
    raw_dir.mkdir()
    pd.DataFrame({"daily_source": ["baostock"]}).to_parquet(
        raw_dir / "sh600519.parquet",
        index=False,
    )
    pd.DataFrame({"close": [10.0]}).to_parquet(
        raw_dir / "sz000001.parquet",
        index=False,
    )
    with pytest.raises(
        PIPELINE.PipelineError,
        match="requires one valid existing daily source",
    ):
        PIPELINE.resolve_sync_daily_source(
            None,
            force_full=False,
            raw_dir=raw_dir,
        )
    with pytest.raises(
        PIPELINE.PipelineError,
        match="separate clean staging root",
    ):
        PIPELINE.resolve_sync_daily_source(
            "baostock",
            force_full=True,
            raw_dir=raw_dir,
        )


def test_tushare_is_an_accepted_audited_source_but_not_in_place_sync_source(
    tmp_path,
    monkeypatch,
):
    bars = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-24"]),
            "symbol": ["SH600000"],
            "open": [10.0],
            "high": [10.2],
            "low": [9.8],
            "close": [10.1],
            "volume": [1000.0],
            "amount": [1_000_000.0],
            "vwap": [10.0],
            "change": [0.1],
            "pct_chg": [0.0],
            "turnover": [1.0],
            "raw_open": [10.0],
            "raw_high": [10.2],
            "raw_low": [9.8],
            "raw_close": [10.1],
            "raw_volume": [1000.0],
            "raw_vwap": [10.0],
            "price_basis": [PIPELINE.POINT_IN_TIME_PRICE_BASIS],
            "daily_source": ["tushare"],
            "factor": [1.0],
        }
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    bars.to_parquet(raw_dir / "sh600000.parquet", index=False)
    audit = PIPELINE.audit_point_in_time_source(raw_dir=raw_dir)
    assert audit["status"] == "passed"
    assert audit["daily_sources"] == ["tushare"]

    monkeypatch.setattr(
        PIPELINE,
        "resolve_sync_daily_source",
        lambda *args, **kwargs: "tushare",
    )
    monkeypatch.setattr(PIPELINE, "LOCK_PATH", tmp_path / "pipeline.lock")
    with pytest.raises(
        PIPELINE.PipelineError,
        match="active daily root is Tushare",
    ):
        PIPELINE.run_sync(
            SimpleNamespace(
                source=None,
                force_full=False,
            )
        )
