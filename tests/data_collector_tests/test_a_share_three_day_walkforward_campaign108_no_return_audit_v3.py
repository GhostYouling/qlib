from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign108_no_return_audit_v3 as audit


def test_recovery_changes_only_candidate_loader_range_hook() -> None:
    assert audit._candidate_import_old not in audit._source
    assert audit._candidate_import_new in audit._source
    assert audit._range_old not in audit._source
    assert audit._source.count(audit._range_new) == 1


def test_recovery_freeze_and_activation_are_live() -> None:
    freeze = audit._validate_audit_recovery_freeze()
    assert freeze["scientific_boundary"]["only_change"] == (
        "candidate loader validation range (0,1) to (-1,1)"
    )
    activation = audit._load_activation_binding()
    assert activation["single_use"] is True
    assert activation["candidate_snapshot"]["dataset_sha256"] == (
        "da56afa190e7721f2e94fa124c747d54ec3d54eeeb717954e5ae6dcb56c0a3b2"
    )
