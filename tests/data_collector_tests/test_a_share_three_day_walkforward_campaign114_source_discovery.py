from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONCEPT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_114_concept_scouting_20260809.json"
)
PROTOCOL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_114_source_discovery_protocol_20260809.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_114/research_attempt_ledger_v1.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_114/research_attempt_ledger_v2.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_114_prevalue_source_discovery_result_v2_20260809.json"
)
POLICY_V80 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v80_20260809.json"
)
POLICY_V81 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v81_20260809.json"
)
POLICY_V82 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v82_20260809.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260809_campaign114_source_discovery_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign114_core_artifact_hashes_are_exact() -> None:
    assert _sha256(CONCEPT) == (
        "381b0644fd981d862d3a5e3df036c56c11379ff89d9f51d6b83694d83a158745"
    )
    assert _sha256(PROTOCOL) == (
        "4f345109f48c534fbe4f7f577aefca7a5da0de804598b6c6548e682b99e4a199"
    )
    assert _sha256(LEDGER) == (
        "d7167c0ce582e89cea4f14f1626e35336dd0c0840e4d4442d1f9a992d5aa9a75"
    )
    assert _sha256(RESULT) == (
        "a1d6e0d2a961f873fa502027539b4963cd8658397137cc0b8e9e4658142c0b2c"
    )
    assert _sha256(POLICY_V82) == (
        "c68165a819eb483a02c41d7803a153457fa02194f192b458dfe41204f4f95365"
    )


def test_finite_catalog_selects_one_metadata_only_candidate() -> None:
    concept = _load(CONCEPT)
    catalog = concept["finite_prevalue_concept_catalog"]
    selected = [
        item
        for item in catalog
        if item["decision"] == "selected_for_metadata_only_source_discovery"
    ]
    assert len(catalog) == 6
    assert len(selected) == 1
    assert selected[0]["name"] == (
        "official_exchange_information_disclosure_evaluation_grade"
    )
    decision = concept["prevalue_decision"]
    assert decision["complete_logical_definitions_reviewed"] == 141
    assert decision["rejected_concept_count"] == 5
    assert decision["selected_candidate_count"] == 1
    assert decision["campaign114_complete_factor_definition_count"] == 0
    assert decision["formula_direction_mapping_window_or_missing_rule_frozen"] is False
    assert (
        decision["campaign114_source_rows_attachments_or_values_may_be_read"] is False
    )


def test_protocol_is_two_exchange_metadata_only_and_fail_closed() -> None:
    protocol = _load(PROTOCOL)
    source = protocol["selected_source_family"]
    assert source["mandatory_publishers"] == [
        "Shanghai Stock Exchange",
        "Shenzhen Stock Exchange",
    ]
    assert source["mandatory_archive_years"] == list(range(2019, 2026))
    assert protocol["finite_search_vocabulary"] == [
        "信息披露工作评价",
        "信息披露考核",
        "信息披露评价结果",
    ]
    gate = protocol["acceptance_gate"]
    assert gate["both_exchanges_must_pass"] is True
    assert gate["success_does_not_authorize_attachment_or_issuer_row_access"] is True
    failure = protocol["failure_policy"]
    assert failure["one_exchange_research_path_allowed"] is False
    assert failure["third_party_fill_allowed"] is False
    assert failure["formula_or_mapping_rescue_allowed"] is False
    forbidden = " ".join(protocol["forbidden_actions"])
    assert "Open, download" in forbidden
    assert "issuer code" in forbidden
    boundary = protocol["research_boundary_at_freeze"]
    assert boundary["official_exchange_archive_page_opened"] is False
    assert boundary["source_rows_read_persisted_or_counted"] is False


def test_append_only_chain_and_attempt_accounting_are_exact() -> None:
    original = _load(LEDGER_V1)
    ledger = _load(LEDGER)
    inputs = original["authoritative_predecessor"]
    genesis_payload = (
        "campaign114|genesis|"
        + inputs["iteration_state"]["sha256"]
        + "|"
        + inputs["numeric_policy_v80"]["sha256"]
        + "|"
        + inputs["historical_walkforward_policy"]["sha256"]
    ).encode()
    previous = hashlib.sha256(genesis_payload).hexdigest()
    assert previous == original["genesis_sha256"]
    for entry in original["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign114|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == _sha256(LEDGER_V1)
    assert extension["prior_chain_tip_sha256"] == previous
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign114|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["current_chain_tip_sha256"]
    assert ledger["total_attempt_count"] == 5
    assert ledger["total_infrastructure_failure_count"] == 4
    assert ledger["total_prevalue_scientific_attempt_count"] == 1
    assert ledger["total_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 850
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_v82_preserves_v81_library_and_numeric_comparator_orders() -> None:
    previous = _load(POLICY_V81)
    policy = _load(POLICY_V82)
    assert policy["supersedes_without_rewriting"]["sha256"] == _sha256(POLICY_V81)
    library = policy["complete_historical_feature_library"]
    assert library["factor_definition_count"] == 141
    assert (
        library["order_sha256"]
        == previous["complete_historical_feature_library"]["order_sha256"]
    )
    assert library["order_sha256"] == (
        "ccab6e3d9d81b0a02d4ff178fdd442b26a1e68e3655e1c6f5b2fcb28cd4a4559"
    )
    comparators = policy["numerical_comparator_eligibility"]
    assert comparators["eligible_numeric_comparator_count"] == 134
    assert (
        comparators["eligible_numeric_comparator_order_sha256"]
        == previous["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert comparators["eligible_numeric_comparator_order_sha256"] == (
        "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
    )
    classification = policy["campaign114_prevalue_classification"]
    assert classification["complete_factor_definition_count"] == 0
    assert classification["numeric_snapshot_count"] == 0
    assert classification["development_trial_count"] == 0
    assert classification["stress_2024_2025_opened"] is False


def test_result_state_candidate49_and_sunday_boundaries_are_closed() -> None:
    result = _load(RESULT)
    state = _load(STATE)
    scientific = result["scientific_result"]
    assert scientific["campaign114_terminal"] is False
    assert scientific["source_contract_frozen"] is False
    assert scientific["historical_predictive_value_established"] is False
    assert (
        result["research_boundary"]["source_rows_accessed_persisted_or_counted"]
        is False
    )
    assert state["local_session_status"]["accepted_local_trading_day"] is False
    assert state["local_session_status"]["candidate49_plan_or_run_executed"] is False
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["provider_credential"]["tushare_token_entry_count"] == 1
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert (
        state["provider_credential"]["secret_printed_hashed_logged_or_persisted"]
        is False
    )


def test_new_logical_timestamps_do_not_postdate_file_writes() -> None:
    for path in (CONCEPT, PROTOCOL, LEDGER, RESULT, POLICY_V82, STATE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified


def test_unified_reports_record_prevalue_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_114_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "docs/a_share_data_pipeline.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign114" in text
        assert "v82" in text
        assert "850" in text
        assert "302" in text
        assert "Candidate49" in text
        assert "投资建议" in text
