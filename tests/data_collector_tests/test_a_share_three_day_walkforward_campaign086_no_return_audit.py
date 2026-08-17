from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts import a_share_three_day_walkforward_campaign086_no_return_audit as audit


def test_protocol_orders_and_status_are_frozen_without_metrics() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 115
    assert comparisons[-1] == {
        "name": "quarterly_freshness_market_neutral_late_drift_confirmation_product_2r",
        "score_direction": "higher",
    }
    status = audit.status()
    assert status["coverage_or_capacity_metrics_computed"] is False
    assert status["comparison_values_read"] is False
    assert status["historical_daily_price_or_forward_return_values_read"] is False


def test_synthetic_coverage_uses_exact_stock_day_denominator() -> None:
    spec = audit.load_protocol()
    sessions = np.repeat(np.arange(10, 16, dtype=np.int64), 60)
    security = np.tile(np.arange(1, 61, dtype=np.int64), 6)
    keys = sessions * 4_000_000 + security
    values = np.ones(len(keys), dtype=np.float64)
    values[::20] = np.nan
    years = np.full(len(keys), 2021, dtype=np.int64)
    result, finite_keys, finite_values = audit.coverage_and_capacity(
        keys, values, years, spec
    )
    assert result["quality_listing_eligible_rows"] == 360
    assert result["candidate_eligible_rows"] == 342
    assert result["median_coverage"] == 0.95
    assert len(finite_keys) == len(finite_values) == 342
    assert result["gate_passed_before_comparison_values"] is False


def test_audit_freeze_is_live_when_published() -> None:
    if audit.AUDIT_IMPLEMENTATION_FREEZE.is_file():
        record = audit._load_implementation_freeze()
        assert record["comparison_values_read_before_freeze"] is False
        assert Path(record["audit_runner"]["path"]).name == Path(audit.__file__).name
