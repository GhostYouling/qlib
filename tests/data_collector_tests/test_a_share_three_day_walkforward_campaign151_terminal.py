from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v3.json"
)
POLICY_V206 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v206_20260815.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260815_campaign151_terminal.json"
)
RECEIPT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_full_verification_20260815.json"
)
MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign151_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign151_feature_library_v1/snapshot_manifest.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign151_terminal_ledger_extends_v2_and_counts_every_failure() -> None:
    predecessor = _load(LEDGER_V2)
    ledger = _load(LEDGER_V3)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V2)
    assert (
        ledger["authoritative_predecessor"]["chain_tip_sha256"]
        == predecessor["chain_tip_sha256"]
    )
    previous = predecessor["chain_tip_sha256"]
    assert [entry["attempt_id"] for entry in ledger["delta_entries"]] == [
        f"campaign151_infrastructure_{index:03d}" for index in range(3, 8)
    ]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign151",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        assert entry["entry_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
        assert entry["failed_exit_code_bypassed_or_masked"] is False
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["effective_attempt_count"] == 13
    assert ledger["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger["cumulative_historical_research_attempt_count"] == 1316


def test_campaign151_full_snapshot_is_verified_zero_coverage_before_returns() -> None:
    receipt = _load(RECEIPT)
    manifest = _load(MANIFEST)
    assert _sha(MANIFEST) == receipt["snapshot_manifest_sha256"]
    assert manifest["dataset_sha256"] == receipt["dataset_sha256"]
    assert receipt["partitions"] == manifest["partitions"] == 33_015
    assert receipt["rows"] == manifest["rows"] == 7_724_498
    assert receipt["eligible_rows"] == manifest["eligible_rows"] == 0
    assert all(receipt["verified"].values())
    assert receipt["peer_benchmark"]["position_238_zero_dates"] == 1_699
    assert receipt["terminal_decision"]["campaign151_return_read_allowed"] is False
    assert receipt["terminal_decision"]["formula_or_gate_rescue_allowed"] is False
    assert (
        receipt["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_campaign151_terminal_policy_and_state_bind_current_evidence() -> None:
    policy = _load(POLICY_V206)
    state = _load(STATE)
    for record in (policy, state):
        for name, binding in record["authoritative_inputs"].items():
            if record is state and name == "campaign151_terminal_report":
                continue
            path = Path(binding["path"])
            if not path.is_absolute():
                path = ROOT / path
            assert _sha(path) == binding["sha256"]
    assert policy["campaign151_terminal_classification"]["terminal"] is True
    assert policy["numerical_comparator_eligibility"] == {
        "eligible_numeric_comparator_count": 142,
        "eligible_numeric_comparator_order_sha256": (
            "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        ),
        "unchanged_from_v205": True,
        "campaign151_numeric_series_appended": False,
        "campaign151_append_prohibited_reason": (
            "zero eligible rows across the independently verified 7724498-row snapshot"
        ),
    }
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign151_scientific_decision_completed"] is True
    assert state["goal"]["campaign152_historical_prevalue_authorized"] is True
    assert state["goal"]["campaign152_started"] is False
    assert state["candidate49"]["only_active_prospective_candidate"] is True
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0


def test_campaign151_terminal_reports_are_appended_once() -> None:
    heading = "## Campaign151 同钟点相对成交额因子零覆盖终止"
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        section = text.split(heading, 1)[1]
        assert "7,724,498" in section
        assert "累计历史尝试 `1316`" in section
        assert "Campaign152" in section


def test_campaign151_terminal_records_use_reached_wall_clock_times() -> None:
    for path in (LEDGER_V3, POLICY_V206, STATE, RECEIPT):
        record = _load(path)
        recorded_at = datetime.fromisoformat(record["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
