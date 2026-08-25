from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign299 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign299_terminal.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v429_20260825.json"
)
DOCUMENTED_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_299_terminal_result_20260825.json"
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


def test_campaign299_terminal_publication_bindings_and_semantics() -> None:
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
        "numeric_policy_v429",
        "local_terminal_result",
        "terminal_trial_ledger",
        "library_order_reconstruction_receipt",
        "unified_pipeline_documentation",
        "unified_report_renderer",
        "candidate49_same_day_plan_failure",
    ):
        _assert_binding(state["authoritative_inputs"][name])
    for binding in state["authoritative_inputs"]["infrastructure_failure_records"]:
        _assert_binding(binding)

    uniqueness = no_return["ordered_uniqueness"]
    assert local_terminal["status"] == "terminal_no_survivor_lockbox_closed"
    assert local_terminal["development_return_values_read"] is True
    assert local_terminal["validation_fold_count"] == 3
    assert local_terminal["survivor_count"] == 0
    assert local_terminal["definition_library_append_eligible"] is True
    assert no_return["coverage"]["gate_passed"] is True
    assert uniqueness["all_151_passed"] is True
    assert uniqueness["comparators_evaluated"] == 151
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.08372414786893397
    )
    assert no_return["historical_daily_price_or_forward_return_values_read"] is False
    assert ledger["entry_count"] == 13
    assert ledger["infrastructure_failure_count"] == 2
    assert documented["effective_accounting"]["campaign299_total_attempts"] == 16
    assert documented["development_result"]["current_strategy_deployable"] is False
    assert all(
        item["mean_rank_ic"] < 0
        and item["normalized_return"] < 0
        and item["pilot_10bp_return"] < 0
        for item in documented["development_result"]["folds"]
    )
    assert (
        documented["development_result"]["aggregate"]["compounded_pilot_20bp_return"]
        < 0
    )
    assert (
        documented["development_result"]["aggregate"][
            "worst_validation_normalized_drawdown"
        ]
        < -0.25
    )

    library = policy["complete_historical_feature_library"]
    comparators = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 171
    assert library["campaign299_definition_appended"] is True
    assert library["order_sha256"] == (
        "b43cca1423094b1644e66130b6ef1b21680bbb023544ed6c99d73af515e4120e"
    )
    assert comparators["eligible_numeric_comparator_count"] == 152
    assert comparators["campaign299_numeric_comparator_appended"] is True
    assert comparators["order_sha256"] == (
        "f7cf9cf460464920a6bdfdafe0cf846fafd54862bb9837db3c7b808df341ae14"
    )


def test_campaign299_candidate49_and_lockbox_boundaries_unchanged() -> None:
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


def test_campaign299_handoff_and_unified_reports_are_latest() -> None:
    handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    ).read_text(encoding="utf-8")
    campaign_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign299.md"
    ).read_text(encoding="utf-8")
    pipeline = (REPO_ROOT / "docs/a_share_data_pipeline.md").read_text(encoding="utf-8")
    renderer = (
        REPO_ROOT / "scripts/a_share_short_horizon_factor_research.py"
    ).read_text(encoding="utf-8")
    state = _load(STATE_PATH)

    assert "截至 Campaign299" in handoff
    assert "a_share_three_day_strategy_handoff_20260825_campaign299.md" in handoff
    assert "Campaign300" in handoff
    assert "171/152" in handoff
    assert "151/151" in campaign_handoff
    assert "-46.60%" in campaign_handoff
    assert "Campaign299 离线历史终局" in pipeline
    assert "历史滚动 Campaign299 权威追加" in renderer
    assert state["workspace_boundary"]["data_path_is_external_symlink"] is True
    assert (
        state["workspace_boundary"]["external_data_change_may_be_staged_or_reverted"]
        is False
    )
    assert (
        state["workspace_boundary"]["unrelated_tracked_data_deletions_observed"] == 79
    )
