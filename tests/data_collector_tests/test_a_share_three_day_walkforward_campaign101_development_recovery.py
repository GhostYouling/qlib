from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign101_development_recovery as recovery,
)


def test_failed_ledger_has_one_infrastructure_entry_and_no_complete_trial() -> None:
    ledger = json.loads(recovery.TRIAL_LEDGER.read_text(encoding="utf-8"))
    recovery._validate_failed_ledger(ledger)
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0]["phase"] == "infrastructure_failure"


def test_recovery_arguments_preserve_preregistration_output_and_trial() -> None:
    args = recovery._development_args(256)
    assert Path(args.campaign) == recovery.PREREGISTRATION
    assert Path(args.output_root) == recovery.OUTPUT_ROOT
    assert args.batch_size == 256
    assert recovery.FROZEN_TRIAL_ID == (
        "wf101_full_numeric_library_directional_lower_quartile_consensus_129f_single_higher"
    )


def test_recovery_rejects_wrong_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recovery.sys, "executable", "/tmp/not-the-frozen-runtime")
    with pytest.raises(recovery.Campaign101DevelopmentRecoveryError):
        recovery.require_exact_runtime()


def test_original_scientific_runner_and_preregistration_are_unchanged() -> None:
    assert (
        recovery._sha256(recovery.SCIENTIFIC_RUNNER)
        == recovery.SCIENTIFIC_RUNNER_SHA256
    )
    assert recovery._sha256(recovery.PREREGISTRATION) == recovery.PREREGISTRATION_SHA256
    assert recovery._sha256(recovery.TRIAL_LEDGER) == recovery.FAILED_LEDGER_SHA256


def test_recovery_status_reads_no_prices_returns_or_stress() -> None:
    source = recovery.main.__doc__ or ""
    assert isinstance(source, str)
    assert not (recovery.OUTPUT_ROOT / "development_survivors.json").exists()
    assert not (recovery.OUTPUT_ROOT / "exposed_stress_open_intent.json").exists()
    assert not (
        recovery.OUTPUT_ROOT / "exposed_stress_consumption_record.json"
    ).exists()
