from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign102 as campaign

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_102/"
    "walkforward_recovery_v2"
)
LEDGER = ROOT / "trial_ledger.json"
SURVIVORS = ROOT / "development_survivors.json"
REPORT = ROOT / "development_report.json"


def test_terminal_artifact_hashes_are_exact() -> None:
    assert campaign.file_sha256(LEDGER) == (
        "ac69d69ccf3a1e42c7056a69932edf522a05f0873ee9785e10111570fbd4bc1b"
    )
    assert campaign.file_sha256(SURVIVORS) == (
        "49e85527c05b9410d8c001eaa033c0232a78ccc270a4fb00e3556c80fe638e78"
    )
    assert campaign.file_sha256(REPORT) == (
        "98651cde0da7084e38fbc64b07707f8011637e99e2bcff80e9047cf2f15c50dc"
    )


def test_trial_ledger_chain_and_all_trial_outcomes_are_complete() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["append_only"] is True
    assert len(ledger["entries"]) == 3
    previous = campaign.CHAIN_GENESIS
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        assert campaign.value_sha256(payload) == entry["entry_sha256"]
        previous = entry["entry_sha256"]
        assert entry["status"] == "development_rejected"
        assert len(entry["folds"]) == 3
        assert len(entry["validation_metrics"]) == 3
        assert all(
            fold["uniqueness"]["all_required_comparisons_passed"] is True
            and fold["uniqueness"]["comparison_count"] == 130
            for fold in entry["folds"]
        )
    assert ledger["chain_tip_sha256"] == previous


def test_zero_survivors_keep_lockbox_closed() -> None:
    survivors = json.loads(SURVIVORS.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert survivors["selected_survivor_count"] == 0
    assert survivors["selected_lockbox_survivor_trial_ids"] == []
    assert survivors["lockbox_return_fields_read"] is False
    assert report["survivor_count"] == 0
    assert report["validation_return_reading_trial_count"] == 3
    assert report["lockbox_2024_2025_opened"] is False
    assert not list(ROOT.glob("*lockbox*"))


def test_both_infrastructure_failures_remain_preserved() -> None:
    original = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_102/"
        "walkforward/development_failure.json"
    )
    v1 = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_102/"
        "walkforward_recovery_v1/development_failure.json"
    )
    assert campaign.file_sha256(original) == (
        "5bf1c93c153bae6b49848ae328d1999cadacc32c22168edc511fee6e703afbd8"
    )
    assert campaign.file_sha256(v1) == (
        "c1352638402b4e47fe416d7a0d4696c30e3602b9d316a2d160a0b3e6c2f471f4"
    )


def test_candidate49_ledgers_are_unchanged() -> None:
    signal = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert campaign.file_sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign.file_sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert json.loads(signal.read_text(encoding="utf-8"))["entries"] == []
    assert json.loads(execution.read_text(encoding="utf-8"))["entries"] == []
