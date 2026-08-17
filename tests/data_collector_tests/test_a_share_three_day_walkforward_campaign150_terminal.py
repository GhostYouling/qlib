from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign146_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_150_concept_scouting_20260814.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_150_mechanism_frontier_audit_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_150/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_150_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v203_20260814.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign150_prevalue_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_150_terminal_report.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign150_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    assert all(entry["prevalue_decision"].startswith("rejected_") for entry in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    boundary = scouting["research_boundary"]
    assert boundary["source_rows_or_column_values_read"] is False
    assert boundary["campaign150_candidate_values_computed_or_read"] is False
    assert boundary["campaign150_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign150_mechanism_gate_rejects_every_proposal() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(
        item["accepted_historical_source_and_original_contract_permits_inputs"]
        for item in results
    )
    assert all(
        item["semantically_independent_from_terminal_library"] is False
        for item in results
    )
    assert all(item["passed"] is False for item in results)
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    assert (
        audit["decision"]["source_acceptance_coverage_uniqueness_or_return_stage_run"]
        is False
    )


def test_campaign150_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign150",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = expected
    assert len(ledger["entries"]) == 6
    assert ledger["effective_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1303
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign150_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    comparisons = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(definitions) == 155
    assert features._order_digest(definitions) == (
        "2e4114edb26fa3aaebd145ef07fe4e2ac9c5d9dc4586cf70ff61c20e39b954ba"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )


def test_campaign150_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = ROOT / binding["path"]
            assert _sha(bound) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign150"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign150"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign150_terminal_report"]["sha256"] == _sha(REPORT)
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert len(_load(SIGNAL_LEDGER)["entries"]) == 0
    assert len(_load(EXECUTION_LEDGER)["entries"]) == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49"]["ledgers_changed"] is False
    assert state["candidate49_daily_20260814"]["same_day_retry_performed"] is False


def test_campaign150_records_have_reached_wall_clock_timestamps() -> None:
    for path in (SCOUTING, AUDIT, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign150_reports_are_append_only_once() -> None:
    heading = "## Campaign150 算法与状态模型残余前沿值前终止"
    assert "Campaign150" in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
