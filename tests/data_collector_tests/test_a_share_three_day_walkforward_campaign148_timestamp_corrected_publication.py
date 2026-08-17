from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_148/research_attempt_ledger_v6.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_result_v6_20260814.json"
)
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_validation_v3_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v201_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign148_prevalue_terminal_v3.json"
)
TIMESTAMP_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_logical_timestamp_failure_20260814.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign148_timestamp_corrected_authority_bindings_and_wall_clock() -> None:
    for path in (LEDGER, TERMINAL, VALIDATION, POLICY, STATUS):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True, (path, report)
        recorded_at = dt.datetime.fromisoformat(_load(path)["recorded_at"]).timestamp()
        assert recorded_at <= path.stat().st_mtime + 1


def test_campaign148_timestamp_failure_is_counted_once() -> None:
    failure = _load(TIMESTAMP_FAILURE)
    assert len(failure["affected_artifacts"]) == 8
    assert failure["handling"]["common_root_cause_counted_once"] is True
    assert failure["handling"]["affected_artifacts_rewritten_or_deleted"] is False
    ledger = _load(LEDGER)
    assert ledger["effective_attempt_count"] == 11
    assert ledger["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 1291
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign148_timestamp_corrected_goal_remains_active() -> None:
    policy = _load(POLICY)
    status = _load(STATUS)
    assert policy["version"] == 201
    assert policy["future_campaign_boundary"]["next_campaign"] == 149
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 155
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert status["goal"]["status"] == "active"
    assert status["goal"]["campaign149_offline_scouting_authorized"] is True
    assert status["candidate49_daily_20260814"]["same_day_retry_performed"] is False
    assert status["candidate49"]["signal_ledger"]["entries"] == 0
    assert status["candidate49"]["execution_ledger"]["entries"] == 0
