from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign077_no_return_audit_v2 as v2


def test_repair_protocol_and_failure_record_are_live() -> None:
    spec = v2.load_repair_protocol()
    assert spec["retry"]["partial_statistics_reused"] is False
    assert spec["retry"]["restart_from_candidate_snapshot_verification_and_coverage"] is True
    assert spec["sole_repair"]["comparison_library_or_order_changed"] is False
    assert spec["sole_repair"]["historical_daily_price_or_return_field_changed"] is False


def test_runtime_binding_changes_only_expected_version_constants_and_restores() -> None:
    module = v2._legacy_verifier_module()
    before = (module.PANDAS_VERSION, module.PYARROW_VERSION)
    with v2._temporary_runtime_version_binding():
        assert module.PANDAS_VERSION == module.pd.__version__ == "2.2.2"
        assert module.PYARROW_VERSION == module.pyarrow.__version__ == "16.1.0"
    assert (module.PANDAS_VERSION, module.PYARROW_VERSION) == before == (
        "2.2.3",
        "25.0.0",
    )


def test_v2_pre_retry_status_is_zero_audits_and_no_returns() -> None:
    status = v2.v1.status()
    assert status["audit_count"] == 0
    assert status["historical_daily_price_fields_read"] == []
    assert status["historical_forward_return_fields_read"] is False
    assert status["provider_request_issued"] is False


def test_v2_implementation_freeze_is_live() -> None:
    freeze = v2._load_implementation_freeze()
    assert freeze["partial_statistics_reused"] is False
    assert freeze["candidate_snapshot_or_manifest_rewritten"] is False
