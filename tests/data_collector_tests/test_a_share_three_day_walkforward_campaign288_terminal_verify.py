from __future__ import annotations

import copy

import pytest

from scripts import a_share_three_day_walkforward_campaign288_terminal_verify as verifier


def test_terminal_verification_passes_and_keeps_lockbox_closed() -> None:
    result = verifier.verify()

    assert result["status"] == "verified_terminal_no_survivor_lockbox_closed"
    assert result["ledger_entry_count"] == 10
    assert result["infrastructure_failure_attempt_count"] == 1
    assert result["positive_rank_ic_fold_count"] == 3
    assert result["positive_pilot_10bp_return_fold_count"] == 0
    assert result["survivor_count"] == 0
    assert not result["lockbox_2024_2025_opened"]


def test_terminal_ledger_validator_rejects_mutation() -> None:
    ledger = verifier.load_json(verifier.OUTPUT_ROOT / "terminal_trial_ledger.json")
    mutated = copy.deepcopy(ledger)
    mutated["entries"][0]["outcome"] = "mutated"

    with pytest.raises(
        verifier.Campaign288TerminalVerificationError, match="hash chain"
    ):
        verifier.validate_terminal_ledger(mutated)


def test_terminal_rejection_preserves_positive_ic_but_failed_economics() -> None:
    ledger = verifier.load_json(verifier.OUTPUT_ROOT / "terminal_trial_ledger.json")
    trial = verifier.validate_terminal_ledger(ledger)
    decision = trial["decision"]

    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_pilot_10bp_return_fold_count"] == 0
    assert decision["median_validation_spread"] < 0
    assert decision["development_aggregate"]["pilot_20bp_return"] < 0
    assert not decision["passed"]
