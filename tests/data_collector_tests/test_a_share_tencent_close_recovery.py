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
