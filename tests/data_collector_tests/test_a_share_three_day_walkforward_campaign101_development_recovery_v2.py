from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign101_development_recovery_v2 as recovery,
)


def test_failed_ledger_has_two_infrastructure_entries_and_no_complete_trial() -> None:
    ledger = json.loads(recovery.TRIAL_LEDGER.read_text(encoding="utf-8"))
    recovery._validate_failed_ledger(ledger)
    assert len(ledger["entries"]) == 2
    assert all(item["phase"] == "infrastructure_failure" for item in ledger["entries"])


def test_loader_namespace_exposes_exact_inherited_defect() -> None:
    namespace = recovery._candidate_loader_namespace()
    assert namespace["EXPECTED_ELIGIBLE_ROWS"] == (
        recovery.STALE_INHERITED_ELIGIBLE_ROWS
    )
    assert recovery.campaign.EXPECTED_ELIGIBLE_ROWS == recovery.EXPECTED_ELIGIBLE_ROWS


def test_namespace_repair_changes_only_frozen_eligible_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = recovery._candidate_loader_namespace()
    original = dict(namespace)
    monkeypatch.setitem(
        namespace,
        "EXPECTED_ELIGIBLE_ROWS",
        recovery.STALE_INHERITED_ELIGIBLE_ROWS,
    )
    recovery.synchronize_frozen_candidate_semantics()
    assert namespace["EXPECTED_ELIGIBLE_ROWS"] == recovery.EXPECTED_ELIGIBLE_ROWS
    assert all(
        namespace.get(key) == value
        for key, value in original.items()
        if key != "EXPECTED_ELIGIBLE_ROWS"
    )


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
    with pytest.raises(recovery.Campaign101DevelopmentRecoveryV2Error):
        recovery.require_exact_runtime()


def test_bound_scientific_inputs_and_failure_evidence_are_unchanged() -> None:
    assert (
        recovery._sha256(recovery.SCIENTIFIC_RUNNER)
        == recovery.SCIENTIFIC_RUNNER_SHA256
    )
    assert recovery._sha256(recovery.PREREGISTRATION) == recovery.PREREGISTRATION_SHA256
    assert recovery._sha256(recovery.TRIAL_LEDGER) == recovery.FAILED_LEDGER_SHA256
    assert recovery._sha256(recovery.FAILURE_RECORD) == recovery.FAILURE_RECORD_SHA256
    assert recovery._sha256(recovery.RESEARCH_LEDGER) == recovery.RESEARCH_LEDGER_SHA256


def test_failure_record_preserves_read_boundary() -> None:
    record = json.loads(recovery.FAILURE_RECORD.read_text(encoding="utf-8"))
    boundary = record["read_boundary"]
    assert boundary["development_daily_execution_quote_values_read"] is True
    assert boundary["forward_return_or_fold_metric_computed"] is False
    assert boundary["complete_development_trial_consumed"] is False
    assert boundary["stress_2024_2025_read"] is False
    assert boundary["candidate49_ledgers_changed"] is False


def test_recovery_v2_status_has_no_survivor_or_stress_state() -> None:
    assert not (recovery.OUTPUT_ROOT / "development_survivors.json").exists()
    assert not (recovery.OUTPUT_ROOT / "exposed_stress_open_intent.json").exists()
    assert not (
        recovery.OUTPUT_ROOT / "exposed_stress_consumption_record.json"
    ).exists()
