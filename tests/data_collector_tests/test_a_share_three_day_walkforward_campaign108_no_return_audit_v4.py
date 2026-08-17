from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign108_no_return_audit_v4 as audit


def test_range_recovery_is_injected_at_campaign105_source_generation_depth() -> None:
    assert audit._candidate_import_old not in audit._source
    assert audit._candidate_import_new in audit._source
    assert audit._source.count(audit._generation_hook) == 1
    assert audit._source.count(
        f'_source = _source.replace("{audit._range_old}", "{audit._range_new}")'
    ) == 1


def test_generated_audit_contains_exact_recovered_loader_range() -> None:
    assert audit._range_old not in audit._generated_audit_source
    assert audit._generated_audit_source.count(audit._range_new) == 1
    assert audit._impl["candidate"].FACTOR_NAME == audit.FACTOR_NAME
    assert audit.AUDIT_ACTIVATION_BINDING == audit.RECOVERY_ACTIVATION_BINDING


def test_recovery_freeze_and_activation_are_live() -> None:
    freeze = audit._validate_audit_recovery_freeze()
    assert freeze["scientific_boundary"]["only_change"].startswith("inject candidate")
    activation = audit._load_activation_binding()
    assert activation["single_use"] is True
    assert activation["candidate_snapshot"]["dataset_sha256"] == (
        "da56afa190e7721f2e94fa124c747d54ec3d54eeeb717954e5ae6dcb56c0a3b2"
    )
