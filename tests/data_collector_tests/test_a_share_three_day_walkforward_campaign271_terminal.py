from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_271_external_attention_concept_scouting_preregistration_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_271_external_attention_concept_scouting_result_20260824.json"
)
LEDGERS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_271/research_attempt_ledger_v{version}.json"
    for version in (1, 2, 3, 4, 5, 6, 7, 8)
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign271_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_271_terminal_report.md"
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign271.md"
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
            "campaign271",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_was_frozen_before_targeted_search_with_sequence_disclosed() -> None:
    assert _sha256(PREREGISTRATION) == (
        "1f7dd8d354cd0120669a0a226b1f257d9743ebe6a37a26d1559ee7997be77169"
    )
    preregistration = _load(PREREGISTRATION)
    _assert_bindings(preregistration["authoritative_inputs"])
    assert preregistration["sequence_disclosure"] == {
        "broad_filename_inventory_already_observed": True,
        "classification": (
            "infrastructure_sequence_deviation_recorded_before_targeted_content_search"
        ),
        "scope_observed": (
            "Tracked concept/frontier/source filenames for Campaign118-Campaign270 "
            "only."
        ),
        "value_or_source_row_observed": False,
        "effect_on_catalog": (
            "The exact six-route catalog, priority order, decision rule and query "
            "families below were still frozen before any targeted repository "
            "content search. The preliminary filename inventory is recorded as "
            "Campaign271 infrastructure failure 004 and is not hidden or treated "
            "as scientific evidence."
        ),
    }
    catalog = preregistration["finite_concept_catalog"]
    assert [route["route_id"] for route in catalog] == [
        "c271_01",
        "c271_02",
        "c271_03",
        "c271_04",
        "c271_05",
        "c271_06",
    ]
    for route in catalog:
        for key in (
            "formula",
            "direction",
            "source_fields",
            "query_basket",
            "window_or_threshold",
        ):
            assert route[key] is None
    rule = preregistration["decision_rule"]
    assert rule["preserve_count_maximum"] == 1
    assert rule["preserved_route_is_factor"] is False
    assert rule["formula_direction_or_value_access_allowed"] is False


def test_result_preserves_only_search_attention_as_a_nonfactor() -> None:
    assert _sha256(RESULT) == (
        "dadfa6372870b2392d43880adfbb0100973a52ba4c8494276aa32d810230efbd"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    decisions = result["route_decisions"]
    assert len(decisions) == 6
    assert decisions[0]["route_id"] == "c271_01"
    assert decisions[0]["decision"] == "preserve_for_separate_zero_row_source_contract"
    assert decisions[0]["classification"] == "concept_selected_not_factor_admitted"
    assert all(
        decision["decision"] != "preserve_for_separate_zero_row_source_contract"
        for decision in decisions[1:]
    )
    for decision in decisions:
        assert decision["formula"] is None
        assert decision["direction"] is None
        assert decision["source_fields"] is None
        assert decision["candidate_or_comparator_value_read"] is False
    selection = result["selection"]
    assert selection["selected_concept_id"] == "c271_01"
    assert selection["selected_concept_is_not_a_factor"] is True
    assert (
        selection["selected_concept_does_not_authorize_source_or_value_access"] is True
    )
    assert "Terminalize c271_01" in selection["fallback_if_contract_cannot_close"]


def test_targeted_repository_evidence_is_exact_and_nonpredictive() -> None:
    result = _load(RESULT)
    evidence = result["targeted_repository_search_evidence"]
    assert evidence["query_family_file_match_counts"] == {
        "public_search_attention": 2,
        "website_audience_traffic": 0,
        "mobile_app_store_rank_download_engagement": 0,
        "ecommerce_product_demand_review": 0,
        "online_vacancy_job_posting_demand": 1,
        "public_social_discussion_reputation": 1,
    }
    assert "Campaign114" in evidence["public_search_attention_match_interpretation"]
    assert "board-seat vacancy" in evidence["vacancy_match_interpretation"]
    assert "Campaign207" in evidence["social_match_interpretation"]
    assert evidence["accepted_local_external_attention_raw_channel_present"] is False
    assert evidence["provider_or_web_request_issued"] is False
    assert evidence["source_row_or_research_value_read"] is False
    gate = result["gate_summary"]
    assert gate["selected_factor_count"] == 0
    assert gate["complete_factor_definition_created"] is False
    assert gate["development_trial_count"] == 0
    assert gate["stress_trial_count_2024_2025"] == 0


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    expected_hashes = (
        "e9b8d784a63b66309c7baac1626549282727d773cb79e7ae7c6fc27760b8ace5",
        "4d03dffa3c796a592ff847c10566848d5d700ed8e4cf500d86b3ae985affdbd9",
        "3e873cd06fe507431b267ca7cfe42bbdc4f2e050cbc0d308380f8822df19217c",
        "4ff8b374318881b9dd42e98933e4a6672f2e263332a7e0d8e8eef90cc25cd9bd",
        "e373b7099cd81a7e76668f2b348fcb08df88c348fe764ee3fcfd894e307579b7",
        "5e5e8e280f1edf2f8ad7928989fa71d7785d873382614e8a4cccdc8af669124a",
        "426ff30d5d91ef6cd9347e3bb3ae3c164b371bd164433bff81b42feba676a71d",
        "c992fd5dd95f29329071ac6b031803bc23df58c554ffbf5839089840c522b2c6",
    )
    assert tuple(_sha256(path) for path in LEDGERS) == expected_hashes
    ledgers = [_load(path) for path in LEDGERS]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 16
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert sum(not entry["scientific_attempt"] for entry in entries) == 10
    assert sum(entry["scientific_attempt"] for entry in entries) == 6
    assert sum(entry["result_consumed"] for entry in entries) == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2753
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_goal_library_campaign265_and_candidate49_are_unchanged() -> None:
    state = _load(STATE)
    _assert_bindings(state["authoritative_inputs"])
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert state["goal"]["current_campaign"] == 271
    assert "Campaign272" in state["goal"]["next_safe_work"]
    scientific = state["scientific_state"]
    assert scientific["preserved_concept_id"] == "c271_01"
    assert scientific["preserved_concept_is_factor"] is False
    assert scientific["selected_factor_count"] == 0
    assert scientific["predictive_claim_created"] is False
    library = state["library_state"]
    assert library["changed_by_campaign271"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign271"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign271_plan_or_run_executed"] is False
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
    assert "预测价值没有被测试" in report
    assert "不授权当前评分、选股、仓位或订单" in report
    assert "不是因子" in handoff
    assert "Campaign272" in handoff
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        title = "## Campaign271：外部公共搜索关注概念前沿（2026-08-24）"
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert (
            "只保留 `c271_01 issuer_brand_product_public_search_attention_state`"
            in section
        )
        assert "预测价值没有测试" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "不构成投资建议" in section
