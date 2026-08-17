from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign102_development_recovery as recovery,
)


def test_failed_predata_state_is_exact_and_has_no_complete_trial() -> None:
    recovery.validate_failed_state()
    failure = json.loads(recovery.FAILED_RECORD.read_text(encoding="utf-8"))
    assert failure["error_type"] == "ImportError"
    assert "libc++.1.dylib" in failure["error"]
    assert not (recovery.FAILED_ROOT / "trial_ledger.json").exists()
    assert not (recovery.FAILED_ROOT / "development_report.json").exists()


def test_recovery_uses_fresh_root_and_same_scientific_runner() -> None:
    assert recovery.RECOVERY_ROOT != recovery.FAILED_ROOT
    assert recovery.SCIENTIFIC_RUNNER_SHA256 == recovery.campaign.file_sha256(
        recovery.SCIENTIFIC_RUNNER
    )
    assert recovery.RECOVERY_ROOT.name == "walkforward_recovery_v1"


def test_status_is_read_only() -> None:
    payload = recovery.status()
    assert payload["failed_state_preserved"] is True
    assert payload["market_rows_or_return_values_read_by_status"] is False
    assert payload["candidate49_ledgers_changed_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False


def test_exact_runtime_rejects_current_nonproject_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recovery.sys, "executable", str(Path("/tmp/not-project-python")))
    with pytest.raises(recovery.Campaign102RecoveryError, match="exact runtime"):
        recovery.require_exact_runtime()


def test_recovery_activation_cannot_authorize_lockbox_or_provider() -> None:
    if not recovery.RECOVERY_ACTIVATION.exists():
        pytest.skip("activation is frozen after runner and tests are hashed")
    activation = json.loads(recovery.RECOVERY_ACTIVATION.read_text(encoding="utf-8"))
    assert activation["remaining_complete_development_trial_count"] == 3
    assert activation["lockbox_2024_2025_authorized"] is False
    assert activation["provider_request_authorized"] is False
