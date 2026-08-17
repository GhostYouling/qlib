import copy

import pytest

from scripts import a_share_three_day_walkforward_campaign133_finalize as finalize


def _ledger() -> dict:
    entry = {
        "attempt_id": "a",
        "previous_entry_sha256": finalize.CHAIN_GENESIS,
    }
    entry["entry_sha256"] = finalize.canonical_sha256(entry)
    return {
        "entries": [entry],
        "entry_count": 1,
        "infrastructure_failure_attempt_count": 0,
        "chain_tip_sha256": entry["entry_sha256"],
    }


def test_validate_chain_accepts_canonical_entry_and_rejects_mutation() -> None:
    ledger = _ledger()
    assert finalize.validate_chain(ledger) == ledger["chain_tip_sha256"]
    ledger["entries"][0]["attempt_id"] = "changed"
    with pytest.raises(finalize.Campaign133FinalizeError, match="digest changed"):
        finalize.validate_chain(ledger)


def test_append_postrun_failures_extends_without_rewriting() -> None:
    ledger = _ledger()
    before = copy.deepcopy(ledger)
    result = finalize.append_postrun_failures(ledger)
    assert ledger == before
    assert result["entries"][:-3] == before["entries"]
    assert result["entry_count"] == 4
    assert result["infrastructure_failure_attempt_count"] == 3
    assert finalize.validate_chain(result) == result["chain_tip_sha256"]


def test_bound_completed_trial_has_three_prefit_before_return_folds() -> None:
    ledger, report, survivors = finalize.validate_inputs()
    trial = finalize.summarize_trial(ledger)
    assert report["survivor_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert trial["validation_return_fold_count"] == 3
    assert all(fold["uniqueness_passed"] for fold in trial["folds"])
    assert all(fold["comparison_count"] == 140 for fold in trial["folds"])
    assert all(fold["mean_rank_ic"] < 0 for fold in trial["folds"])


def test_terminal_markdown_states_no_survivor_and_closed_lockbox() -> None:
    ledger, _, _ = finalize.validate_inputs()
    payload = {"trial": finalize.summarize_trial(ledger)}
    markdown = finalize.terminal_markdown(payload)
    assert "没有开发期幸存者" in markdown
    assert "2024–2025 准样本外锁箱未打开" in markdown
    assert "不构成投资建议" in markdown
