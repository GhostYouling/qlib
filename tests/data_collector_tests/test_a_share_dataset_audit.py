"""Offline tests for the full A-share data-set audit helpers."""

import importlib.util
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
