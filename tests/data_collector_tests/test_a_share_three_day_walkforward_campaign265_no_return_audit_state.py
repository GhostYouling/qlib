from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign265_no_return_audit_runner_ready.json"
)
PLAN_RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_no_return_audit_plan_result_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v19.json"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORTS = (
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
            "campaign265",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_latest_state_binds_the_new_no_return_evidence() -> None:
    state = _load(STATE)
    assert state["status"] == (
        "campaign265_no_return_audit_runner_frozen_source_snapshot_pending"
    )
    assert state["goal"] == {
        "objective": "请持续迭代因子。",
        "status": "active",
        "completion_claimed": False,
        "reason": "Campaign265 has a complete downstream no-return audit path, but its accepted source snapshot is absent and no candidate value, comparator value or return value has been read.",
    }
    for binding in state["new_authoritative_evidence"].values():
        target = ROOT / binding["path"]
        assert target.is_file()
        assert _sha256(target) == binding["sha256"]


def test_real_plan_is_fail_closed_only_on_the_missing_source_snapshot() -> None:
    plan = _load(PLAN_RESULT)
    observed = plan["real_plan_execution"]
    assert observed["exit_code"] == 2
    assert observed["ready"] is False
    assert observed["blockers"] == ["source_acceptance_manifest_absent_or_unsafe"]
    assert observed["source_parquet_rows_decoded"] == 0
    assert observed["candidate_values_read"] is False
    assert observed["comparator_values_read"] is False
    assert observed["historical_daily_price_or_forward_return_values_read"] is False
    assert plan["research_boundary"]["v420_policy_created"] is False


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == (
        "d300835fb37fbe83e6a59427e802f6e8d3d694c9438663e56e1b9b6a8e19d738"
    )
    entry = ledger["appended_entries"][0]
    assert entry["ordinal"] == 40
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert ledger["chain_tip_sha256"] == entry["entry_sha256"]
    assert ledger["effective_entry_count"] == 40
    assert ledger["effective_infrastructure_failure_attempt_count"] == 25
    assert ledger["effective_prevalue_scientific_attempt_count"] == 15
    assert ledger["cumulative_historical_research_attempt_count"] == 2644
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_candidate49_and_prospective_boundary_are_unchanged() -> None:
    state = _load(STATE)
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
    assert state["candidate49"]["sole_active_prospective_candidate"] is True
    assert state["research_boundary"]["second_prospective_candidate_created"] is False


def test_unified_reports_have_one_matching_new_section() -> None:
    heading = "## Campaign265：下游零收益审计入口冻结（2026-08-24）"
    for report in REPORTS:
        text = report.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "累计历史尝试 2,644" in text
        assert "source_acceptance_manifest_absent_or_unsafe" in text
        assert "143 个数值比较器" in text
