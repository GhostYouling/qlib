"""Offline unit tests for the A-share factor-readiness validator."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_a_share_factor_readiness.py"
SPEC = importlib.util.spec_from_file_location("a_share_factor_readiness", SCRIPT_PATH)
READINESS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = READINESS
SPEC.loader.exec_module(READINESS)


def test_board_classification_and_deterministic_sampling():
    assert READINESS.classify_board("SH600519") == "main"
    assert READINESS.classify_board("SZ300750") == "chinext"
    assert READINESS.classify_board("SH688981") == "star"
    assert READINESS.classify_board("BJ430047") is None
    assert READINESS.evenly_spaced(["a", "b", "c", "d", "e"], 3) == ["a", "c", "e"]


def test_select_full_window_sample_requires_complete_history():
    start, end = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31")
    spans = {
        "SH600000": [(start, end)],
        "SZ300001": [(start, end)],
        "SH688001": [(start, end)],
        "SH600001": [(pd.Timestamp("2024-06-01"), end)],
    }
    selected, by_board = READINESS.select_full_window_sample(spans, start, end, 1)
    assert selected == ["SH600000", "SH688001", "SZ300001"]
    assert by_board == {"main": ["SH600000"], "chinext": ["SZ300001"], "star": ["SH688001"]}
