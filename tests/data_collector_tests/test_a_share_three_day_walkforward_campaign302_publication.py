from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_short_horizon_factor_research as renderer


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign302_terminal.json"
)
TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_terminal_result_20260825.json"
)
ADJUDICATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_development_failure_adjudication_20260825.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_terminal_trial_ledger_20260825.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v432_20260825.json"
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
            "campaign302",
            str(entry["attempt_id"]),
            str(entry["previous_entry_sha256"]),
            str(entry["phase"]),
            str(entry["status"]),
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_campaign302_static_reference_graph_is_exact() -> None:
    state = _load(STATE_PATH)
    terminal = _load(TERMINAL_PATH)
    policy = _load(POLICY_PATH)
    ledger = _load(LEDGER_PATH)

    for binding in state["authoritative_inputs"].values():
        _assert_binding(binding)
    for binding in terminal["authoritative_inputs"].values():
        _assert_binding(binding)
    for binding in policy["authoritative_inputs"].values():
        _assert_binding(binding)
    _assert_binding(ledger["authoritative_predecessor"])
    for binding in ledger["source_bindings"].values():
        _assert_binding(binding)


def test_campaign302_freezes_bind_unchanged_runner_worker_and_tests() -> None:
    design = _load(
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_302_design_implementation_freeze_20260825.json"
    )
    development = _load(
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_302_development_execution_freeze_20260825.json"
    )

    for record in (design, development):
        for key in ("runner", "worker", "tests"):
            _assert_binding(record[key])
        assert record["dependencies"]["alpha360_loader_sha256"] == _sha256(
            REPO_ROOT / "qlib/contrib/data/loader.py"
        )
        assert record["dependencies"]["execution_engine_sha256"] == _sha256(
            REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign.py"
        )
        assert record["dependencies"]["campaign286_engine_sha256"] == _sha256(
            REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign286.py"
        )
    assert design["research_boundary"]["alpha360_feature_value_read_before_freeze"] is False
    assert design["research_boundary"]["historical_return_value_read_before_freeze"] is False
    assert development["research_boundary"]["training_or_validation_return_read_before_freeze"] is False


def test_campaign302_failure_is_terminal_before_validation_returns() -> None:
    terminal = _load(TERMINAL_PATH)
    adjudication = _load(ADJUDICATION_PATH)
    reached = terminal["reached_stage"]
    scientific = terminal["scientific_result"]

    assert reached["zero_return_design_fold_count"] == 3
    assert reached["persisted_training_feature_bytes"] == 54197216
    assert reached["fold1_training_rows"] == 8369
    assert reached["fold1_model_fit_completed"] is True
    assert reached["fold1_validation_alpha360_feature_pass_completed"] is True
    assert reached["fold1_validation_score_gate_completed"] is False
    assert reached["fold1_validation_score_snapshot_persisted"] is False
    assert reached["fold1_validation_return_read"] is False
    assert reached["validation_fold_return_read_count"] == 0
    assert scientific["development_survivor_count"] == 0
    assert scientific["candidate_predictive_quality_assessed"] is False
    assert scientific["predictive_rejection_claimed"] is False
    assert scientific["predictive_validation_claimed"] is False
    assert scientific["stress_2024_2025_opened"] is False
    assert adjudication["failure"]["same_campaign_retry_allowed"] is False
    assert adjudication["failure"]["frozen_runner_modified_after_failure"] is False
    assert adjudication["research_boundary"]["fold1_validation_forward_return_values_read"] is False


def test_campaign302_append_only_chain_and_accounting_are_complete() -> None:
    ledger = _load(LEDGER_PATH)
    entries = ledger["entries"]
    previous = ledger["authoritative_predecessor"]["sha256"]

    assert len(entries) == ledger["entry_count"] == 12
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["prevalue_concept_attempt_count"] == 8
    assert ledger["infrastructure_failure_attempt_count"] == 3
    assert ledger["complete_model_trial_attempt_count"] == 1
    assert ledger["return_reading_development_trial_count"] == 1
    assert ledger["validation_fold_return_read_count"] == 0
    assert ledger["cumulative_historical_research_attempts"] == 3119
    assert ledger["cumulative_return_reading_development_trials"] == 332


def test_campaign302_library_lockbox_and_candidate49_are_unchanged() -> None:
    policy = _load(POLICY_PATH)
    state = _load(STATE_PATH)

    assert policy["version"] == 432
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 172
    assert policy["complete_historical_feature_library"]["campaign302_definition_appended"] is False
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 153
    assert policy["numerical_comparator_eligibility"]["campaign302_numeric_comparator_appended"] is False
    assert policy["next_stage_boundary"]["campaign302_same_identifier_retry_allowed"] is False
    assert policy["next_stage_boundary"]["stress_2024_2025_allowed"] is False
    assert state["candidate49"]["same_day_retry_allowed"] is False
    assert state["candidate49"]["signal_ledger_entry_count"] == 0
    assert state["candidate49"]["execution_ledger_entry_count"] == 0
    assert state["candidate49"]["signal_ledger_sha256"] == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert state["candidate49"]["execution_ledger_sha256"] == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_campaign302_handoff_pipeline_and_renderer_are_published() -> None:
    state = _load(STATE_PATH)
    latest_handoff = REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825.md"
    campaign_handoff = (
        REPO_ROOT / "docs/a_share_three_day_strategy_handoff_20260825_campaign302.md"
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
    assert "截至 Campaign302" in latest_text
    assert "DatetimeIndex.eq()" in campaign_text
    assert "172/153" in campaign_text
    assert "Campaign302 完整 Alpha360 时序模型实现终止" in pipeline_text
    assert "历史滚动 Campaign302 权威追加" in rendered
    assert "验证收益读取 0 折" in rendered
    assert state["goal"]["current_strategy_campaign_complete"] is True
    assert state["workspace_boundary"]["external_data_change_may_be_staged_or_reverted"] is False
