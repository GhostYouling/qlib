from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_114_official_metadata_discovery_failure_20260809.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_114/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_114/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_114/research_attempt_ledger_v4.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_114_terminal_result_20260809.json"
)
POLICY_V82 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v82_20260809.json"
)
POLICY_V83 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v83_20260809.json"
)
POLICY_V84 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v84_20260809.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260809_campaign114_terminal.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign114_terminal_artifact_hashes_are_exact() -> None:
    assert _sha256(FAILURE) == (
        "3b2da64258cd3e00e648edea8086b3e84bb7543f9656c919e37d800b8f2ab66a"
    )
    assert _sha256(LEDGER_V3) == (
        "2bc343aebf1444a6979ba2535296335f3230abc51c8abd3d3e57ae5b0b4e83aa"
    )
    assert _sha256(RESULT) == (
        "2ad2e0203859ce4822ed8e232d6c822e8f6af5bc313db429e03d3d408438c17f"
    )
    assert _sha256(POLICY_V83) == (
        "d140d58d0f8e084f321bad838db86dfc3cc4b218ee592171f262892e0c756f28"
    )
    assert _sha256(LEDGER_V4) == (
        "d0113b0e15f14fb6aa2b87a5e97bc90a5e2353cc53675f07f857be475055c33c"
    )
    assert _sha256(POLICY_V84) == (
        "83a9b83bc2a8056623b7248fc61a70cf86d8a994b7bd9a08c7d0e13f744f5d8f"
    )


def test_search_response_exposure_fails_the_frozen_prevalue_boundary() -> None:
    failure = _load(FAILURE)
    execution = failure["protocol_bound_execution"]
    assert execution["search_vocabulary"] == [
        "信息披露工作评价",
        "信息披露考核",
        "信息披露评价结果",
    ]
    assert execution["search_query_count"] == 9
    assert execution["attachment_click_open_download_or_screenshot_count"] == 0
    hard_failure = failure["hard_failure"]
    assert hard_failure["direct_attachment_opened_or_downloaded"] is False
    assert hard_failure["search_response_exposed_attachment_source_rows"] is True
    assert hard_failure["source_row_count"] is None
    assert hard_failure["individual_source_row_values_persisted_in_repository"] is False
    assert hard_failure["formula_or_grade_mapping_frozen_before_exposure"] is False
    assert (
        hard_failure[
            "post_exposure_formula_mapping_adapter_or_source_contract_freeze_allowed"
        ]
        is False
    )
    gate = failure["mandatory_gate_result"]
    assert gate["both_exchange_2019_2025_archive_gate_passed"] is False
    assert gate["metadata_only_boundary_preserved"] is False
    assert gate["overall_passed"] is False


def test_v3_ledger_extends_v2_and_final_accounting_is_exact() -> None:
    prior = _load(LEDGER_V2)
    ledger = _load(LEDGER_V3)
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == _sha256(LEDGER_V2)
    assert extension["prior_chain_tip_sha256"] == prior["current_chain_tip_sha256"]
    previous = extension["prior_chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign114|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["current_chain_tip_sha256"]
    assert ledger["total_attempt_count"] == 7
    assert ledger["total_infrastructure_failure_count"] == 5
    assert ledger["total_prevalue_scientific_attempt_count"] == 2
    assert ledger["total_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 852
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_v4_ledger_records_first_terminal_verification_failure() -> None:
    prior = _load(LEDGER_V3)
    ledger = _load(LEDGER_V4)
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == _sha256(LEDGER_V3)
    assert extension["prior_chain_tip_sha256"] == prior["current_chain_tip_sha256"]
    entry = ledger["entries"][0]
    assert entry["directed_test_receipt"] == "31 passed, 1 failed in 1.96s"
    payload = (
        "campaign114|"
        + entry["attempt_id"]
        + "|"
        + entry["previous_entry_sha256"]
        + "|"
        + entry["phase"]
        + "|"
        + entry["status"]
    ).encode()
    assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
    assert entry["entry_sha256"] == ledger["current_chain_tip_sha256"]
    assert ledger["total_attempt_count"] == 8
    assert ledger["total_infrastructure_failure_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 853
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_terminal_result_stops_before_definition_values_or_returns() -> None:
    result = _load(RESULT)
    scientific = result["scientific_result"]
    assert scientific["campaign114_terminal"] is True
    assert scientific["complete_factor_definition_count"] == 0
    assert scientific["numeric_snapshot_count"] == 0
    assert scientific["development_trial_count"] == 0
    assert scientific["stress_trial_count"] == 0
    assert scientific["historical_predictive_value_established"] is False
    future = result["future_boundary"]
    assert future["campaign114_reopen_or_repair_allowed"] is False
    assert future["campaign114_attachment_or_source_row_request_allowed"] is False
    assert future["campaign114_definition_may_enter_complete_library"] is False


def test_v83_preserves_v82_library_and_comparator_orders() -> None:
    previous = _load(POLICY_V82)
    policy = _load(POLICY_V83)
    assert policy["supersedes_without_rewriting"]["sha256"] == _sha256(POLICY_V82)
    library = policy["complete_historical_feature_library"]
    assert library["factor_definition_count"] == 141
    assert (
        library["order_sha256"]
        == previous["complete_historical_feature_library"]["order_sha256"]
    )
    comparators = policy["numerical_comparator_eligibility"]
    assert comparators["eligible_numeric_comparator_count"] == 134
    assert (
        comparators["eligible_numeric_comparator_order_sha256"]
        == previous["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert policy["campaign114_terminal_classification"]["terminal"] is True
    assert (
        policy["future_campaign_boundary"][
            "campaign114_reopen_repair_search_or_source_row_request_allowed"
        ]
        is False
    )


def test_v84_accounts_for_verification_without_changing_library() -> None:
    previous = _load(POLICY_V83)
    policy = _load(POLICY_V84)
    assert policy["supersedes_without_rewriting"]["sha256"] == _sha256(POLICY_V83)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 141
    )
    assert (
        policy["complete_historical_feature_library"]["order_sha256"]
        == previous["complete_historical_feature_library"]["order_sha256"]
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 134
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
        == previous["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert policy["final_accounting"]["campaign114_attempt_count"] == 8
    assert (
        policy["final_accounting"]["cumulative_historical_research_attempt_count"]
        == 853
    )


def test_state_candidate49_and_sunday_boundaries_remain_closed() -> None:
    state = _load(STATE)
    assert state["effective_future_numeric_policy"]["path"] == str(
        POLICY_V84.relative_to(ROOT)
    )
    assert state["accounting"]["campaign114_attempt_count"] == 8
    assert state["accounting"]["cumulative_historical_research_attempt_count"] == 853
    assert state["local_session_status"]["accepted_local_trading_day"] is False
    assert state["local_session_status"]["candidate49_plan_or_run_executed"] is False
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["provider_credential"]["tushare_token_entry_count"] == 1
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert (
        state["provider_credential"]["secret_printed_hashed_logged_or_persisted"]
        is False
    )


def test_terminal_timestamps_do_not_postdate_file_writes() -> None:
    for path in (FAILURE, LEDGER_V3, RESULT, POLICY_V83, LEDGER_V4, POLICY_V84, STATE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified


def test_unified_reports_record_terminal_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_114_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "docs/a_share_data_pipeline.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign114 官方元数据终止" in text
        assert "v83" in text
        assert "v84" in text
        assert "852" in text
        assert "853" in text
        assert "302" in text
        assert "Candidate49" in text
        assert "投资建议" in text
