from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import a_share_three_day_walkforward_campaign106_no_return_audit_recovery_v2 as recovery


def test_range_registration_adds_only_frozen_campaign105_domain() -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"old": (-1.0, 1.0)})
    recovery._register_campaign105_range(engine)
    assert engine.FACTOR_RANGES == {
        "old": (-1.0, 1.0),
        recovery.c105.FACTOR_NAME: (0.0, 1.0),
    }


def test_conflicting_existing_range_fails_closed() -> None:
    engine = SimpleNamespace(
        FACTOR_RANGES={recovery.c105.FACTOR_NAME: (-1.0, 1.0)}
    )
    with pytest.raises(recovery.Campaign106NoReturnAuditRecoveryError, match="conflicts"):
        recovery._register_campaign105_range(engine)


def test_comparator_loader_still_requires_coverage_pass() -> None:
    with pytest.raises(recovery.Campaign106NoReturnAuditRecoveryError, match="before"):
        recovery._recovery_comparison_loader(
            coverage={"gate_passed_before_comparison_values": False}
        )


def test_recovery_requires_explicit_confirmation(tmp_path) -> None:
    with pytest.raises(recovery.Campaign106NoReturnAuditRecoveryError, match="confirm-run"):
        recovery.run_recovery(
            data_root=recovery.base.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )


def test_recovery_activation_is_live() -> None:
    record = recovery._load_recovery_activation()
    assert record["single_recovery_attempt"] is True

