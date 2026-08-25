from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign297 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign297_terminal.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v427_20260825.json"
)
DOCUMENTED_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_297_terminal_result_20260825.json"
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_binding(binding: dict[str, Any]) -> None:
    path = Path(str(binding["path"]))
    if not path.is_absolute():
        path = REPO_ROOT / path
    assert path.is_file()
    assert _sha256(path) == binding["sha256"]


def test_campaign297_terminal_publication_bindings_and_semantics() -> None:
    state = _load(STATE_PATH)
    policy = _load(POLICY_PATH)
    documented = _load(DOCUMENTED_TERMINAL_PATH)
    local_terminal = _load(campaign.TERMINAL_RESULT_PATH)
    no_return = _load(campaign.NO_RETURN_PATH)
    ledger = _load(campaign.TRIAL_LEDGER_PATH)

    for name in (
        "predecessor",
        "terminal_result",
        "terminal_report",
        "handoff",
        "latest_handoff_index",
        "numeric_policy_v427",
        "local_terminal_result",
        "terminal_trial_ledger",
        "library_order_reconstruction_receipt",
        "infrastructure_failure_record",
        "candidate49_same_day_plan_failure",
    ):
        _assert_binding(state["authoritative_inputs"][name])

    uniqueness = no_return["ordered_uniqueness"]
    assert local_terminal["status"] == "terminal_no_survivor_lockbox_closed"
    assert local_terminal["development_return_values_read"] is True
    assert local_terminal["validation_fold_count"] == 3
    assert local_terminal["survivor_count"] == 0
    assert local_terminal["definition_library_append_eligible"] is True
    assert no_return["coverage"]["gate_passed"] is True
    assert uniqueness["all_149_passed"] is True
    assert uniqueness["comparators_evaluated"] == 149
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.08685419208922868
    )
    assert no_return["historical_daily_price_or_forward_return_values_read"] is False
    assert ledger["entry_count"] == 11
    assert ledger["infrastructure_failure_count"] == 1
    assert documented["effective_accounting"]["campaign297_total_attempts"] == 11
    assert documented["development_result"]["current_strategy_deployable"] is False
    assert all(
        item["top3_minus_bottom3_gross_spread"] < 0
        for item in documented["development_result"]["folds"]
    )
    assert all(
        item["normalized_return"] < 0
        for item in documented["development_result"]["folds"]
    )

    library = policy["complete_historical_feature_library"]
    comparators = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 169
    assert library["campaign297_definition_appended"] is True
    assert library["order_sha256"] == (
        "b25aef820170480a3c43ec34096b603c39fa60923565be21040852a6df5b9fea"
    )
    assert comparators["eligible_numeric_comparator_count"] == 150
    assert comparators["campaign297_numeric_comparator_appended"] is True
    assert comparators["order_sha256"] == (
        "135dec87e00f39a78913e8b678c0c5e809f516c952575a9e406c360086a6508e"
    )


def test_campaign297_candidate49_and_lockbox_boundaries_unchanged() -> None:
    state = _load(STATE_PATH)
    policy = _load(POLICY_PATH)
    assert _sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["same_day_retry_allowed"] is False
    assert state["candidate49"]["signal_ledger_entry_count"] == 0
    assert state["candidate49"]["execution_ledger_entry_count"] == 0
    assert state["scientific_state"]["stress_2024_2025_opened"] is False
    assert policy["next_stage_boundary"]["stress_2024_2025_allowed"] is False
    assert policy["research_boundary"]["provider_api_request_issued"] is False
    assert (
        policy["research_boundary"][
            "current_scoring_selection_sizing_positions_or_orders_performed"
        ]
        is False
    )


def test_campaign297_handoff_is_latest_and_external_data_change_is_excluded() -> None:
    handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    ).read_text(encoding="utf-8")
    campaign_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign297.md"
    ).read_text(encoding="utf-8")
    state = _load(STATE_PATH)

    assert "截至 Campaign297" in handoff
    assert "a_share_three_day_strategy_handoff_20260825_campaign297.md" in handoff
    assert "Campaign298" in handoff
    assert "169/150" in handoff
    assert "149/149" in campaign_handoff
    assert "-27.00%" in campaign_handoff
    assert state["workspace_boundary"]["data_path_is_external_symlink"] is True
    assert (
        state["workspace_boundary"]["external_data_change_may_be_staged_or_reverted"]
        is False
    )
