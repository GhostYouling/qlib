from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v2.json"
)
POLICY_V205 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v205_20260815.json"
)
STATE_V2 = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign151_formula_frozen_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign151_additive_ledger_extends_v1_once() -> None:
    v1 = _load(LEDGER_V1)
    v2 = _load(LEDGER_V2)
    assert v2["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    assert v2["authoritative_predecessor"]["chain_tip_sha256"] == v1["chain_tip_sha256"]
    assert len(v2["delta_entries"]) == 1
    entry = v2["delta_entries"][0]
    assert entry["previous_entry_sha256"] == v1["chain_tip_sha256"]
    payload = "|".join(
        [
            "campaign151",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        ]
    )
    assert entry["entry_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
    assert v2["chain_tip_sha256"] == entry["entry_sha256"]
    assert v2["effective_attempt_count"] == 8
    assert v2["effective_infrastructure_failure_attempt_count"] == 2
    assert v2["cumulative_historical_research_attempt_count"] == 1311


def test_campaign151_v205_and_v2_state_bind_current_evidence() -> None:
    policy = _load(POLICY_V205)
    state = _load(STATE_V2)
    for record in (policy, state):
        for binding in record["authoritative_inputs"].values():
            path = Path(binding["path"])
            if not path.is_absolute():
                path = ROOT / path
            assert _sha(path) == binding["sha256"]
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 156
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign152_authorized"] is False
    assert (
        state["research_boundary"]["campaign151_historical_source_rows_read"] is False
    )
    assert state["research_boundary"]["campaign151_peer_benchmark_values_read"] is False
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0


def test_campaign151_v2_timestamps_and_accounting_reports() -> None:
    for path in (LEDGER_V2, POLICY_V205, STATE_V2):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
    heading = "### Campaign151 发布校验会计追加"
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "累计历史尝试 `1311`" in text
