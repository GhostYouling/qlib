from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_short_horizon_factor_research as renderer
from scripts import a_share_three_day_walkforward_campaign300 as prior


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTIER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_301_prevalue_frontier_audit_20260825.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_301_prevalue_trial_ledger_20260825.json"
)
TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_301_terminal_result_20260825.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v431_20260825.json"
)
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign301_prevalue_terminal.json"
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


def _entry_hash(entry: dict[str, Any]) -> str:
    payload = "|".join(
        (
            "campaign301",
            str(entry["attempt_id"]),
            str(entry["previous_entry_sha256"]),
            str(entry["phase"]),
            str(entry["status"]),
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_campaign301_static_reference_graph_is_exact() -> None:
    state = _load(STATE_PATH)
    for binding in state["authoritative_inputs"].values():
        _assert_binding(binding)

    policy = _load(POLICY_PATH)
    terminal = _load(TERMINAL_PATH)
    for binding in policy["authoritative_inputs"].values():
        _assert_binding(binding)
    for binding in terminal["authoritative_inputs"].values():
        _assert_binding(binding)


def test_campaign301_finite_frontier_stops_before_values() -> None:
    frontier = _load(FRONTIER_PATH)
    catalog = frontier["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        f"c301_{ordinal:02d}" for ordinal in range(1, 12)
    ]
    assert len(catalog) == 11
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    assert all(item["decision"] != "selected" for item in catalog)
    assert catalog[-1]["decision"] == "deferred_alpha360_storage_headroom"
    assert "not a scientific rejection" in catalog[-1]["reason"]

    decision = frontier["decision"]
    assert decision["terminal_or_forbidden_route_count"] == 10
    assert decision["infrastructure_deferred_route_count"] == 1
    assert decision["selected_candidate_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["runner_or_feature_snapshot_created"] is False
    assert decision["candidate_or_comparator_value_read"] is False
    assert decision["historical_daily_price_or_forward_return_value_read"] is False
    assert decision["development_trial_count"] == 0
    assert decision["stress_trial_count_2024_2025"] == 0


def test_campaign301_append_only_prevalue_chain_and_accounting() -> None:
    ledger = _load(LEDGER_PATH)
    entries = ledger["entries"]
    previous = ledger["authoritative_predecessor"]["sha256"]
    assert len(entries) == ledger["entry_count"] == 11
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["prevalue_scientific_attempt_count"] == 11
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempts"] == 3107
    assert ledger["cumulative_return_reading_development_trials"] == 331


def test_campaign301_library_lockbox_candidate49_and_goal_boundaries() -> None:
    terminal = _load(TERMINAL_PATH)
    policy = _load(POLICY_PATH)
    state = _load(STATE_PATH)

    assert terminal["scientific_result"]["selected_candidate_count"] == 0
    assert terminal["scientific_result"]["development_survivor_count"] == 0
    assert terminal["scientific_result"]["current_strategy_deployable"] is False
    assert terminal["scientific_result"]["stress_2024_2025_opened"] is False
    assert policy["version"] == 431
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 172
    assert (
        policy["complete_historical_feature_library"][
            "campaign301_definition_appended"
        ]
        is False
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_count"
        ]
        == 153
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "campaign301_numeric_comparator_appended"
        ]
        is False
    )
    assert policy["next_stage_boundary"]["stress_2024_2025_allowed"] is False
    assert _sha256(prior.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(prior.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["same_day_retry_allowed"] is False
    assert state["candidate49"]["signal_ledger_entry_count"] == 0
    assert state["candidate49"]["execution_ledger_entry_count"] == 0
    assert state["goal"]["status"] == "active"
    assert "Campaign302" in state["goal"]["next_safe_work"]


def test_campaign301_handoff_pipeline_and_renderer_are_published() -> None:
    state = _load(STATE_PATH)
    latest_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    )
    campaign_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign301.md"
    )
    pipeline = REPO_ROOT / "docs/a_share_data_pipeline.md"
    renderer_path = REPO_ROOT / "scripts/a_share_short_horizon_factor_research.py"

    assert _sha256(latest_handoff) == state["publication_state"][
        "latest_handoff_index"
    ]["sha256_at_publication"]
    assert _sha256(pipeline) == state["publication_state"][
        "unified_pipeline_documentation"
    ]["sha256_at_publication"]
    assert _sha256(renderer_path) == state["publication_state"][
        "unified_report_renderer"
    ]["sha256_at_publication"]

    latest_text = latest_handoff.read_text(encoding="utf-8")
    campaign_text = campaign_handoff.read_text(encoding="utf-8")
    pipeline_text = pipeline.read_text(encoding="utf-8")
    rendered = renderer.append_historical_walkforward_terminal_summaries("base")
    assert "截至 Campaign301" in latest_text
    assert "Campaign302" in latest_text
    assert "172/153" in latest_text
    assert "11 条有限路线" in campaign_text
    assert "Alpha360" in campaign_text
    assert "Campaign301 Alpha158/日线残余前沿终局" in pipeline_text
    assert "历史滚动 Campaign301 权威追加" in rendered
    assert "172/153" in rendered
    assert state["workspace_boundary"]["data_path_is_external_symlink"] is True
    assert (
        state["workspace_boundary"][
            "external_data_change_may_be_staged_or_reverted"
        ]
        is False
    )
