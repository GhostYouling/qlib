"""Frozen development-boundary tests for Campaign048."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign048_v2 as campaign


CAMPAIGN_SHA256 = (
    "05d8bb6b45dac88a03583e87baf9bd15fc9cd88340ba7a024333e1ca9772bef1"
)
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")


def test_campaign048_preregistration_and_exact_pre_value_trial_are_frozen() -> None:
    path = campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    result = bindings.validate_record(path, data_root=DATA_ROOT)
    assert result["all_bindings_passed"] is True
    spec, observed_sha256 = campaign.load_campaign(path)
    assert observed_sha256 == CAMPAIGN_SHA256
    protocol = json.loads(
        (
            campaign.REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"
        ).read_text()
    )
    exact_trial = protocol["finite_development_catalog_if_admitted"]["trial_id"]
    assert campaign.build_trial_catalog(spec) == [
        {
            "trial_id": exact_trial,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.ADMITTED_FACTOR],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_campaign048_folds_search_and_stress_boundary_are_closed() -> None:
    spec, _ = campaign.load_campaign(
        campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert len(spec["walkforward_folds"]) == 3
    assert spec["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert spec["split_protocol"]["label_containment_required"] is True
    assert spec["search_space"]["expected_trial_count"] == 1
    assert spec["search_space"]["weight_fitting"] is False
    assert spec["search_space"]["threshold_search"] is False
    assert spec["search_space"]["year_subset_search"] is False
    assert spec["search_space"]["filter_search"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["current_scoring_allowed"] is False
    assert spec["exposed_stress_replay"]["opening_rule"] == (
        "Open only after the single frozen Campaign048 development trial is "
        "retained and the survivor record is frozen."
    )


def test_campaign048_status_is_terminal_with_closed_stress() -> None:
    result = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.engine_namespace["DEFAULT_CAMPAIGN"]),
            output_root=str(campaign.engine_namespace["DEFAULT_OUTPUT_ROOT"]),
        )
    )
    assert result["campaign_sha256"] == CAMPAIGN_SHA256
    assert result["expected_trial_count"] == 1
    assert result["ledger_entry_count"] == 1
    assert result["selected_survivor_count"] == 0
    assert result["stress_intent_exists"] is False
    assert result["stress_record_exists"] is True
    assert result["stress_status"] == "not_opened_zero_development_survivors"
    assert result["candidate49_historical_return_read"] is False
    assert result["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign048_survivor_reporting_uses_one_feature_complexity(
    monkeypatch,
) -> None:
    monkeypatch.setitem(
        campaign._survivor_decision_with_canonical_complexity.__globals__,
        "_inherited_survivor_decision",
        lambda entry, spec: {
            "development_survivor_gate_passed": False,
            "complexity": 2,
        },
    )
    decision = campaign._survivor_decision_with_canonical_complexity(
        {
            "feature_set": [campaign.ADMITTED_FACTOR],
            "window_transform_threshold_filter_and_weight_configuration": {
                "kind": "single_factor"
            },
        },
        {},
    )
    assert decision["development_survivor_gate_passed"] is False
    assert decision["complexity"] == 1
