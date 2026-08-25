from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign288_finalize as finalizer


def test_terminal_ledger_appends_infrastructure_failure_without_rewriting_source() -> None:
    source, _, _ = finalizer.validate_inputs()
    terminal = finalizer.build_terminal_ledger()

    assert source["entry_count"] == 9
    assert source["infrastructure_failure_attempt_count"] == 0
    assert terminal["entry_count"] == 10
    assert terminal["infrastructure_failure_attempt_count"] == 1
    assert terminal["entries"][:9] == source["entries"]
    assert terminal["entries"][-1]["attempt_id"] == "c288_infra_01"
    assert finalizer.validate_chain(source) == source["chain_tip_sha256"]


def test_rejected_model_keeps_lockbox_closed() -> None:
    _, report, trial = finalizer.validate_inputs()

    assert not trial["decision"]["passed"]
    assert trial["decision"]["positive_mean_rank_ic_fold_count"] == 3
    assert trial["decision"]["positive_pilot_10bp_return_fold_count"] == 0
    assert report["survivor_count"] == 0
    assert not report["lockbox_2024_2025_opened"]
