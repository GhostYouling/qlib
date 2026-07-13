"""Offline tests for the full A-share data-set audit helpers."""

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_a_share_dataset.py"
SPEC = importlib.util.spec_from_file_location("a_share_dataset_audit", SCRIPT_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def test_evenly_spaced_is_deterministic():
    assert AUDIT.evenly_spaced(["a", "b", "c", "d", "e"], 3) == ["a", "c", "e"]
    assert AUDIT.evenly_spaced(["a", "b"], 5) == ["a", "b"]
    assert AUDIT.evenly_spaced(["a", "b"], 0) == []


def test_read_instrument_ranges_rejects_duplicates_and_keeps_dates(tmp_path):
    path = tmp_path / "all.txt"
    path.write_text("SH600000\t2024-01-01\t2024-12-31\nSZ300001\t2024-01-01\t2024-12-31\n", encoding="utf-8")
    ranges = AUDIT.read_instrument_ranges(path)
    assert ranges["SH600000"] == (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"))


def test_temporal_universe_audit_preserves_terminal_ranges_and_listing_boundaries(tmp_path):
    snapshot = tmp_path / "universe_latest.json"
    snapshot.write_text(
        json.dumps(
            [
                {"symbol": "SH600000", "listing_date": "2019-01-01"},
                {"symbol": "SZ300001", "listing_date": "2020-01-02"},
            ]
        ),
        encoding="utf-8",
    )
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]))
    ranges = {
        "SH600000": (pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-06")),
        "SZ300001": (pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")),
    }
    summary, errors, limitations = AUDIT.audit_temporal_universe_coverage(
        snapshot, calendar, ranges, ranges, ranges
    )
    assert not errors
    assert summary["status"] == "passed"
    assert summary["terminal_range_count"] == 1
    assert summary["terminal_buyable_range_count"] == 1
    assert summary["pre_listing_range_count"] == 0
    assert limitations


def test_temporal_universe_audit_rejects_pre_listing_trade_ranges(tmp_path):
    snapshot = tmp_path / "universe_latest.json"
    snapshot.write_text(json.dumps([{"symbol": "SH600000", "listing_date": "2020-01-03"}]), encoding="utf-8")
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03"]))
    ranges = {"SH600000": (pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03"))}
    summary, errors, _ = AUDIT.audit_temporal_universe_coverage(snapshot, calendar, ranges, ranges, ranges)
    assert summary["status"] == "failed"
    assert summary["pre_listing_range_count"] == 1
    assert errors == ["1 retained instruments start before their listed date"]


def test_temporal_universe_audit_reports_snapshot_symbols_without_daily_bars_as_limitation(tmp_path):
    snapshot = tmp_path / "universe_latest.json"
    snapshot.write_text(
        json.dumps(
            [
                {"symbol": "SH600000", "listing_date": "2019-01-01"},
                {"symbol": "SZ000001", "listing_date": "2019-01-01"},
            ]
        ),
        encoding="utf-8",
    )
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03"]))
    ranges = {"SH600000": (pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03"))}
    summary, errors, limitations = AUDIT.audit_temporal_universe_coverage(snapshot, calendar, ranges, ranges, ranges)
    assert not errors
    assert summary["status"] == "passed"
    assert summary["snapshot_without_daily_bar_count"] == 1
    assert summary["snapshot_without_daily_bar_examples"] == ["SZ000001"]
    assert any("without retained daily bars" in item for item in limitations)
