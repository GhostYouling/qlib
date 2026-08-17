from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_162_prevalue_infrastructure_failures_20260815.json"
)
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_162_daily_ohlcv_residual_catalog_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_162/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_162_terminal_result_20260815.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_162_terminal_report.md"
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v229_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign162_prevalue_terminal.json"
)
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


def test_campaign162_all_authoritative_bindings_resolve() -> None:
    for record_path in (FAILURES, CATALOG, TERMINAL, POLICY, STATE):
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]

    state = _load(STATE)
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign162"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign162"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign162_terminal_report"]["sha256"] == _sha(REPORT)


def test_campaign162_catalog_is_finite_complete_and_value_free() -> None:
    catalog = _load(CATALOG)
    routes = catalog["finite_prevalue_catalog"]
    assert len(routes) == 6
    assert [item["catalog_id"] for item in routes] == [
        "c162_01",
        "c162_02",
        "c162_03",
        "c162_04",
        "c162_05",
        "c162_06",
    ]
    assert all(item["formula"] is None for item in routes)
    assert all(item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert catalog["decision"]["selected_candidate_count"] == 0
    assert catalog["decision"]["complete_factor_definition_created"] is False
    boundary = catalog["research_boundary"]
    assert boundary["source_file_row_or_column_value_read"] is False
    assert boundary["candidate_or_comparator_value_read"] is False
    assert boundary["historical_daily_price_or_forward_return_value_read"] is False


def test_campaign162_infrastructure_failures_are_preserved() -> None:
    record = _load(FAILURES)
    failures = record["failures"]
    assert len(failures) == 2
    assert [item["attempt_id"] for item in failures] == [
        "campaign162_infrastructure_001",
        "campaign162_infrastructure_002",
    ]
    assert [item["exit_code"] for item in failures] == [0, 1]
    assert failures[0]["temporary_file_present_after_recovery"] is False
    assert failures[0]["workspace_target_written"] is False
    assert failures[1]["partial_output_or_target_write"] is False
    assert all(
        item["source_candidate_comparator_price_or_return_value_read"] is False
        for item in failures
    )


def test_campaign162_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    assert predecessor["cumulative_historical_research_attempt_count"] == 1413
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign162",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 8
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 1421
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign162_terminal_result_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {
            "name": "eastmoney_debt_maturity_resilience",
            "score_direction": "higher",
        }
    )
    comparisons = features.reconstruct_comparisons()
    terminal = _load(TERMINAL)
    policy = _load(POLICY)

    assert len(definitions) == 158
    assert features._order_digest(definitions) == (
        "4819c7fd7c0795d7598a52f3c615e3f117d5f4ecd9332974bc8e3dfa57c96667"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert terminal["library_state"]["changed_by_campaign162"] is False
    assert policy["complete_historical_feature_library"]["unchanged_from_v228"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v228"]


def test_campaign162_policy_keeps_walkforward_and_holdout_boundaries() -> None:
    policy = _load(POLICY)
    boundary = policy["future_campaign_boundary"]
    assert boundary["next_campaign"] == 163
    assert boundary["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert (
        boundary[
            "campaign162_routes_may_not_be_retried_rewindowed_inverted_reestimated_interacted_or_rescued"
        ]
        is True
    )
    assert (
        boundary[
            "2019_2023_development_requires_the_three_frozen_expanding_folds_and_three_signal_session_purge"
        ]
        is True
    )
    assert boundary["2024_2025_source_or_returns_remain_closed"] is True


def test_campaign162_candidate49_weekend_and_goal_boundaries_hold() -> None:
    state = _load(STATE)
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["signal_ledger"]["entries"] == 0
    assert state["candidate49"]["execution_ledger"]["entries"] == 0
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False
    assert state["candidate49_daily_20260815"]["credential_presence_checked"] is False
    assert state["candidate49_daily_20260815"]["plan_run"] is False
    assert state["candidate49_daily_20260815"]["run_run"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign163_offline_scouting_authorized"] is True
    assert state["goal"]["campaign163_started"] is False


def test_campaign162_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign162 日线 OHLCV 残余路线值前终止"
    assert "6 次科学值前判断和 2 次基础设施失败" in REPORT.read_text(encoding="utf-8")
    state = _load(STATE)
    for report_key in ("current_research_report", "three_day_research_report"):
        binding = state["reports"][report_key]
        assert binding["mutable_append_only_report_not_an_immutable_binding"]
        text = (ROOT / binding["path"]).read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign162 共 8 次尝试（6 科学、2 基础设施）" in text
        assert len(binding["sha256_at_publication"]) == 64


def test_campaign162_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (FAILURES, CATALOG, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
