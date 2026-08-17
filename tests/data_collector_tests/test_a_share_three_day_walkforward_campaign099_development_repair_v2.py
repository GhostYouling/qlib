from __future__ import annotations

from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign099 as campaign
from scripts import (
    a_share_three_day_walkforward_campaign099_development_repair_v2 as repair,
)


ROOT = Path(__file__).resolve().parents[2]


def test_repair_prerequisites_are_immutable() -> None:
    assert repair._sha256(repair.ORIGINAL_RUNNER) == repair.ORIGINAL_RUNNER_SHA256
    assert repair._sha256(repair.PREREGISTRATION) == repair.PREREGISTRATION_SHA256
    assert repair._sha256(repair.FAILURE_RECORD) == repair.FAILURE_RECORD_SHA256
    assert repair._sha256(repair.PRE_REPAIR_LEDGER) == repair.PRE_REPAIR_LEDGER_SHA256


def test_pre_retry_ledger_contains_only_recorded_infrastructure_failure() -> None:
    ledger = repair._validate_pre_retry_trial_ledger()
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0]["phase"] == "infrastructure_failure"
    assert not any(
        entry["phase"] == "development_walkforward" for entry in ledger["entries"]
    )


def test_nested_loader_repair_changes_only_manifest_binding_and_restores() -> None:
    globals_dict = campaign._load_compact_factor_panel.__globals__
    original = {
        name: globals_dict[name]
        for name in (
            "CANDIDATE_MANIFEST",
            "CANDIDATE_MANIFEST_SHA256",
            "CANDIDATE_DATASET_SHA256",
        )
    }
    assert original["CANDIDATE_MANIFEST"] == repair.NONCOMPACT_MANIFEST
    with repair._temporary_nested_loader_binding_repair():
        assert globals_dict["CANDIDATE_MANIFEST"] == campaign.COMPACT_MANIFEST
        assert (
            globals_dict["CANDIDATE_MANIFEST_SHA256"]
            == campaign.COMPACT_MANIFEST_SHA256
        )
        assert (
            globals_dict["CANDIDATE_DATASET_SHA256"] == campaign.COMPACT_DATASET_SHA256
        )
        assert globals_dict["ADMITTED_FACTOR"] == campaign.ADMITTED_FACTOR
        assert globals_dict["EXPECTED_ROWS"] == campaign.EXPECTED_ROWS
        assert globals_dict["EXPECTED_ELIGIBLE_ROWS"] == campaign.EXPECTED_ELIGIBLE_ROWS
    assert {
        name: globals_dict[name]
        for name in (
            "CANDIDATE_MANIFEST",
            "CANDIDATE_MANIFEST_SHA256",
            "CANDIDATE_DATASET_SHA256",
        )
    } == original


def test_repair_activation_is_fail_closed_and_does_not_open_stress() -> None:
    activation = repair._load_repair_activation()
    assert activation["remaining_complete_development_trials_authorized"] == 1
    assert activation["stress_2024_2025_authorized"] is False
    assert activation["provider_request_authorized"] is False
    assert (
        activation[
            "formula_direction_window_threshold_filter_subset_cost_model_or_gate_change_authorized"
        ]
        is False
    )
