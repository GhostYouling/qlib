from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign102 as campaign

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign102_terminal.json"
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v59_20260807.json"
)


def test_authoritative_state_bindings_and_accounting_are_exact() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["status"] == (
        "campaign102_verified_terminal_zero_survivors_ready_for_campaign103_offline_research"
    )
    assert state["campaign102_terminal_result"]["development_survivor_count"] == 0
    assert state["campaign102_terminal_result"]["lockbox_2024_2025_opened"] is False
    assert state["final_accounting"] == {
        "campaign102_attempt_count": 7,
        "campaign102_infrastructure_failure_count": 2,
        "campaign102_complete_no_return_design_outcome_count": 1,
        "campaign102_return_reading_complete_development_trial_count": 3,
        "campaign102_development_survivor_count": 0,
        "campaign102_lockbox_trial_count": 0,
        "cumulative_historical_research_attempt_count": 753,
        "cumulative_return_reading_development_trial_count": 298,
    }
    for binding in (
        state["supersedes_without_rewriting"],
        state["terminal_result"],
        state["research_attempt_ledger"],
        state["effective_future_numeric_policy"],
    ):
        path = REPO_ROOT / binding["path"]
        assert campaign.file_sha256(path) == binding["sha256"]


def test_v59_preserves_133_definition_and_130_numeric_orders() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["status"] == (
        "frozen_after_campaign102_terminal_zero_survivors_before_campaign103_values"
    )
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 133
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 130
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "c80d9b929536dd509d6c1a904f790831050e68200393de381f92ad9293ef69e7"
    )
    assert numeric["campaign102_lambda_0_numeric_comparator_eligible"] is False
    assert policy["campaign102_terminal_model_trial_classification"][
        "future_same_family_lambda_reweight_bounds_relaxation_target_change_subset_rescue_or_retry_allowed"
    ] is False


def test_candidate49_and_action_boundaries_remain_closed() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["candidate49"]["remains_only_active_prospective_candidate"] is True
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49"]["ledgers_changed_by_campaign102"] is False
    assert state["provider_request_issued_by_campaign102"] is False
    assert state["current_scoring_selection_sizing_or_orders_performed"] is False


def test_env_credential_exists_without_reading_or_exposing_secret() -> None:
    path = REPO_ROOT / ".env"
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode)
    assert not path.is_symlink()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    keys = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            if key.strip() in {"TUSHARE_TOKEN", "TUSHARE_API_TOKEN"} and value.strip():
                keys.append(key.strip())
    assert keys == ["TUSHARE_TOKEN"]
    assert os.system(f"git check-ignore -q {path.name}") == 0
