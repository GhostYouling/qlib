from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v200_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign148_prevalue_terminal_v2.json"
)
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_validation_v2_20260814.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_result_v5_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_148/research_attempt_ledger_v5.json"
)
INVALID_TERMINAL_V4 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_result_v4_20260814.json"
)
INVALID_TERMINAL_V4_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_v4_predecessor_binding_failure_20260814.json"
)
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


def test_campaign148_effective_policy_status_and_validation_bindings() -> None:
    for path in (POLICY, STATUS, VALIDATION, TERMINAL, LEDGER):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True, (path, report)

    policy = _load(POLICY)
    assert policy["version"] == 200
    assert policy["future_campaign_boundary"]["next_campaign"] == 149
    assert policy["effective_accounting"] == {
        "campaign148_attempt_count": 10,
        "campaign148_prevalue_concept_attempt_count": 6,
        "campaign148_infrastructure_failure_count": 4,
        "campaign148_complete_factor_attempt_count": 0,
        "campaign148_return_reading_development_trial_count": 0,
        "campaign148_development_survivor_count": 0,
        "campaign148_stress_trial_count": 0,
        "cumulative_historical_research_attempt_count": 1290,
        "cumulative_return_reading_development_trial_count": 314,
    }
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 155
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )


def test_campaign148_invalid_v4_is_preserved_but_not_authoritative() -> None:
    invalid = bindings.validate_record(INVALID_TERMINAL_V4)
    assert invalid["all_bindings_passed"] is False
    assert invalid["failed_binding_count"] == 1
    failure = _load(INVALID_TERMINAL_V4_FAILURE)
    assert failure["handling"]["invalid_record_rewritten_or_deleted"] is False
    assert failure["handling"]["failed_binding_bypassed_or_masked"] is False
    terminal = _load(TERMINAL)
    assert (
        terminal["supersedes_without_rewriting"][
            "predecessor_is_invalid_binding_evidence"
        ]
        is True
    )
    assert terminal["effective_accounting"]["campaign148_attempt_count"] == 10


def test_campaign148_goal_and_candidate49_remain_unchanged() -> None:
    status = _load(STATUS)
    assert status["goal"]["status"] == "active"
    assert status["goal"]["campaign149_offline_scouting_authorized"] is True
    assert status["campaign148"]["selected_candidate_count"] == 0
    assert status["candidate49_daily_20260814"]["same_day_retry_performed"] is False
    assert status["candidate49"]["signal_ledger"]["entries"] == 0
    assert status["candidate49"]["execution_ledger"]["entries"] == 0
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
