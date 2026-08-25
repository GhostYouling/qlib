from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign289_terminal_verify as verifier,
)


def test_expected_terminal_artifact_map_is_complete_and_bound() -> None:
    assert len(verifier.EXPECTED_ARTIFACT_SHA256) == 19
    for relative, expected in verifier.EXPECTED_ARTIFACT_SHA256.items():
        verifier.require_file(verifier.OUTPUT_ROOT / relative, expected, relative)


def test_terminal_ledger_semantics_and_decision_are_frozen() -> None:
    ledger = verifier.load_json(verifier.OUTPUT_ROOT / "terminal_trial_ledger.json")
    trial = verifier.validate_terminal_ledger(ledger)
    decision = trial["decision"]
    assert decision["passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_normalized_return_fold_count"] == 2
    assert decision["positive_pilot_10bp_return_fold_count"] == 1
    assert decision["development_aggregate"]["pilot_20bp_return"] < 0
