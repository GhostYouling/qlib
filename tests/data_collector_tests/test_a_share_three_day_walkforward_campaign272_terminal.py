from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_272_public_search_attention_source_contract_preregistration_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_272_terminal_source_contract_result_20260824.json"
)
LEDGERS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_272/research_attempt_ledger_v{version}.json"
    for version in (1, 2, 3, 4, 5, 6)
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign272_terminal.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_272_terminal_source_contract_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign272.md"
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED_REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else ROOT / target


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        target = _resolve(binding["path"])
        assert target.is_file()
        assert _sha256(target) == binding["sha256"]


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign272",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_preregistration_freezes_seven_conjunctive_gates_before_values() -> None:
    assert _sha256(PREREGISTRATION) == (
        "aa2d36e7a11a4bccc022f6d58e91848a5ddb772517a6c269b460b4640f75ca8e"
    )
    preregistration = _load(PREREGISTRATION)
    _assert_bindings(preregistration["authoritative_inputs"])
    gates = preregistration["finite_contract_gate_catalog"]
    assert [gate["gate_id"] for gate in gates] == [
        "c272_g01",
        "c272_g02",
        "c272_g03",
        "c272_g04",
        "c272_g05",
        "c272_g06",
        "c272_g07",
    ]
    locked = preregistration["locked_route"]
    for key in (
        "formula",
        "direction",
        "platform",
        "geography",
        "query_basket",
        "sampling_window",
        "source_fields",
    ):
        assert locked[key] is None
    rule = preregistration["decision_rule"]
    assert rule["partial_contract_not_admissible"] is True
    assert rule["provider_or_web_access_allowed_by_campaign272"] is False
    assert rule["terminalize_if_any_gate_fails"] is True


def test_result_rejects_all_seven_gates_and_terminalizes_c271_01() -> None:
    assert _sha256(RESULT) == (
        "b42f4ba49f6e5198a92ba46d44461b2f50c8de46d0991751cb22329ee3c48cc6"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    gates = result["contract_gate_results"]
    assert len(gates) == 7
    assert all(gate["passed"] is False for gate in gates)
    assert result["decision"]["all_seven_contract_gates_passed"] is False
    assert result["decision"]["source_contract_admitted"] is False
    assert result["decision"]["terminalize_c271_01"] is True
    assert result["decision"]["sibling_channel_or_parameter_rescue_allowed"] is False
    locked = result["locked_route"]
    assert locked["concept_is_factor"] is False
    assert locked["source_contract_or_adapter_created"] is False
    for key in (
        "formula",
        "direction",
        "platform",
        "geography",
        "query_basket",
        "sampling_window",
        "source_fields",
    ):
        assert locked[key] is None


def test_repository_inventory_is_zero_source_and_nonpredictive() -> None:
    result = _load(RESULT)
    inventory = result["bounded_repository_inventory"]
    assert inventory["query_family_file_match_counts"] == {
        "pit_issuer_brand_product_identity": 45,
        "platform_geography_sampling_archive": 24,
        "public_search_attention": 2,
        "query_basket_identity_ambiguity": 2,
        "zero_missing_all_issuer_denominator": 6,
    }
    assert inventory["targeted_adapter_and_artifact_counts"] == {
        "script_brand_product_identity_adapter": 0,
        "script_search_attention_adapter": 0,
        "tracked_search_attention_query_basket_or_brand_product_source_manifest_names": 0,
    }
    assert (
        inventory["accepted_local_public_search_attention_source_contract_present"]
        is False
    )
    assert inventory["accepted_local_unconsumed_raw_channel_present"] is False
    scientific = result["scientific_result"]
    assert scientific["complete_factor_definition_created"] is False
    assert scientific["numeric_comparator_created"] is False
    assert scientific["predictive_claim_created"] is False
    assert scientific["development_trial_count"] == 0
    assert scientific["stress_trial_count_2024_2025"] == 0


def test_append_only_attempt_chain_and_effective_accounting_are_exact() -> None:
    assert tuple(_sha256(path) for path in LEDGERS) == (
        "8019b7b99e27a58e0fa3194e2bc9d5983965853396bac0e05c255e227155dc63",
        "7efa1570f0dc4be04f08eb1effae218c001b4a41fd054c380e84baae6bc58d05",
        "6ca7cd1b251e618dff5f05c45ee62151a751b756b3ff8e72021e291eed17ad46",
        "ace2d5e3c5e2804484eb20fde0761aa96ea3836b0964911de6ae9a94920bab9f",
        "edf979c6cecb0086a0d8c17ed34f0469ddedea610c60cade4e2f4d438f6b0c09",
        "aeda5b6294adbd17c76e25b28838db689abb38b06cd6d332b373ad4b3707d110",
    )
    ledgers = [_load(path) for path in LEDGERS]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    assert (
        previous == "f238e7533364698e5dd274b15fb19ed661833d870b75ca0ba104988d0ee95da3"
    )
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 14
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert sum(entry["scientific_attempt"] for entry in entries) == 7
    assert sum(not entry["scientific_attempt"] for entry in entries) == 7
    assert sum(entry["result_consumed"] for entry in entries) == 7
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2767
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_library_campaign265_and_candidate49_unchanged() -> None:
    assert _sha256(STATE) == (
        "caa49e03087a394f3a9251faf1d07bd9b7ba8044a9ba05af5da556b21e87af83"
    )
    state = _load(STATE)
    _assert_bindings(state["authoritative_inputs"])
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert state["goal"]["current_campaign"] == 272
    assert "Campaign273" in state["goal"]["next_safe_work"]
    library = state["library_state"]
    assert library["changed_by_campaign272"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign272"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign272_plan_or_run_executed"] is False
    assert candidate49["historical_backfill_performed"] is False
    assert _sha256(SIGNAL) == candidate49["signal_ledger_sha256"]
    assert _sha256(EXECUTION) == candidate49["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_no_value_provider_stress_or_current_use_boundary_is_closed() -> None:
    artifacts = [_load(PREREGISTRATION), _load(RESULT), _load(STATE)]
    artifacts.extend(_load(path) for path in LEDGERS)
    for artifact in artifacts:
        boundary = artifact["research_boundary"]
        for key, value in boundary.items():
            if key == "repository_metadata_and_prior_terminal_history_read":
                assert value is True
            else:
                assert value is False


def test_reports_publish_one_terminal_section_without_a_trading_claim() -> None:
    report = REPORT.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "预测价值没有测试" in report
    assert "不授权当前评分、选股、仓位或订单" in report
    assert "结论是终止" in handoff
    assert "Campaign273" in handoff
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        title = "## Campaign272：公共搜索关注来源合同值前终止（2026-08-24）"
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "七项门全部失败" in section
        assert "预测价值没有测试" in section
        assert "Candidate49 同日失败继续封口且账本 0/0" in section
        assert "不构成投资建议" in section
