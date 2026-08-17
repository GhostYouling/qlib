from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign076_no_return_audit_v2 as v2


def test_repair_protocol_changes_only_timestamp_binding() -> None:
    spec = v2.load_repair_protocol()
    sole = spec["sole_repair"]
    assert sole["candidate_formula_changed"] is False
    assert sole["coverage_gate_changed"] is False
    assert sole["comparison_library_or_order_changed"] is False
    assert sole["uniqueness_threshold_changed"] is False
    assert sole["snapshot_or_manifest_rewritten"] is False
    assert spec["retry"]["partial_statistics_reused"] is False


def test_temporary_timestamp_binding_is_installed_and_restored() -> None:
    target, provider = v2._timestamp_target_and_provider()
    assert not hasattr(target, "research")
    with v2._temporary_timestamp_binding():
        assert target.research is provider
        assert callable(target.research._timestamp)
    assert not hasattr(target, "research")


def test_v1_frozen_runner_and_empty_audit_state_preserved() -> None:
    assert v2._sha256(v2.v1.Path(v2.v1.__file__).resolve()) == "a9371fbfeaf48163a41768c8300fec6f944e8a4e14ef04f20eb58853ad2a2d9d"
    assert v2.v1.status()["audit_count"] == 0
    assert v2.v1.status()["historical_forward_return_fields_read"] is False
