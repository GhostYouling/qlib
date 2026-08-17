from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign120_no_return_audit as audit


def _synthetic_panel(
    *, sessions: int = 756, names: int = 60
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2019-01-02", periods=sessions)
    symbols = [f"SZ{index:06d}" for index in range(names)]
    keys = pd.MultiIndex.from_product(
        [dates, symbols], names=["trade_date", "symbol"]
    ).to_frame(index=False)
    ordinal = np.tile(np.arange(names, dtype=int), sessions)
    candidate = keys.copy()
    candidate[audit.FACTOR_NAME] = (ordinal % 60 + 2).astype(float)
    candidate[f"{audit.FACTOR_NAME}_eligible"] = True
    return candidate, keys


def test_campaign120_gate_and_protocol_are_frozen() -> None:
    spec = audit.load_protocol()
    assert spec["candidate"]["name"] == audit.FACTOR_NAME
    gate = audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_p05_daily_coverage"] == 0.90
    assert gate["minimum_nonconstant_cross_sectional_sessions"] == 200


def test_campaign120_synthetic_panel_passes_coverage_and_variation() -> None:
    candidate, keys = _synthetic_panel(sessions=1300)
    result = audit.coverage_and_variation(candidate, keys)
    assert result["median_daily_coverage"] == 1.0
    assert result["p05_daily_coverage"] == 1.0
    assert result["eligible_names_p05"] == 60.0
    assert result["gate_passed_before_comparator_values"] is True


def test_campaign120_constant_cross_section_fails_variation_only() -> None:
    candidate, keys = _synthetic_panel(sessions=1300)
    candidate[audit.FACTOR_NAME] = 20.0
    result = audit.coverage_and_variation(candidate, keys)
    assert result["coverage_capacity_gate_passed"] is True
    assert result["cross_sectional_variation_gate_passed"] is False
    assert result["gate_passed_before_comparator_values"] is False


def test_campaign120_invalid_or_undeclared_values_fail_closed() -> None:
    for invalid in (1.0, 2.5, 239.0):
        candidate, keys = _synthetic_panel(sessions=10)
        candidate.loc[0, audit.FACTOR_NAME] = invalid
        with pytest.raises(audit.Campaign120NoReturnAuditError):
            audit.coverage_and_variation(candidate, keys)

    candidate, keys = _synthetic_panel(sessions=10)
    candidate.loc[0, f"{audit.FACTOR_NAME}_eligible"] = False
    with pytest.raises(audit.Campaign120NoReturnAuditError):
        audit.coverage_and_variation(candidate, keys)
