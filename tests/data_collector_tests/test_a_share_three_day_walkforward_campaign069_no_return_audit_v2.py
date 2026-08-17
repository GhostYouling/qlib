from __future__ import annotations

import json

from scripts import a_share_three_day_walkforward_campaign069_no_return_audit_v2 as repair


def test_campaign069_v2_protocol_freezes_only_range_registration_repair() -> None:
    spec = repair.load_repair_protocol()
    assert spec["sole_repair"]["install_candidate_range"]["range"] == [-1.0, 1.0]
    assert spec["sole_repair"]["install_campaign068_comparator_range"] == {
        "factor": "quarterly_profit_revenue_acceleration_rank_gap_2r",
        "range": [-1.0, 1.0],
    }
    assert spec["sole_repair"]["delegate_all_other_behavior_to_immutable_v1_runner"] is True
    assert spec["unchanged_semantics"]["coverage_gates_changed"] is False
    assert spec["unchanged_semantics"]["uniqueness_gates_changed"] is False


def test_campaign069_v2_installs_both_signed_ranges() -> None:
    class Engine:
        FACTOR_RANGES = {"existing": (0.0, 1.0)}

    engine = Engine()
    repair.install_repaired_ranges(engine)
    assert engine.FACTOR_RANGES[repair.v1.FACTOR_NAME] == (-1.0, 1.0)
    assert engine.FACTOR_RANGES[repair.v1.candidate.C68_FACTOR] == (-1.0, 1.0)


def test_campaign069_v2_status_is_read_only() -> None:
    payload = repair.status()
    assert payload["v1_failure_preserved"] is True
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False


def test_campaign069_v2_implementation_freeze_binds_runner_and_tests() -> None:
    record = json.loads(repair.IMPLEMENTATION_FREEZE.read_text())
    assert record["v2_runner"]["sha256"] == repair._sha256(
        repair.Path(repair.__file__)
    )
    assert record["tests"]["sha256"] == repair._sha256(repair.TEST_PATH)
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False
