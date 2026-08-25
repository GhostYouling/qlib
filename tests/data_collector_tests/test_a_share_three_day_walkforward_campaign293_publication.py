from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign293 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign293_terminal.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v423_20260825.json"
)
DOCUMENTED_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_293_terminal_result_20260825.json"
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


def test_campaign293_terminal_publication_bindings_and_semantics() -> None:
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
        "numeric_policy_v423",
        "local_terminal_result",
        "terminal_trial_ledger",
        "library_order_reconstruction_receipt",
    ):
        _assert_binding(state["authoritative_inputs"][name])
    for binding in state["authoritative_inputs"][
        "infrastructure_failure_records"
    ]:
        _assert_binding(binding)

    assert local_terminal["status"] == "terminal_no_survivor_lockbox_closed"
    assert local_terminal["survivor_count"] == 0
    assert local_terminal["validation_fold_count"] == 3
    assert local_terminal["lockbox_2024_2025_returns_open"] is False
    assert no_return["coverage"]["gate_passed"] is True
    assert no_return["ordered_uniqueness"]["all_146_passed"] is True
    assert no_return["historical_daily_price_or_forward_return_values_read"] is False
    assert ledger["entry_count"] == 10
    assert documented["effective_accounting"]["campaign293_total_attempts"] == 13
    assert documented["development_result"]["survivor_count"] == 0
    assert state["scientific_state"]["current_strategy_deployable"] is False

    library = policy["complete_historical_feature_library"]
    comparators = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 166
    assert library["order_sha256"] == (
        "57662d72c897fc701f40a97e04946ebd9728b113587c7ad4f15c758be6ace06f"
    )
    assert comparators["eligible_numeric_comparator_count"] == 147
    assert comparators["order_sha256"] == (
        "5a771c4f9bd028b352194ec4779acb15b38ab6ab23a935458660b2024c7914c1"
    )


def test_campaign293_candidate49_and_production_boundaries_unchanged() -> None:
    state = _load(STATE_PATH)
    policy = _load(POLICY_PATH)
    assert _sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["signal_ledger_entry_count"] == 0
    assert state["candidate49"]["execution_ledger_entry_count"] == 0
    assert policy["research_boundary"]["provider_api_request_issued"] is False
    assert policy["research_boundary"]["stress_2024_2025_opened"] is False
    assert (
        policy["research_boundary"][
            "current_scoring_selection_sizing_positions_or_orders_performed"
        ]
        is False
    )


def test_campaign293_handoff_is_latest_and_external_data_change_is_excluded() -> None:
    handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    ).read_text(encoding="utf-8")
    campaign_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign293.md"
    ).read_text(encoding="utf-8")
    state = _load(STATE_PATH)

    assert "截至 Campaign293" in handoff
    assert "a_share_three_day_strategy_handoff_20260825_campaign293.md" in handoff
    assert "Campaign294" in handoff
    assert "166/147" in handoff
    assert "data` 被外部切换" in campaign_handoff
    assert state["workspace_boundary"]["data_path_is_external_symlink"] is True
    assert (
        state["workspace_boundary"]["external_data_change_may_be_staged_or_reverted"]
        is False
    )
