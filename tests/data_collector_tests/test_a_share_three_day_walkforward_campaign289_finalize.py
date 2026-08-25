from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign289_finalize as finalizer


def test_source_outputs_are_terminal_no_survivor() -> None:
    ledger, report, trial = finalizer.validate_inputs()
    assert ledger["entry_count"] == 8
    assert report["survivor_count"] == 0
    assert trial["decision"]["passed"] is False
    assert len(trial["validation_metrics"]) == 3


def test_terminal_ledger_appends_both_failures_without_rewriting_source_chain() -> None:
    source, _, _ = finalizer.validate_inputs()
    terminal = finalizer.build_terminal_ledger()
    assert terminal["entries"][:8] == source["entries"]
    assert [entry["attempt_id"] for entry in terminal["entries"][-2:]] == [
        "c289_infra_01",
        "c289_infra_02",
    ]
    assert terminal["entry_count"] == 10
    assert terminal["infrastructure_failure_attempt_count"] == 2
    assert terminal["fold1_training_return_read_count_total"] == 3
    assert (
        terminal["fold1_training_return_reread_count_for_infrastructure_recovery"] == 2
    )
    assert terminal["lockbox_2024_2025_opened"] is False
