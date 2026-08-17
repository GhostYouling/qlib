from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v4.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v5.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v208_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign151_terminal_v3.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign151_v5_ledger_appends_exact_lifecycle_failure() -> None:
    predecessor = _load(LEDGER_V4)
    ledger = _load(LEDGER_V5)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V4)
    entry = ledger["delta_entries"][0]
    assert entry["attempt_id"] == "campaign151_infrastructure_009"
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
    assert ledger["effective_attempt_count"] == 15
    assert ledger["effective_infrastructure_failure_attempt_count"] == 9
    assert ledger["cumulative_historical_research_attempt_count"] == 1318
    assert ledger["terminal_result"]["unchanged_from_v4"] is True


def test_campaign151_current_policy_and_state_bind_only_current_immutable_evidence() -> (
    None
):
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (policy, state):
        for binding in record["authoritative_inputs"].values():
            path = Path(binding["path"])
            if not path.is_absolute():
                path = ROOT / path
            assert _sha(path) == binding["sha256"]
    assert policy["effective_accounting"]["campaign151_attempt_count"] == 15
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 156
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert policy["campaign151_terminal_classification"]["eligible_rows"] == 0
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign152_historical_prevalue_authorized"] is True
    assert state["goal"]["campaign152_started"] is False
    assert state["candidate49"]["only_active_prospective_candidate"] is True
    assert (
        state["validation"][
            "mutable_report_or_lifecycle_test_bytes_bound_by_current_authority"
        ]
        is False
    )


def test_campaign151_reports_reach_final_accounting_without_scientific_change() -> None:
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "累计历史尝试 `1318`" in text
        assert "第 9 个基础设施失败" in text
        assert text.count("## Campaign151 同钟点相对成交额因子零覆盖终止") == 1
