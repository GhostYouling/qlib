from __future__ import annotations

import pytest

from scripts import a_share_three_day_walkforward_campaign083_no_return_audit_v2 as v2


def test_repair_protocol_preserves_every_research_gate() -> None:
    spec = v2.load_repair_protocol()
    assert spec["retry"]["partial_statistics_reused"] is False
    assert spec["retry"]["maximum_authorized_v2_retries"] == 1
    assert (
        spec["runtime_transition"][
            "runtime_gate_suppression_monkey_patch_or_constant_rebinding_allowed"
        ]
        is False
    )
    assert (
        spec["sole_repair"][
            "all_112_comparators_still_required_in_frozen_order_after_coverage_pass"
        ]
        is True
    )


def test_runtime_gate_fails_closed_until_exact_versions_are_installed() -> None:
    observed = v2.runtime_versions()
    required = {
        "pandas": v2.REQUIRED_PANDAS_VERSION,
        "pyarrow": v2.REQUIRED_PYARROW_VERSION,
    }
    if observed == required:
        assert v2.require_exact_runtime() == required
    else:
        with pytest.raises(v2.Campaign083NoReturnAuditV2Error):
            v2.require_exact_runtime()


def test_zero_audit_status_and_no_value_boundary() -> None:
    status = v2.v1.status()
    assert status["audit_count"] == 0
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_daily_price_fields_read"] == []
    assert status["historical_forward_return_fields_read"] is False


def test_v2_implementation_freeze_is_live_when_published() -> None:
    if v2.IMPLEMENTATION_FREEZE.is_file():
        freeze = v2._load_implementation_freeze()
        assert freeze["runtime_gate_suppressed_or_monkey_patched"] is False
        assert freeze["partial_statistics_reused"] is False
