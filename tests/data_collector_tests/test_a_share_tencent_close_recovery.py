"""Offline checks for the audited Tencent close fallback parser."""

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "recover_a_share_close_from_tencent.py"
SPEC = importlib.util.spec_from_file_location("a_share_tencent_close_recovery", SCRIPT_PATH)
RECOVERY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RECOVERY
SPEC.loader.exec_module(RECOVERY)


def _quote(timestamp="20260713160419"):
    values = [""] * 40
    values[3] = "9.19"
    values[4] = "9.06"
    values[5] = "9.04"
    values[6] = "757620"
    values[30] = timestamp
    values[32] = "1.43"
    values[33] = "9.21"
    values[34] = "9.01"
    values[35] = "9.19/757620/693325381"
    values[38] = "0.23"
    return "~".join(values)


def test_parse_quote_line_normalizes_daily_bar():
    bar = RECOVERY.parse_quote_line("sh600000", _quote(), RECOVERY.dt.date(2026, 7, 13))
    assert bar is not None
    assert bar["close"] == 9.19
    assert bar["amount"] == 693325381.0
    assert round(bar["vwap"], 4) == round(693325381 / (757620 * 100), 4)


def test_parse_quote_line_rejects_stale_quote():
    assert RECOVERY.parse_quote_line("sh600000", _quote("20260710150000"), RECOVERY.dt.date(2026, 7, 13)) is None


def test_parse_quote_line_rejects_missing_amount():
    invalid = _quote().replace("9.19/757620/693325381", "")
    with pytest.raises(ValueError, match="missing amount"):
        RECOVERY.parse_quote_line("sh600000", invalid, RECOVERY.dt.date(2026, 7, 13))


def test_recovery_bar_is_written_with_canonical_symbol(monkeypatch, tmp_path):
    quote = RECOVERY.parse_quote_line("sh600000", _quote(), RECOVERY.dt.date(2026, 7, 13))
    assert quote is not None
    universe = [
        {
            "symbol": "SH600000", "code": "600000", "name": "测试", "board": "main",
            "listing_date": None, "market_cap": None, "float_market_cap": None, "is_st": False,
        }
    ]
    snapshot = tmp_path / "universe.json"
    snapshot.write_text(__import__("json").dumps(universe), encoding="utf-8")
    captured = {}
    monkeypatch.setattr(RECOVERY, "UNIVERSE_PATH", snapshot)
    monkeypatch.setattr(RECOVERY, "PipelineLock", lambda _: _NoopLock())
    monkeypatch.setattr(RECOVERY, "fetch_quotes", lambda *_: ({"sh600000": quote}, {}))
    monkeypatch.setattr(RECOVERY, "materialize_qlib", lambda *_: {})
    monkeypatch.setattr(RECOVERY, "_atomic_write_json", lambda *_: None)
    monkeypatch.setattr(RECOVERY, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(RECOVERY, "RECOVERY_DIR", tmp_path / "recoveries")
    monkeypatch.setattr(RECOVERY, "METADATA_DIR", tmp_path / "metadata")
    def capture_merge(_path, bar, **_kwargs):
        captured["symbol"] = bar.loc[0, "symbol"]
    monkeypatch.setattr(RECOVERY, "merge_and_save_bars", capture_merge)
    RECOVERY.run_recovery(RECOVERY.dt.date(2026, 7, 13), batch_size=1, dump_workers=1)
    assert captured["symbol"] == "SH600000"


class _NoopLock:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None
