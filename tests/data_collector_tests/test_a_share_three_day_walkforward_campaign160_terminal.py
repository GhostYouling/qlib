from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
INITIAL_FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_prevalue_infrastructure_failures_20260815.json"
)
INVENTORY = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_no_credential_source_contract_delta_inventory_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_no_credential_source_contract_delta_audit_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_160/research_attempt_ledger_v1.json"
)
TERMINAL_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_terminal_result_20260815.json"
)
PUBLICATION_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_unified_report_patch_context_failure_20260815.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_160/research_attempt_ledger_v2.json"
)
TERMINAL_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_160_terminal_result_v2_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v223_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign160_prevalue_terminal.json"
)
REPORT_V2 = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_160_terminal_report_v2.md"
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


def _entry_hash(entry: dict, previous: str) -> str:
    payload = "|".join(
        [
            "campaign160",
            entry["attempt_id"],
            previous,
            entry["phase"],
            entry["status"],
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign160_initial_and_publication_failures_are_preserved() -> None:
    initial = _load(INITIAL_FAILURES)
    assert len(initial["failures"]) == 3
    assert [item["exit_code"] for item in initial["failures"]] == [1, 1, 130]
    assert all(
        item["source_or_schema_opened_before_failure"] is False
        for item in initial["failures"]
    )
    assert all(
        item["partial_output_or_target_write"] is False for item in initial["failures"]
    )
    recovery = initial["safe_recovery"]
    assert recovery["akshare_import_spec_present"] is False
    assert (
        sum(item["matching_paths"] for item in recovery["fixed_cache_roots_checked"])
        == 0
    )
    assert recovery["package_install_or_network_recovery_attempted"] is False
    publication = _load(PUBLICATION_FAILURE)
    assert publication["failure"]["exit_code"] == 1
    assert publication["failure"]["target_files_written"] == 0
    assert publication["failure"]["partial_publication"] is False
    assert publication["failure"]["failed_exit_code_bypassed_or_masked"] is False


def test_campaign160_delta_inventory_is_finite_and_value_free() -> None:
    inventory = _load(INVENTORY)
    catalog = inventory["finite_source_contract_delta_catalog"]
    assert len(catalog) == 6
    assert len({item["catalog_id"] for item in catalog}) == 6
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in catalog
    )
    summary = inventory["inventory_summary"]
    assert summary["source_admission_deferrals_not_factor_failures"] == 2
    assert summary["terminal_source_field_schema_or_sample_reuse_rejections"] == 4
    assert summary["routes_with_locally_verifiable_complete_new_contract"] == 0
    assert summary["selected_candidate_count"] == 0
    boundary = inventory["research_boundary"]
    assert boundary["source_row_response_or_column_value_read"] is False
    assert boundary["candidate_or_comparator_value_read"] is False
    assert boundary["historical_daily_price_or_forward_return_value_read"] is False


def test_campaign160_evidence_registry_is_fully_bound() -> None:
    registry = _load(INVENTORY)["evidence_registry"]
    assert len(registry) == 6
    assert len({item["path"] for item in registry}) == 6
    for binding in registry:
        assert _sha(ROOT / binding["path"]) == binding["sha256"]


def test_campaign160_delta_gate_has_no_passer_and_preserves_deferrals() -> None:
    audit = _load(AUDIT)
    results = audit["route_gate_results"]
    assert len(results) == 6
    assert all(item["passed"] is False for item in results)
    assert sum(item["genuinely_new_economic_state"] for item in results) == 2
    assert sum(item["changed_source_evidence"] for item in results) == 0
    assert (
        sum(item["locally_verifiable_exact_source_contract"] for item in results) == 0
    )
    summary = audit["gate_summary"]
    assert summary["all_gate_passers"] == 0
    assert summary["source_admission_deferrals_not_factor_failures"] == 2
    assert summary["terminal_source_field_schema_or_sample_reuse_rejections"] == 4
    assert summary["selected_candidate_count"] == 0
    assert (
        audit["scientific_interpretation"]["deferred_routes_declared_ineffective"]
        is False
    )


def test_campaign160_effective_terminal_result_and_accounting() -> None:
    terminal = _load(TERMINAL_V2)
    assert (
        terminal["supersedes_without_rewriting"]["scientific_result_changed"] is False
    )
    scientific = terminal["unchanged_scientific_result"]
    assert scientific["terminal"] is True
    assert scientific["source_contract_routes_reviewed"] == 6
    assert scientific["source_admission_deferrals_not_factor_failures"] == 2
    assert scientific["terminal_source_field_schema_or_sample_reuse_rejections"] == 4
    assert scientific["selected_candidate_count"] == 0
    assert scientific["complete_source_contract_or_factor_definition_created"] is False
    assert (
        scientific[
            "source_row_response_candidate_comparator_daily_price_or_forward_return_values_read"
        ]
        is False
    )
    accounting = terminal["effective_accounting"]
    assert accounting["campaign160_attempt_count"] == 10
    assert accounting["campaign160_prevalue_scientific_attempt_count"] == 6
    assert accounting["campaign160_infrastructure_failure_count"] == 4
    assert accounting["cumulative_historical_research_attempt_count"] == 1396
    assert accounting["cumulative_return_reading_development_trial_count"] == 314


def test_campaign160_v1_and_delta_attempt_chains_are_exact() -> None:
    ledger_v1 = _load(LEDGER_V1)
    predecessor = ledger_v1["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1386
    previous = "0" * 64
    for entry in ledger_v1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = entry["entry_sha256"]
    assert len(ledger_v1["entries"]) == 9
    assert ledger_v1["chain_tip_sha256"] == previous
    ledger_v2 = _load(LEDGER_V2)
    assert ledger_v2["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    delta = ledger_v2["delta_entries"]
    assert len(delta) == 1
    assert delta[0]["previous_entry_sha256"] == previous
    assert delta[0]["entry_sha256"] == _entry_hash(delta[0], previous)
    assert ledger_v2["chain_tip_sha256"] == delta[0]["entry_sha256"]
    assert ledger_v2["effective_entry_count"] == 10
    assert ledger_v2["cumulative_historical_research_attempt_count"] == 1396


def test_campaign160_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    comparisons = features.reconstruct_comparisons()
    assert len(definitions) == 157
    assert features._order_digest(definitions) == (
        "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    policy = _load(POLICY)
    assert policy["complete_historical_feature_library"]["unchanged_from_v222"] is True
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v222"] is True


def test_campaign160_publication_bindings_are_current() -> None:
    records = (
        INITIAL_FAILURES,
        INVENTORY,
        AUDIT,
        TERMINAL_V1,
        PUBLICATION_FAILURE,
        TERMINAL_V2,
        POLICY,
        STATE,
    )
    for record_path in records:
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if isinstance(binding, dict) and "path" in binding:
                assert _sha(ROOT / binding["path"]) == binding["sha256"]
    state = _load(STATE)
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign160"]["terminal_result"]["sha256"] == _sha(TERMINAL_V2)
    assert state["campaign160"]["attempt_ledger"]["sha256"] == _sha(LEDGER_V2)
    assert state["reports"]["campaign160_effective_terminal_report"]["sha256"] == _sha(
        REPORT_V2
    )


def test_campaign160_candidate49_and_weekend_boundaries_are_unchanged() -> None:
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert len(_load(SIGNAL_LEDGER)["entries"]) == 0
    assert len(_load(EXECUTION_LEDGER)["entries"]) == 0
    state = _load(STATE)
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49"]["ledgers_changed"] is False
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False
    assert state["candidate49_daily_20260815"]["plan_run"] is False
    assert state["candidate49_daily_20260815"]["run_run"] is False


def test_campaign160_records_use_reached_wall_clock_timestamps() -> None:
    records = (
        INITIAL_FAILURES,
        INVENTORY,
        AUDIT,
        LEDGER_V1,
        TERMINAL_V1,
        PUBLICATION_FAILURE,
        LEDGER_V2,
        TERMINAL_V2,
        POLICY,
        STATE,
    )
    for record_path in records:
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign160_reports_are_effective_and_appended_once() -> None:
    heading = "## Campaign160 无高积分来源合同增量审查值前终止"
    assert "有效 v2" in REPORT_V2.read_text(encoding="utf-8")
    assert "6 次科学检查和 4 次基础设施失败" in REPORT_V2.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign160 共 10 次尝试（6 科学、4 基础设施）" in text


def test_campaign160_goal_remains_active_and_campaign161_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign160_scientific_decision_completed"] is True
    assert state["goal"]["campaign161_offline_scouting_authorized"] is True
    assert state["goal"]["campaign161_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
    assert state["research_boundary"]["stress_2024_2025_returns_opened"] is False
