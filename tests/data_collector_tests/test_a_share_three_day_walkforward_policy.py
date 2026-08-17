from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_historical_walkforward_research_policy_20260727.json"
)
STATUS_PATH = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260727_walkforward.json"
)
CAMPAIGN004_STATUS_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_iteration_status_20260728_campaign004.json"
)
CAMPAIGN004_RECORD_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_004_research_record.json"
)
PREVIOUS_STATUS_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_iteration_status_20260725_future_only.json"
)
CANDIDATE49_POLICY_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_future_only_minute_research_policy_20260725.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_walkforward_policy_freezes_expected_splits_and_three_session_purge() -> None:
    policy = _load(POLICY_PATH)

    assert policy["kind"] == "a_share_three_day_historical_walkforward_research_policy"
    folds = policy["dataset_roles"]["development_and_inner_walkforward"][
        "expanding_folds"
    ]
    assert [
        (
            fold["training"]["start"],
            fold["training"]["end"],
            fold["validation"]["start"],
            fold["validation"]["end"],
        )
        for fold in folds
    ] == [
        ("2019-01-01", "2020-12-31", "2021-01-01", "2021-12-31"),
        ("2019-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
        ("2019-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ]
    locked = policy["dataset_roles"]["locked_historical_backtest"]
    assert (locked["start"], locked["end"]) == ("2024-01-01", "2025-12-31")
    assert policy["three_session_leakage_controls"][
        "purge_before_every_split_local_signal_sessions"
    ] == 3
    assert "t+1" in policy["three_session_leakage_controls"]["label_containment"]
    assert "t+3" in policy["three_session_leakage_controls"]["label_containment"]


def test_walkforward_policy_requires_complete_append_only_trial_ledger() -> None:
    policy = _load(POLICY_PATH)
    ledger = policy["trial_and_multiplicity_ledger"]

    assert ledger["required"] is True
    assert ledger["append_only"] is True
    assert "trial_id" in ledger["minimum_fields"]
    assert "parent_trial_id" in ledger["minimum_fields"]
    assert "locked_backtest_metrics_when_opened" in ledger["minimum_fields"]
    assert "every attempted formula" in ledger["counting_rule"]


def test_walkforward_policy_preserves_candidate49_future_only_identity() -> None:
    policy = _load(POLICY_PATH)
    candidate49 = policy["candidate49_preservation"]

    assert candidate49["historical_return_diagnostic_allowed"] is False
    assert candidate49["historical_signal_or_execution_backfill_allowed"] is False
    assert candidate49["future_ledger_semantics_changed"] is False
    assert candidate49["candidate49_no_longer_blocks_historical_walkforward_research"]
    assert (
        policy["promotion_and_live_boundary"][
            "candidate50_prospective_activation_while_candidate49_active"
        ]
        is False
    )


def test_walkforward_status_advances_exact_fingerprinted_predecessors() -> None:
    policy = _load(POLICY_PATH)
    status = _load(STATUS_PATH)

    assert _sha256(POLICY_PATH) == (
        "38426d6161b9bfed323c58caba18feca668b8c9d53e294951a8ba90c01a798bb"
    )
    assert _sha256(STATUS_PATH) == (
        "75e639c4b8579983bfcda8da19c221d018b7b62cd68fac9e94822f6c3ed73267"
    )
    assert status["governance_policy"]["sha256"] == _sha256(POLICY_PATH)
    assert status["previous_authoritative_state"]["sha256"] == _sha256(
        PREVIOUS_STATUS_PATH
    )
    assert status["preserved_future_only_policy"]["sha256"] == _sha256(
        CANDIDATE49_POLICY_PATH
    )
    assert policy["governance_scope"]["advances_without_rewriting"][
        "sha256"
    ] == _sha256(CANDIDATE49_POLICY_PATH)
    assert status["decision"]["offline_historical_research_allowed_while_candidate49_active"]
    assert status["decision"]["historical_factor_combination_research_allowed"]
    assert status["decision"]["candidate49_historical_return_diagnostic_allowed"] is False
    assert status["decision"]["orders_allowed"] is False


def test_campaign004_status_advances_without_rewriting_candidate49() -> None:
    status = _load(CAMPAIGN004_STATUS_PATH)

    assert _sha256(CAMPAIGN004_STATUS_PATH) == (
        "2037007da4fe750b70715b9f0cf7e8d361cb9d6d18128fdb6c18b05486954749"
    )
    assert status["previous_authoritative_state"]["sha256"] == _sha256(STATUS_PATH)
    assert status["active_prospective_candidate"]["ordinal"] == 49
    assert status["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert (
        status["active_prospective_candidate"]["execution_ledger"]["entry_count"]
        == 0
    )
    assert status["research_counts"]["completed_historical_walkforward_campaign_count"] == 4
    assert status["research_counts"]["recorded_historical_development_trial_count"] == 230
    assert status["research_counts"]["campaign004_development_survivor_count"] == 0
    assert status["decision"]["candidate50_prospective_activation_allowed_while_candidate49_active"] is False
    assert status["decision"]["current_scoring_allowed"] is False
    assert status["decision"]["orders_allowed"] is False


def test_campaign004_record_closes_stress_and_routes_only_to_new_no_return_work() -> None:
    status = _load(CAMPAIGN004_STATUS_PATH)
    record = _load(CAMPAIGN004_RECORD_PATH)
    campaign = status["completed_historical_walkforward_campaigns"][-1]

    assert campaign["campaign_id"] == "a_share_three_day_walkforward_campaign_004"
    assert campaign["research_record"]["sha256"] == _sha256(CAMPAIGN004_RECORD_PATH)
    assert _sha256(CAMPAIGN004_RECORD_PATH) == (
        "6e0dd1295a75c1f3eebe70a5cf327d98490bd76a43b307cf5fb416013d60c88e"
    )
    assert record["no_return_admission"]["audit"]["admissible_factor_count"] == 3
    assert record["development_result"]["frozen_trial_count"] == 12
    assert record["development_result"]["selected_exposed_stress_survivor_count"] == 0
    assert record["exposed_stress_result"]["interval_opened"] is False
    assert record["exposed_stress_result"]["return_fields_read"] is False
    assert record["research_boundary"]["candidate49_historical_return_read"] is False
    assert record["research_boundary"]["candidate50_prospective_activation_created"] is False
    assert record["next_iteration"]["campaign_id"] == (
        "a_share_three_day_walkforward_campaign_005"
    )
    assert "not_yet_frozen" in record["next_iteration"][
        "formula_direction_and_parameter_status"
    ]
