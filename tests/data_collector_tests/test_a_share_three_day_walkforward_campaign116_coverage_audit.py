from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign116_coverage_audit as audit


def _synthetic_frames(*, variation_sessions: int = 100):
    dates = pd.DatetimeIndex([])
    for year in range(2019, 2024):
        dates = dates.append(pd.bdate_range(f"{year}-01-02", periods=121))
    symbols = [f"sh{index:06d}" for index in range(60)]
    eligible_rows = []
    candidate_rows = []
    for date_index, date in enumerate(dates):
        for symbol_index, symbol in enumerate(symbols):
            eligible_rows.append({"trade_date": date, "symbol": symbol})
            value = float(symbol_index % 2) if date_index < variation_sessions else 0.0
            candidate_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    audit.FACTOR_NAME: value,
                    f"{audit.FACTOR_NAME}_eligible": True,
                }
            )
    return pd.DataFrame(candidate_rows), pd.DataFrame(eligible_rows)


def test_coverage_and_variation_passes_exact_frozen_gates():
    candidate, eligible = _synthetic_frames(variation_sessions=100)
    result = audit.coverage_and_variation(candidate, eligible)

    assert result["median_daily_coverage"] == 1.0
    assert result["p05_daily_coverage"] == 1.0
    assert result["eligible_names_p05"] == 60.0
    assert result["potential_non_overlapping_three_signal_session_cohorts"] >= 200
    assert result["observed_cohort_years"] == [2019, 2020, 2021, 2022, 2023]
    assert result["nonconstant_cross_sectional_sessions"] == 100
    assert result["gate_passed_before_comparator_values"] is True


def test_exactly_constant_cross_sections_fail_before_comparators():
    candidate, eligible = _synthetic_frames(variation_sessions=0)
    result = audit.coverage_and_variation(candidate, eligible)

    assert result["coverage_capacity_gate_passed"] is True
    assert result["cross_sectional_variation_gate_passed"] is False
    assert result["gate_passed_before_comparator_values"] is False


def test_declared_missing_values_reduce_coverage_and_fail_closed():
    candidate, eligible = _synthetic_frames(variation_sessions=100)
    candidate.loc[
        candidate["symbol"].isin(candidate["symbol"].unique()[:20]),
        f"{audit.FACTOR_NAME}_eligible",
    ] = False
    candidate.loc[~candidate[f"{audit.FACTOR_NAME}_eligible"], audit.FACTOR_NAME] = (
        float("nan")
    )
    result = audit.coverage_and_variation(candidate, eligible)

    assert result["median_daily_coverage"] == 2.0 / 3.0
    assert result["coverage_capacity_gate_passed"] is False
    assert result["gate_passed_before_comparator_values"] is False


def test_plan_function_does_not_open_candidate_values(monkeypatch, tmp_path):
    monkeypatch.setattr(
        audit,
        "validate_static_bindings",
        lambda: {
            "candidate_values_read": False,
            "comparator_values_read": False,
        },
    )
    monkeypatch.setattr(
        audit,
        "_load_candidate_frame",
        lambda: (_ for _ in ()).throw(AssertionError("candidate values opened")),
    )

    result = audit.build_plan(tmp_path / "absent.json")

    assert result["ready"] is True
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
