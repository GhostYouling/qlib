from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign146_no_return_audit as c146


def test_campaign146_no_return_protocol_and_gate_order_are_bound() -> None:
    spec = c146.load_protocol()
    assert [item["gate"] for item in spec["ordered_no_return_gates"]] == [1, 2, 3]
    assert spec["comparison_contract"]["numeric_comparator_count"] == 141
    assert c146.candidate.FACTOR_NAME == c146.FACTOR_NAME


def test_campaign146_coverage_gate_is_exact() -> None:
    assert c146.expected_gate() == {
        "holding_period_sessions": 3,
        "minimum_median_daily_coverage": 0.95,
        "minimum_p05_daily_coverage": 0.9,
        "minimum_p05_eligible_names": 50,
        "minimum_non_overlapping_three_signal_session_cohorts": 200,
        "minimum_observed_cohort_years": 5,
        "minimum_nonconstant_cross_sectional_sessions": 200,
        "cross_sectional_distinctness": "exact finite float values without rounding tolerance or binning",
    }


def _frames(value: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range("2021-01-04", periods=9, freq="B")
    symbols = [f"SZ{i:06d}" for i in range(50)]
    keys = pd.MultiIndex.from_product(
        [dates, symbols], names=["trade_date", "symbol"]
    ).to_frame(index=False)
    candidate = keys.copy()
    candidate[c146.FACTOR_NAME] = value + np.tile(
        np.linspace(0.0, 0.01, len(symbols)), len(dates)
    )
    candidate[f"{c146.FACTOR_NAME}_eligible"] = True
    return candidate, keys


def test_campaign146_coverage_accepts_finite_negative_scores() -> None:
    candidate, keys = _frames(-0.5)
    result = c146.coverage_and_variation(candidate, keys)
    assert result["median_daily_coverage"] == 1.0
    assert result["p05_daily_coverage"] == 1.0
    assert result["nonconstant_cross_sectional_sessions"] == 9


def test_campaign146_coverage_rejects_out_of_range_score() -> None:
    candidate, keys = _frames(-0.5)
    candidate.loc[0, c146.FACTOR_NAME] = -1.01
    with pytest.raises(c146.Campaign146NoReturnAuditError):
        c146.coverage_and_variation(candidate, keys)


def test_campaign146_paths_and_candidate49_ledgers_are_bound() -> None:
    assert "campaign_146" in str(c146.OUTPUT_PATH)
    assert "campaign_146" in str(c146.ACTIVATION_BINDING_PATH)
    assert "campaign146" in str(c146.SNAPSHOT_MANIFEST_PATH)
    assert c146.CANDIDATE49_SIGNAL_LEDGER_SHA256 == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert c146.CANDIDATE49_EXECUTION_LEDGER_SHA256 == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
