from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v4.json"
)
INVALID_LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v5.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v6.json"
)
BINDING_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_attempt_ledger_v5_binding_failure_20260824.json"
)
CROSS_STAGE_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_cross_stage_mutable_report_hash_failure_20260824.json"
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


def test_invalid_v5_is_preserved_and_excluded_from_the_effective_chain() -> None:
    assert _sha256(LEDGER_V4) == (
        "c7977692c83a4dec92db587cd4b3508a447cd3dc31dc9a0e8ee1d7c6ee90d1c0"
    )
    assert _sha256(INVALID_LEDGER_V5) == (
        "38af979e39ca96b54bea518371efeb855377b547785ab91830c894ef006102d5"
    )
    assert _sha256(BINDING_FAILURE) == (
        "5e1a3c34b553cb275a32c7250b70ea31544f4a0becff3412cb0e88649377c1d9"
    )
    failure = _load(BINDING_FAILURE)
    assert failure["invalid_ledger_used_as_chain_authority"] is False
    assert failure["actual_predecessor"]["sha256"] == _sha256(LEDGER_V4)
    assert failure["invalid_ledger"]["sha256"] == _sha256(INVALID_LEDGER_V5)


def test_effective_v6_restarts_from_valid_v4_and_appends_two_failures() -> None:
    assert _sha256(LEDGER) == (
        "d2783a1bdb6575c380a8e772d96b20e6aada70d25225c0d6c8832cc460276ea6"
    )
    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha256(LEDGER_V4)
    assert ledger["invalid_ledger_preserved_not_in_chain"]["sha256"] == _sha256(
        INVALID_LEDGER_V5
    )
    assert [entry["ordinal"] for entry in ledger["entries"]] == [15, 16]
    assert [entry["attempt_id"] for entry in ledger["entries"]] == [
        "campaign270_infrastructure_009",
        "campaign270_infrastructure_010",
    ]
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 16
    assert ledger["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 2736
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_cross_stage_failure_and_live_report_semantics_are_preserved() -> None:
    assert _sha256(CROSS_STAGE_FAILURE) == (
        "bd562ec5dc77086672f6d3d55e22426c5ecf3c634ce255a191d5350683a72ad3"
    )
    failure = _load(CROSS_STAGE_FAILURE)
    assert failure["result"] == {
        "passed": 214,
        "failed": 1,
        "deselected": 5,
        "duration_seconds": 36.08,
    }
    assert failure["old_test_or_mutable_report_rewrite_allowed"] is False
    heading = "### Campaign270 当前状态验证与台账绑定修正"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        section = text.split(heading, maxsplit=1)[1]
        assert "16 次尝试（6 科学、10 基础设施）" in section
        assert "累计历史尝试 2,736" in section
        assert "Candidate49 0/0" in section


def test_current_boundary_and_candidate49_ledgers_remain_closed() -> None:
    for artifact in (_load(BINDING_FAILURE), _load(CROSS_STAGE_FAILURE), _load(LEDGER)):
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
