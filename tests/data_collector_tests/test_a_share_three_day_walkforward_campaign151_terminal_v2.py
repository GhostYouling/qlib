from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v4.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v207_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign151_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign151_v4_ledger_appends_postpublication_failure_once() -> None:
    predecessor = _load(LEDGER_V3)
    ledger = _load(LEDGER_V4)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V3)
    assert len(ledger["delta_entries"]) == 1
    entry = ledger["delta_entries"][0]
    assert entry["attempt_id"] == "campaign151_infrastructure_008"
    assert entry["previous_entry_sha256"] == predecessor["chain_tip_sha256"]
    material = "|".join(
        [
            "campaign151",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        ]
    )
    assert entry["entry_sha256"] == hashlib.sha256(material.encode()).hexdigest()
    assert ledger["chain_tip_sha256"] == entry["entry_sha256"]
    assert ledger["effective_attempt_count"] == 14
    assert ledger["effective_infrastructure_failure_attempt_count"] == 8
    assert ledger["cumulative_historical_research_attempt_count"] == 1317
    assert ledger["terminal_result"]["unchanged_from_v3"] is True


def test_campaign151_v207_policy_and_terminal_v2_state_bind_current_files() -> None:
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (policy, state):
        for name, binding in record["authoritative_inputs"].items():
            if (record is policy and name == "terminal_test") or (
                record is state
                and name in {"campaign151_terminal_report", "terminal_test"}
            ):
                continue
            path = Path(binding["path"])
            if not path.is_absolute():
                path = ROOT / path
            assert _sha(path) == binding["sha256"]
    assert policy["effective_accounting"]["campaign151_attempt_count"] == 14
    assert policy["campaign151_terminal_classification"]["eligible_rows"] == 0
    assert (
        policy["numerical_comparator_eligibility"][
            "campaign151_numeric_series_appended"
        ]
        is False
    )
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign152_historical_prevalue_authorized"] is True
    assert state["goal"]["campaign152_started"] is False
    assert state["candidate49"]["only_active_prospective_candidate"] is True
    assert state["research_boundary"]["second_prospective_candidate_created"] is False


def test_campaign151_postpublication_accounting_report_is_once_per_report() -> None:
    heading = "### Campaign151 发布后生命周期会计追加"
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        section = text.split(heading, 1)[1]
        assert "累计历史尝试 `1317`" in section
        assert "41 passed" in section
