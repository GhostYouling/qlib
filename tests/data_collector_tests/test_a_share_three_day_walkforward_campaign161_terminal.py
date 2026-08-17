from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features
from scripts import (
    a_share_three_day_walkforward_campaign161_debt_maturity as acceptance,
)


ROOT = Path(__file__).resolve().parents[2]
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v4.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v5.json"
)
FAILURE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/source/acceptance_2023q4_failure_v1.json"
)
INTENT = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/source/acceptance_2023q4_intent_v1.json"
)
TERMINAL_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_161_terminal_result_20260815.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_161_terminal_result_v4_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v228_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign161_terminal_v4.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_161_terminal_report_v4.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def test_campaign161_all_authoritative_bindings_resolve() -> None:
    for record_path in (TERMINAL, POLICY, STATE):
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]

    state = _load(STATE)
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign161"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign161"]["attempt_ledger"]["sha256"] == _sha(LEDGER_V5)
    assert state["reports"]["campaign161_terminal_report"]["sha256"] == _sha(REPORT)


def test_campaign161_consumed_source_gate_is_terminal_and_value_free() -> None:
    failure = _load(FAILURE)
    intent = _load(INTENT)
    terminal = _load(TERMINAL_V1)
    plan = acceptance.build_plan()

    assert intent["status"] == "one_shot_authorization_consumed_before_provider_request"
    assert failure["status"].startswith("terminal_source_rejection")
    assert failure["error_code"] == "response_result_object_missing"
    assert failure["provider_request_attempted"] is True
    assert failure["provider_raw_response_persisted"] is False
    assert failure["published_files"] == []
    assert failure["acceptance_retry_allowed"] is False
    assert plan["ready"] is False
    assert plan["exit_code_if_executed"] == 2
    assert set(plan["blockers"]) == {"intent_absent", "failure_record_absent"}
    assert plan["provider_request_issued"] is False
    result = terminal["source_acceptance_result"]
    assert result["provider_response_rows_read"] == 0
    assert result["factor_values_computed_or_read"] == 0
    assert result["accepted_snapshot_published"] is False
    lifecycle = terminal["gate_lifecycle"]
    assert lifecycle["2019_2023_development_source_snapshot_run"] is False
    assert lifecycle["capacity_gate_run"] is False
    assert lifecycle["ordered_142_comparator_uniqueness_gate_run"] is False
    assert lifecycle["2019_2023_walkforward_return_trial_run"] is False
    assert lifecycle["2024_2025_returns_opened"] is False
    assert not acceptance.ACCEPTED_ROOT.exists()
    assert not acceptance.ACCEPTANCE_RECORD_PATH.exists()


def test_campaign161_v1_and_v2_attempt_chains_and_accounting() -> None:
    v1 = _load(LEDGER_V1)
    previous = v1["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in v1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
    assert previous == v1["chain_tip_sha256"]

    v2 = _load(LEDGER_V2)
    assert v2["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    for entry in v2["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert len(v2["delta_entries"]) == 10
    assert previous == v2["chain_tip_sha256"]
    assert v2["effective_entry_count"] == 12
    assert v2["effective_prevalue_scientific_attempt_count"] == 6
    assert v2["effective_infrastructure_failure_attempt_count"] == 6
    assert v2["cumulative_historical_research_attempt_count"] == 1408
    assert v2["cumulative_return_reading_development_trial_count"] == 314

    v3 = _load(LEDGER_V3)
    assert v3["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V2)
    for entry in v3["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert len(v3["delta_entries"]) == 1
    assert previous == v3["chain_tip_sha256"]
    assert v3["effective_entry_count"] == 13
    assert v3["effective_infrastructure_failure_attempt_count"] == 7
    assert v3["cumulative_historical_research_attempt_count"] == 1409
    assert v3["cumulative_return_reading_development_trial_count"] == 314

    v4 = _load(LEDGER_V4)
    assert v4["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V3)
    for entry in v4["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert len(v4["delta_entries"]) == 3
    assert previous == v4["chain_tip_sha256"]
    assert v4["effective_entry_count"] == 16
    assert v4["effective_infrastructure_failure_attempt_count"] == 10
    assert v4["cumulative_historical_research_attempt_count"] == 1412
    assert v4["cumulative_return_reading_development_trial_count"] == 314

    v5 = _load(LEDGER_V5)
    assert v5["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V4)
    for entry in v5["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert len(v5["delta_entries"]) == 1
    assert previous == v5["chain_tip_sha256"]
    assert v5["effective_entry_count"] == 17
    assert v5["effective_infrastructure_failure_attempt_count"] == 11
    assert v5["cumulative_historical_research_attempt_count"] == 1413
    assert v5["cumulative_return_reading_development_trial_count"] == 314


def test_campaign161_appends_definition_but_not_numeric_comparator() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {
            "name": "eastmoney_debt_maturity_resilience",
            "score_direction": "higher",
        }
    )
    comparisons = features.reconstruct_comparisons()
    policy = _load(POLICY)

    assert len(definitions) == 158
    assert features._order_digest(definitions) == (
        "4819c7fd7c0795d7598a52f3c615e3f117d5f4ecd9332974bc8e3dfa57c96667"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    library = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 158
    assert library["campaign161_definition_appended"] is True
    assert numeric["eligible_numeric_comparator_count"] == 142
    assert numeric["campaign161_numeric_series_appended"] is False


def test_campaign161_candidate49_and_append_only_reports_are_unchanged_in_scope() -> (
    None
):
    state = _load(STATE)
    terminal = _load(TERMINAL)
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["signal_ledger"]["entries"] == 0
    assert state["candidate49"]["execution_ledger"]["entries"] == 0
    assert terminal["research_boundary"]["candidate49_ledgers_changed"] is False
    assert terminal["research_boundary"]["stress_2024_2025_opened"] is False
    assert (
        terminal["research_boundary"][
            "current_scoring_selection_sizing_positions_or_orders_performed"
        ]
        is False
    )
    for report_key in ("current_research_report", "three_day_research_report"):
        report_binding = state["reports"][report_key]
        assert report_binding["mutable_append_only_report_not_an_immutable_binding"]
        text = (ROOT / report_binding["path"]).read_text(encoding="utf-8")
        assert text.count("## Campaign161 债务期限结构来源验收终止") == 1
        assert len(report_binding["sha256_at_publication"]) == 64


def test_campaign161_goal_remains_active_and_campaign162_is_offline_only() -> None:
    state = _load(STATE)
    policy = _load(POLICY)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign162_offline_scouting_authorized"] is True
    assert state["goal"]["campaign162_started"] is False
    boundary = policy["future_campaign_boundary"]
    assert boundary["next_campaign"] == 162
    assert boundary["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert (
        boundary[
            "campaign161_endpoint_report_date_field_formula_threshold_or_source_retry_allowed"
        ]
        is False
    )
    assert boundary["2024_2025_source_or_returns_remain_closed"] is True
