from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign117_ordered_uniqueness_recovery as recovery,
)


def test_campaign117_adapter_recovery_accepts_only_current_skill_drift() -> None:
    record = recovery.adapter_recovery.validate_contract()
    assert record["kind"] == (
        "a_share_three_day_walkforward_campaign107_raw_comparator_adapter_contract"
    )
    assert recovery.base.c110_v1.adapter.validate_contract is (
        recovery.adapter_recovery.validate_contract
    )


def test_campaign117_recovered_base_plan_is_value_blind_and_ready() -> None:
    plan = recovery.base.build_plan()
    assert plan["ready"] is True
    assert plan["comparison_count"] == 134
    assert plan["comparator_values_read"] is False
    assert plan["historical_daily_price_or_forward_return_values_read"] is False
