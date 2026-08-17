from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_153_concept_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_153_mechanism_source_frontier_audit_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_153/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_153/research_attempt_ledger_v2.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_153/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_153_terminal_result_v3_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v213_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign153_prevalue_terminal_v3.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_153_terminal_report.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
MINUTE_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/raw/a_share/rich/tushare/minutes/1m/"
    "snapshots/tushare_stk_mins_1m_2019_2025_ea0cbb8f/snapshot_manifest.json"
)
DAILY_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/raw/a_share/rich/tushare/daily/"
    "snapshots/tushare_daily_2019_2025_acf72e28/snapshot_manifest.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign153_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    assert all(entry["prevalue_decision"].startswith("rejected_") for entry in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    boundary = scouting["research_boundary"]
    assert boundary["source_rows_or_column_values_read"] is False
    assert boundary["campaign153_candidate_values_computed_or_read"] is False
    assert boundary["campaign153_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign153_accepted_schemas_do_not_contain_required_new_states() -> None:
    minute_fields = set(_load(MINUTE_MANIFEST)["source_request"]["fields"])
    daily_snapshot = _load(DAILY_MANIFEST)
    daily_acceptance = Path(daily_snapshot["acceptance_manifest_path"])
    assert _sha(daily_acceptance) == daily_snapshot["acceptance_manifest_sha256"]
    daily_fields = set(_load(daily_acceptance)["fields"])
    forbidden_missing = {
        "best_bid",
        "best_ask",
        "aggressor_side",
        "executed_trade_count",
        "order_event_type",
        "displayed_quantity",
        "circ_mv",
        "total_mv",
        "free_share",
        "total_share",
    }
    assert forbidden_missing.isdisjoint(minute_fields)
    assert forbidden_missing.isdisjoint(daily_fields)
    assert minute_fields == {
        "ts_code",
        "trade_time",
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
    }


def test_campaign153_mechanism_and_source_gate_rejects_every_proposal() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(
        item["accepted_historical_source_and_original_contract_permits_inputs"] is False
        for item in results
    )
    assert (
        sum(item["semantically_independent_from_terminal_library"] for item in results)
        == 4
    )
    assert all(item["passed"] is False for item in results)
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    assert (
        audit["terminal_decision"][
            "campaign153_source_acceptance_coverage_uniqueness_or_return_audit_run"
        ]
        is False
    )


def test_campaign153_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1334
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign153",
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
    assert ledger["cumulative_historical_research_attempt_count"] == 1340
    assert ledger["cumulative_return_reading_development_trial_count"] == 314

    ledger_v2 = _load(LEDGER_V2)
    assert ledger_v2["authoritative_predecessor"]["sha256"] == _sha(LEDGER)
    assert len(ledger_v2["delta_entries"]) == 1
    delta = ledger_v2["delta_entries"][0]
    assert delta["previous_entry_sha256"] == previous
    payload = "|".join(
        [
            "campaign153",
            delta["attempt_id"],
            previous,
            delta["phase"],
            delta["status"],
        ]
    )
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert delta["entry_sha256"] == expected
    assert delta["candidate_comparator_price_or_return_value_read"] is False
    assert ledger_v2["chain_tip_sha256"] == expected
    assert ledger_v2["effective_entry_count"] == 7

    effective = _load(EFFECTIVE_LEDGER)
    assert effective["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V2)
    previous = expected
    for delta in effective["delta_entries"]:
        assert delta["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign153",
                delta["attempt_id"],
                previous,
                delta["phase"],
                delta["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert delta["entry_sha256"] == expected
        assert delta["candidate_comparator_price_or_return_value_read"] is False
        previous = expected
    assert len(effective["delta_entries"]) == 2
    assert effective["chain_tip_sha256"] == expected
    assert effective["effective_entry_count"] == 9
    assert effective["effective_infrastructure_failure_attempt_count"] == 3
    assert effective["cumulative_historical_research_attempt_count"] == 1343
    assert effective["cumulative_return_reading_development_trial_count"] == 314


def test_campaign153_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    comparisons = features.reconstruct_comparisons()
    assert len(definitions) == 157
    assert features._order_digest(definitions) == (
        "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )


def test_campaign153_publication_bindings_and_candidate49_boundary() -> None:
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
    assert state["campaign153"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign153"]["attempt_ledger"]["sha256"] == _sha(EFFECTIVE_LEDGER)
    assert state["reports"]["campaign153_terminal_report"]["sha256"] == _sha(REPORT)
    for report_key in ("current_research_report", "three_day_research_report"):
        report_binding = state["reports"][report_key]
        assert (
            report_binding["mutable_append_only_report_not_an_immutable_binding"]
            is True
        )
        assert len(report_binding["sha256_at_publication"]) == 64
        report_text = (ROOT / report_binding["path"]).read_text(encoding="utf-8")
        assert report_text.count("## Campaign153 来源状态前沿值前终止") == 1
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
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False
    assert state["candidate49_daily_20260815"]["provider_request_issued"] is False


def test_campaign153_records_use_reached_wall_clock_timestamps() -> None:
    for path in (
        SCOUTING,
        AUDIT,
        LEDGER,
        LEDGER_V2,
        EFFECTIVE_LEDGER,
        TERMINAL,
        POLICY,
        STATE,
    ):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
    predecessor = _load(LEDGER)["authoritative_predecessor"]
    assert predecessor["recorded_at_ahead_of_campaign153_observed_wall_clock"] is True
    assert predecessor["timestamp_anomaly_preserved_without_rewriting"] is True


def test_campaign152_and_campaign153_reports_are_appended_once() -> None:
    headings = (
        "## Campaign152 绝对成交额规模数值去重终止",
        "## Campaign153 来源状态前沿值前终止",
    )
    assert "Campaign153" in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert all(text.count(heading) == 1 for heading in headings)


def test_campaign153_goal_remains_active_and_campaign154_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign153_scientific_decision_completed"] is True
    assert state["goal"]["campaign154_offline_scouting_authorized"] is True
    assert state["goal"]["campaign154_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
