from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.a_share_three_day_preregistration_binding_validator import (
    validate_record,
)


ROOT = Path(__file__).resolve().parents[2]
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_105_concept_scouting.json"
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_mechanism_support_audit.json"
)
PREREGISTRATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_no_return_preregistration.json"
)
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_prevalue_infrastructure_failures_20260808.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_105/research_attempt_ledger_v1.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260808_campaign105_preregistered.json"
)
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign105_prevalue_artifact_hashes_are_exact() -> None:
    assert (
        _sha256(CONCEPT)
        == "dc9116c62fef98f9aea0029cd24bf88d6be4c914cd7ba42d8b8604664f564d93"
    )
    assert (
        _sha256(AUDIT)
        == "8e1069159f2f807a1f783aba2ad173e0a167b5c67441d76e5604116c88415d45"
    )
    assert (
        _sha256(PREREGISTRATION)
        == "73d7c65b2e531ec613d4baed38bab0b4b507294c2a889db318fc9eec9bb5f126"
    )
    assert (
        _sha256(FAILURES)
        == "afb35fc0ae7898c2946ab98f2d82a362772d8dfcef53dfbd03fec652d418933e"
    )
    assert (
        _sha256(LEDGER)
        == "0fdb8cd770e04d83fea1f56f37355c2635bbf4e0496f4b928baf22f08ae45eac"
    )
    assert (
        _sha256(STATE)
        == "7403f909ce43bce779ac2de85b13862f6df1ebbfc78b5169be74796f87ec270e"
    )


def test_finite_catalog_selects_only_the_frozen_candidate() -> None:
    concept = _load(CONCEPT)
    catalog = concept["finite_prevalue_concept_catalog"]
    selected = [item for item in catalog if item["decision"].startswith("selected")]
    assert len(catalog) == 5
    assert [item["name"] for item in selected] == [
        "intraday_active_trading_bar_share_240m"
    ]
    assert concept["prevalue_decision"]["selected_candidate_count"] == 1
    assert (
        concept["prevalue_decision"]["candidate_may_advance_directly_to_values"]
        is False
    )
    boundary = concept["research_boundary"]
    assert boundary["campaign105_source_rows_read"] is False
    assert boundary["campaign105_candidate_values_computed_or_read"] is False
    assert boundary["campaign105_comparator_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_formula_and_support_predicate_are_frozen_without_hidden_thresholds() -> None:
    preregistration = _load(PREREGISTRATION)
    candidate = preregistration["candidate"]
    assert candidate["name"] == "intraday_active_trading_bar_share_240m"
    assert candidate["direction"] == "higher"
    assert candidate["source_projection"] == [
        "datetime",
        "symbol",
        "provider",
        "volume",
        "amount",
    ]
    assert candidate["source_grid"]["accepted_rows_required"] == 241
    assert candidate["source_grid"]["selected_rows"] == 240
    semantics = candidate["activity_semantics"]
    assert semantics["joint_zero"] == "valid inactive bar"
    assert semantics["one_sided_zero"] == "whole stock-day missing"
    assert semantics["joint_positive"] == "active bar"
    assert semantics["minimum_active_bar_count"] == 0
    assert semantics["positive_total_activity_required"] is False
    assert semantics["activity_magnitude_used"] is False
    assert semantics["clock_order_used_after_exact_grid_validation"] is False

    audit = _load(AUDIT)
    support = audit["mandatory_prevalue_support_predicate_gate"]
    assert (
        support["all_known_terminal_coverage_failures_through_campaign104_reviewed"]
        is True
    )
    assert len(support["known_failed_support_inventory"]) == 10
    assert support["candidate_support_identical_to_known_failed_predicate"] is False
    assert (
        support["candidate_support_provably_narrower_than_known_failed_predicate"]
        is False
    )
    assert support["decision"] == "pass_before_campaign105_source_rows_or_values"


def test_no_return_gates_reserve_all_131_comparisons_and_one_trial() -> None:
    preregistration = _load(PREREGISTRATION)
    comparison = preregistration["comparison_contract"]
    assert (
        comparison["complete_v62_semantic_definition_count_reviewed_before_values"]
        == 134
    )
    assert comparison["numeric_comparator_count"] == 131
    assert comparison["numeric_comparator_order_sha256"] == (
        "ab56a1791ae9a74b75d0a32cfb2346aa4bb6bfe266589be65825f8f51422f646"
    )
    gates = preregistration["ordered_no_return_gates"]
    assert [gate["gate"] for gate in gates] == [1, 2, 3]
    catalog = preregistration["finite_development_catalog_if_admitted"]
    assert catalog["trial_count"] == 1
    assert catalog["direction"] == "higher"
    assert [fold["validation"] for fold in catalog["folds"]] == [2021, 2022, 2023]
    assert "Purge three signal sessions" in catalog["purge"]
    assert "Open once" in catalog["stress_2024_2025"]


def test_preregistration_file_bindings_pass_before_implementation() -> None:
    for path in (CONCEPT, AUDIT, PREREGISTRATION):
        result = validate_record(path, data_root=DATA_ROOT)
        assert result["binding_count"] > 0
        assert result["failed_binding_count"] == 0
        assert result["all_bindings_passed"] is True


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 3
    assert ledger["infrastructure_failure_count"] == 2
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 778
    assert ledger["cumulative_return_reading_development_trial_count"] == 299
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign105|"
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
    assert previous == ledger["chain_tip_sha256"]


def test_state_preserves_candidate49_credential_and_saturday_boundaries() -> None:
    state = _load(STATE)
    assert state["local_session_status"]["accepted_local_trading_day"] is False
    assert (
        state["local_session_status"]["candidate49_provider_workflow_allowed_today"]
        is False
    )
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert (
        state["provider_request_accounting"][
            "campaign105_historical_research_provider_calls"
        ]
        == 0
    )
    assert (
        state["provider_request_accounting"]["candidate49_provider_calls_on_2026_08_08"]
        == 0
    )
    assert state["provider_credential"]["recognized_nonempty_token_key_count"] == 1
    assert (
        state["provider_credential"]["workflow_loader_observed_nonempty_token"] is True
    )
    assert (
        state["provider_credential"]["secret_printed_hashed_logged_or_persisted"]
        is False
    )
    assert (
        state["research_mode"]["current_listing_snapshot_survivorship_limitation"]
        is True
    )


def test_logical_timestamps_and_unified_reports_are_current() -> None:
    for path in (CONCEPT, AUDIT, PREREGISTRATION, FAILURES, LEDGER, STATE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified

    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_105_prevalue_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign105" in text
        assert "intraday_active_trading_bar_share_240m" in text
        assert "778" in text
        assert "299" in text
        assert "Candidate49" in text
