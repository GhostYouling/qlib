"""Tests for fail-closed walk-forward reporting semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPORTING_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "a_share_three_day_walkforward_reporting.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a_share_three_day_walkforward_reporting",
    REPORTING_PATH,
)
assert SPEC and SPEC.loader
REPORTING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORTING)


def _entry(feature_set, *, kind="single_factor"):
    return {
        "feature_set": feature_set,
        "window_transform_threshold_filter_and_weight_configuration": {
            "kind": kind,
        },
    }


def test_single_factor_complexity_replaces_inherited_display_error():
    inherited = {"development_survivor_gate_passed": False, "complexity": 2}

    repaired = REPORTING.with_canonical_complexity(
        inherited,
        _entry(["intraday_example_240m"]),
    )

    assert repaired == {
        "development_survivor_gate_passed": False,
        "complexity": 1,
    }
    assert inherited["complexity"] == 2


def test_multi_factor_complexity_is_exact_feature_count():
    assert (
        REPORTING.canonical_feature_complexity(
            _entry(["factor_a", "factor_b", "factor_c"], kind="fixed_combination")
        )
        == 3
    )


@pytest.mark.parametrize(
    "entry",
    [
        {},
        _entry([]),
        _entry([""]),
        _entry(["factor_a", "factor_a"], kind="fixed_combination"),
        _entry(["factor_a", "factor_b"]),
    ],
)
def test_ambiguous_feature_sets_fail_closed(entry):
    with pytest.raises(REPORTING.WalkForwardReportingError):
        REPORTING.canonical_feature_complexity(entry)
