from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign152_no_return_audit as audit


def _frames(
    *, sessions: int = 700, names: int = 60
) -> tuple[pd.DataFrame, pd.DataFrame]:
    full_calendar = pd.bdate_range("2019-01-02", "2025-12-30")
    positions = np.linspace(0, len(full_calendar) - 1, sessions, dtype=int)
    dates = full_calendar[positions]
    rows = []
    for date_index, date in enumerate(dates):
        for name_index in range(names):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": f"SH{name_index:06d}",
                    audit.FACTOR_NAME: 10.0 + date_index / 1000 + name_index / 100,
                    f"{audit.FACTOR_NAME}_eligible": True,
                }
            )
    candidate = pd.DataFrame(rows)
    return candidate, candidate[["trade_date", "symbol"]].copy()


def test_protocol_and_gate_are_exact() -> None:
    spec = audit.load_protocol()
    assert spec["comparison_contract"]["numeric_comparator_count"] == 142
    assert (
        audit.expected_gate()["minimum_non_overlapping_three_signal_session_cohorts"]
        == 200
    )


def test_coverage_accepts_positive_unbounded_candidate_values() -> None:
    candidate, keys = _frames()
    result = audit.coverage_and_variation(candidate, keys)
    assert result["coverage_capacity_gate_passed"] is True
    assert result["cross_sectional_variation_gate_passed"] is True
    assert result["gate_passed_before_comparator_values"] is True
    assert result["candidate_eligible_rows"] == len(candidate)


def test_constant_cross_sections_fail_variation_only() -> None:
    candidate, keys = _frames()
    candidate[audit.FACTOR_NAME] = 12.0
    result = audit.coverage_and_variation(candidate, keys)
    assert result["coverage_capacity_gate_passed"] is True
    assert result["cross_sectional_variation_gate_passed"] is False


def test_missing_rows_fail_coverage_without_comparator_or_return() -> None:
    candidate, keys = _frames()
    mask = np.arange(len(candidate)) % 2 == 0
    candidate.loc[mask, audit.FACTOR_NAME] = np.nan
    candidate.loc[mask, f"{audit.FACTOR_NAME}_eligible"] = False
    result = audit.coverage_and_variation(candidate, keys)
    assert result["coverage_capacity_gate_passed"] is False
    assert result["gate_passed_before_comparator_values"] is False


def test_daily_hash_is_deterministic() -> None:
    candidate, keys = _frames()
    first = audit.coverage_and_variation(candidate, keys)
    second = audit.coverage_and_variation(candidate, keys)
    assert (
        first["daily_aggregate_frame_sha256"] == second["daily_aggregate_frame_sha256"]
    )
