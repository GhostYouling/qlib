from __future__ import annotations

import copy

import pytest

from scripts import a_share_three_day_walkforward_campaign286_terminal_verify as verifier


def test_terminal_verification_passes_and_keeps_lockbox_closed() -> None:
    result = verifier.verify()

    assert result["status"] == "verified_terminal_no_survivor_lockbox_closed"
    assert result["ledger_entry_count"] == 16
    assert result["model_trial_attempt_count"] == 3
    assert result["return_reading_development_trial_count"] == 3
    assert result["model_fold_validation_return_read_count"] == 9
    assert result["survivor_count"] == 0
    assert not result["lockbox_2024_2025_opened"]
    assert not result["candidate49_ledgers_changed"]


def test_ledger_validator_rejects_a_mutated_chain() -> None:
    ledger = verifier.load_json(verifier.OUTPUT_ROOT / "trial_ledger.json")
    mutated = copy.deepcopy(ledger)
    mutated["entries"][0]["outcome"] = "mutated"

    with pytest.raises(
        verifier.Campaign286TerminalVerificationError,
        match="hash chain",
    ):
        verifier.validate_ledger(mutated)
