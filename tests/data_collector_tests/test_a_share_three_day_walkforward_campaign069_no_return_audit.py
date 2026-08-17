from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign069_no_return_audit as audit


def test_campaign069_complete_definition_and_numeric_orders_are_bound() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 99
    assert comparisons[-1] == {
        "name": "quarterly_profit_revenue_acceleration_rank_gap_2r",
        "score_direction": "higher",
    }
    assert audit.candidate._comparison_order_digest(comparisons) == (
        audit.EXPECTED_COMPARISON_ORDER_SHA256
    )


def test_campaign069_loader_refuses_failed_coverage_before_either_source() -> None:
    with pytest.raises(
        audit.Campaign069NoReturnAuditError,
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


def test_campaign069_signed_candidate_range_is_installed_without_values() -> None:
    class Engine:
        FACTOR_RANGES = {"existing": (0.0, 1.0)}

    engine = Engine()
    audit._install_frozen_candidate_range(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (-1.0, 1.0)


def test_campaign069_status_is_read_only_across_lifecycle() -> None:
    payload = audit.status()
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False


def test_campaign069_audit_implementation_freeze_binds_runner_and_tests() -> None:
    freeze = json.loads(audit.AUDIT_IMPLEMENTATION_FREEZE.read_text())
    assert freeze["audit_runner"]["sha256"] == audit._sha256(
        audit.Path(audit.__file__)
    )
    assert freeze["tests"]["sha256"] == audit._sha256(audit.TEST_PATH)
    assert freeze["candidate_snapshot_existed_before_freeze"] is False
    assert freeze["coverage_or_capacity_metrics_computed_before_freeze"] is False
    assert freeze["comparison_values_read_before_freeze"] is False
    assert freeze["historical_daily_price_fields_read_before_freeze"] == []
    assert freeze["historical_forward_returns_read_before_freeze"] is False
    assert freeze["io_semantics"]["both_comparator_loaders_are_coverage_guarded"] is True
