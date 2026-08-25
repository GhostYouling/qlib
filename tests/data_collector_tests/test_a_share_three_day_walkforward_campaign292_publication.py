from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign292 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign292_terminal.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v422_20260825.json"
)
DOCUMENTED_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_terminal_result_20260825.json"
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


def test_campaign292_terminal_publication_bindings_and_semantics() -> None:
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
        "numeric_policy_v422",
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
    assert no_return["ordered_uniqueness"]["all_145_passed"] is True
    assert no_return["historical_daily_price_or_forward_return_values_read"] is False
    assert ledger["entry_count"] == 11
    assert documented["effective_accounting"]["campaign292_total_attempts"] == 12
    assert (
        documented["effective_accounting"][
            "campaign292_terminal_trial_ledger_entries"
        ]
        == 11
    )
    assert documented["development_result"]["survivor_count"] == 0
    assert state["scientific_state"]["current_strategy_deployable"] is False

    library = policy["complete_historical_feature_library"]
    comparators = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 165
    assert library["order_sha256"] == (
        "bf2f4640dc232a837690717e9be25eb824007cde801df6704756e72dab82c127"
    )
    assert comparators["eligible_numeric_comparator_count"] == 146
    assert comparators["order_sha256"] == (
        "f9abd8653a44f923fc03565b4397d9e1434c660ff6647b7b538b0e65091a8344"
    )


def test_campaign292_candidate49_and_production_boundaries_unchanged() -> None:
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


def test_campaign292_reports_are_unified_and_handoff_is_latest() -> None:
    current = (
        REPO_ROOT / "data/experiments/short_horizon/current_research_report.md"
    ).read_text(encoding="utf-8")
    three_day = (
        REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text(encoding="utf-8")
    handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    ).read_text(encoding="utf-8")
    marker = "## Campaign292：Alpha158 同日同行百分位极端度广度终止"
    assert marker in current
    assert marker in three_day
    assert current[current.index(marker) :] == three_day[three_day.index(marker) :]
    assert "截至 Campaign292" in handoff
    assert "a_share_three_day_strategy_handoff_20260825_campaign292.md" in handoff
    assert "Campaign293" in handoff
