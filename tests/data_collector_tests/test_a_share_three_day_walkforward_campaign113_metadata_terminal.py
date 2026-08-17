from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.a_share_official_exchange_enforcement import (
    EnforcementContractError,
    resolve_schema_roles,
)

ROOT = Path(__file__).resolve().parents[2]
FAILURE = (
    ROOT
    / "docs/a_share_official_exchange_enforcement_metadata_schema_failure_20260809.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_113/research_attempt_ledger_v5.json"
)
LEDGER_V6 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_113/research_attempt_ledger_v6.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_113_metadata_terminal_result_v3_20260809.json"
)
POLICY_V78 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v78_20260809.json"
)
POLICY_V79 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v79_20260809.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260809_campaign113_metadata_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_core_artifact_hashes_are_exact() -> None:
    assert _sha256(FAILURE) == (
        "ea44bd881db6f86fa311fe3c92f31aa465a1bdc845545a92bd2981ed917bbb65"
    )
    assert _sha256(LEDGER_V6) == (
        "de92a8f3e1ef5b3bd4ac03d8f7098dac746500014afdb1e54059ae0fe43f7726"
    )
    assert _sha256(RESULT) == (
        "42eb0e1c1b1310751386cfe9512b4e563670311e5efc8017479de5fad878c752"
    )
    assert _sha256(POLICY_V79) == (
        "28cc7103ca6e8a6079955fe871ad27479c6a5c11dd611aada1d15c6126da1ed8"
    )


def test_observed_szse_metadata_fails_the_frozen_exact_role_gate() -> None:
    failure = _load(FAILURE)
    regulatory = list(
        failure["szse_metadata_mapping"]["regulatory_measure"]["exact_columns"].values()
    )
    disciplinary = list(
        failure["szse_metadata_mapping"]["disciplinary_action"][
            "exact_columns"
        ].values()
    )
    with pytest.raises(EnforcementContractError):
        resolve_schema_roles(regulatory)
    with pytest.raises(EnforcementContractError):
        resolve_schema_roles(disciplinary)
    gate = failure["finite_role_schema_gate"]
    assert gate["sse"]["passed"] is True
    assert gate["szse_regulatory_measure"]["unresolved_required_roles"] == [
        "action_date",
        "document_link",
    ]
    assert gate["szse_disciplinary_action"]["unresolved_required_roles"] == [
        "action_type_or_family",
        "action_date",
        "document_link",
    ]
    assert gate["overall_passed"] is False


def test_metadata_probe_never_accessed_source_rows_or_protected_values() -> None:
    failure = _load(FAILURE)
    probe = failure["probe_boundary"]
    assert probe["szse_metadata_only_catalog_requests"] == 2
    assert probe["response_data_member_accessed"] is False
    assert probe["source_event_row_fields_read"] is False
    assert probe["source_event_row_count"] is None
    assert probe["historical_factor_or_comparator_values_read"] is False
    assert probe["price_or_forward_return_values_read"] is False
    terminal = failure["terminal_decision"]
    assert terminal["campaign113_terminal"] is True
    assert terminal["label_expansion_or_adapter_repair_allowed"] is False
    assert terminal["programmatic_source_row_acceptance_allowed"] is False


def test_v6_extension_chain_and_final_accounting_are_exact() -> None:
    prior = _load(LEDGER_V5)
    ledger = _load(LEDGER_V6)
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == _sha256(LEDGER_V5)
    assert extension["prior_chain_tip_sha256"] == prior["current_chain_tip_sha256"]
    previous = extension["prior_chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign113|"
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
    assert ledger["total_attempt_count"] == 17
    assert ledger["total_infrastructure_failure_count"] == 14
    assert ledger["total_prevalue_scientific_attempt_count"] == 3
    assert ledger["total_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 844
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_v79_preserves_v78_library_orders_and_terminalizes_campaign113() -> None:
    previous = _load(POLICY_V78)
    policy = _load(POLICY_V79)
    assert policy["supersedes_without_rewriting"]["sha256"] == _sha256(POLICY_V78)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"]
        == previous["complete_historical_feature_library"]["factor_definition_count"]
        == 141
    )
    assert (
        policy["complete_historical_feature_library"]["order_sha256"]
        == previous["complete_historical_feature_library"]["order_sha256"]
        == "ccab6e3d9d81b0a02d4ff178fdd442b26a1e68e3655e1c6f5b2fcb28cd4a4559"
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == previous["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_count"
        ]
        == 134
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
        == previous["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
        == "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
    )
    assert policy["campaign113_terminal_classification"]["terminal"] is True
    assert policy["campaign113_terminal_classification"]["numeric_snapshot_count"] == 0


def test_result_state_candidate49_and_sunday_boundaries_are_closed() -> None:
    result = _load(RESULT)
    state = _load(STATE)
    assert result["scientific_result"]["terminal"] is True
    assert result["scientific_result"]["development_trial_count"] == 0
    assert result["research_boundary"]["source_event_row_count"] is None
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
    for path in (FAILURE, LEDGER_V6, RESULT, POLICY_V79, STATE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified


def test_unified_reports_record_terminal_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_113_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "docs/a_share_data_pipeline.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign113 元数据终止" in text
        assert "844" in text
        assert "302" in text
        assert "v79" in text
        assert "Candidate49" in text
        assert "投资建议" in text
