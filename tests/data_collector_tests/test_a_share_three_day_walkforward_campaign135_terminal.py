from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_135_concept_scouting_20260814.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_135_mechanism_source_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_135/research_attempt_ledger.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_135_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v162_20260814.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign135_prevalue_terminal.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: dict) -> str:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _resolve(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def test_campaign135_finite_catalog_rejects_every_concept_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    boundary = scouting["research_boundary"]
    assert boundary["campaign135_source_rows_read"] is False
    assert boundary["campaign135_candidate_values_computed_or_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_campaign135_frontier_and_policy_preserve_151_140_orders() -> None:
    frontier = _load(FRONTIER)
    assert frontier["concept_scouting"]["sha256"] == _sha(SCOUTING)
    assert (
        frontier["terminal_decision"]["campaign135_complete_factor_definition_created"]
        is False
    )

    policy = _load(POLICY)
    assert policy["version"] == 162
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (151, 140)
    assert (
        complete["order_sha256"]
        == "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
    )


def test_campaign135_append_only_ledger_hash_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        body = {key: value for key, value in entry.items() if key != "entry_sha256"}
        assert entry["entry_sha256"] == _canonical_sha(body)
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["entry_count"] == ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1120
    assert ledger["cumulative_return_reading_development_trial_count"] == 312


def test_campaign135_terminal_state_bindings_and_candidate49_isolation() -> None:
    terminal = _load(TERMINAL)
    for binding in terminal["authoritative_inputs"].values():
        assert _sha(_resolve(binding["path"])) == binding["sha256"]
    state = _load(STATE)
    for binding in state["campaign135_authoritative_artifacts"].values():
        assert _sha(_resolve(binding["path"])) == binding["sha256"]
    assert state["active_goal"]["status"] == "active"
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False


def test_unified_reports_record_campaign135_without_current_trading_output() -> None:
    for relative in [
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        section = text.split("## Campaign135 值前零候选终止", maxsplit=1)[1]
        assert "选中 0 个候选" in section
        assert "累计历史尝试 `1120`" in section
        assert "Campaign136" in section
        assert "当前评分" not in section
        assert "订单" not in section
