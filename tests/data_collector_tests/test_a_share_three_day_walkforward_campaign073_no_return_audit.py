from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign073_no_return_audit as audit


def test_campaign073_complete_and_numeric_orders_are_frozen() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 103
    assert comparisons[-5:] == [
        {
            "name": "quarterly_profit_revenue_acceleration_rank_gap_2r",
            "score_direction": "higher",
        },
        {
            "name": "quarterly_profit_growth_roe_transition_gap_2r",
            "score_direction": "higher",
        },
        {
            "name": "quarterly_announcement_delay_improvement_yoy_rank_1y",
            "score_direction": "higher",
        },
        {"name": "quarterly_net_profit_scale_rank", "score_direction": "higher"},
        {
            "name": "quarterly_joint_profit_revenue_growth_floor_rank",
            "score_direction": "higher",
        },
    ]
    complete = audit.candidate.reconstruct_complete_definitions()
    assert len(complete) == 104
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in complete]


def test_campaign073_comparison_loader_refuses_failed_coverage() -> None:
    with pytest.raises(
        audit.Campaign073NoReturnAuditError,
        match="forbidden before all coverage gates pass",
    ):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([], dtype=np.int64),
            candidate_values=np.array([], dtype=np.float64),
            gate={},
            engine=object(),
            comparison_engine=object(),
            workers=1,
        )


def test_campaign073_installs_all_frozen_ranges() -> None:
    class Engine:
        FACTOR_RANGES = {"existing": (0.0, 1.0)}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C68_FACTOR] == (-1.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C69_FACTOR] == (-1.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C70_FACTOR] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C71_FACTOR] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C72_FACTOR] == (0.0, 1.0)


def test_campaign073_comparator_sorter_preserves_missing_values() -> None:
    class ComparisonEngine:
        @staticmethod
        def _compact_stock_day_keys(dates, symbols):
            del dates
            return (
                np.array([2, 1], dtype=np.int64)
                if list(symbols) == ["B", "A"]
                else None
            )

    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
            "symbol": ["B", "A"],
            "factor": [np.nan, 0.25],
        }
    )
    keys, values = audit._sorted_comparator_arrays(
        frame, "factor", ComparisonEngine()
    )
    assert keys.tolist() == [1, 2]
    assert values[0] == 0.25
    assert np.isnan(values[1])


def test_campaign073_status_is_read_only() -> None:
    payload = audit.status()
    assert payload["coverage_or_capacity_metrics_computed_by_status"] is False
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False


def test_campaign073_audit_freeze_binds_runner_and_tests() -> None:
    record = json.loads(audit.AUDIT_IMPLEMENTATION_FREEZE.read_text())
    assert record["audit_runner"]["sha256"] == audit._sha256(
        audit.Path(audit.__file__)
    )
    assert record["tests"]["sha256"] == audit._sha256(audit.TEST_PATH)
    assert record["coverage_or_capacity_metrics_computed_before_freeze"] is False
    assert record["comparison_values_read_before_freeze"] is False
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False
