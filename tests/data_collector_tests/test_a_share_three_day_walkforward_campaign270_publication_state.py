from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v2.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v3.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_publication_stage_failure_record_20260824.json"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED_REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign270",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_publication_failure_is_exact_narrow_and_precommit() -> None:
    assert _sha256(FAILURE) == (
        "a9aabbd6e5ada84b9d816020317e22686a281248c993bd66cc40d8c4bcbe0e2d"
    )
    failure = _load(FAILURE)
    assert failure["attempt_id"] == "campaign270_infrastructure_007"
    assert failure["process_exit_code"] == 1
    assert failure["commit_created"] is False
    assert failure["push_attempted"] is False
    assert failure["scientific_result_changed"] is False
    assert len(failure["partially_staged_before_failure"]) == 9
    assert len(failure["ignored_ledgers_not_staged_by_failed_command"]) == 2


def test_append_only_v3_adds_only_the_publication_failure() -> None:
    assert _sha256(LEDGER_V2) == (
        "1e310a1dfa9e64387fbbc5688d536762fee99daf40b14c595496789fd907967f"
    )
    assert _sha256(LEDGER) == (
        "29db0ed65ae7018685e0fc35cc061fdbe9e90e964fc4996344c4d995860690b7"
    )
    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha256(LEDGER_V2)
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["ordinal"] == 13
    assert entry["attempt_id"] == "campaign270_infrastructure_007"
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert entry["entry_sha256"] == ledger["chain_tip_sha256"]
    assert entry["candidate_or_comparator_value_read"] is False
    assert entry["return_reading_development_trial"] is False
    assert ledger["effective_entry_count"] == 13
    assert ledger["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 2733
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_current_reports_have_one_additive_publication_correction() -> None:
    expected_hashes = (
        "f007b5ea99c4448e643a289f3fb0ee94386271296fcd09ee02a9d714476f235e",
        "c8d9dc101d4a67992447a1384c28bac8cb511936b8d9cc3e4c37c81c733c3613",
    )
    heading = "### Campaign270 发布暂存失败会计修正"
    for path, expected_hash in zip(UNIFIED_REPORTS, expected_hashes, strict=True):
        assert _sha256(path) == expected_hash
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        section = text.split(heading, maxsplit=1)[1]
        assert "13 次尝试（6 科学、7 基础设施）" in section
        assert "累计历史尝试 2,733" in section
        assert "Candidate49 0/0" in section


def test_publication_failure_changes_no_research_or_prospective_boundary() -> None:
    for artifact in (_load(FAILURE), _load(LEDGER)):
        boundary = artifact["research_boundary"]
        for key, value in boundary.items():
            if key == "repository_metadata_and_prior_terminal_history_read":
                assert value is True
            else:
                assert value is False
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
