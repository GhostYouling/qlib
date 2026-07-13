"""Offline tests for the low-resource Alpha158 aggregation pilot."""

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_a_share_alpha158_pilot.py"
SPEC = importlib.util.spec_from_file_location("a_share_alpha158_pilot", SCRIPT_PATH)
PILOT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = PILOT
SPEC.loader.exec_module(PILOT)


def test_calendar_splits_are_contiguous():
    calendar = pd.date_range("2024-01-01", periods=200, freq="B")
    splits = PILOT.calendar_splits(calendar, 40)
    assert splits["train"][0] == calendar[0]
    assert splits["train"][1] < splits["valid"][0] < splits["valid"][1] < splits["test"][0]
    assert splits["test"][1] == calendar[-1]


def test_load_buyable_samples_requires_passed_report(tmp_path):
    report = tmp_path / "readiness.json"
    report.write_text(
        json.dumps(
            {
                "status": "passed",
                "sample": {"by_board": {"main": ["SH600000", "SH600001", "SH600002"], "chinext": ["SZ300001", "SZ300002", "SZ300003"]}},
            }
        ),
        encoding="utf-8",
    )
    assert PILOT.load_buyable_samples(report) == ["SH600000", "SH600001", "SH600002", "SZ300001", "SZ300002", "SZ300003"]
    report.write_text(json.dumps({"status": "failed"}), encoding="utf-8")
    with pytest.raises(ValueError, match="not passed"):
        PILOT.load_buyable_samples(report)
