"""Pre-return boundary tests for Campaign038 development."""

from __future__ import annotations

import argparse

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign038 as campaign
import scripts.a_share_three_day_walkforward_campaign038_features as features


CAMPAIGN_SHA256 = (
    "09324d96780d48be9550a22aa13501fece00070571d0c5503e4c437525dfc312"
)


def test_campaign038_preregistration_and_single_trial_are_frozen() -> None:
    path = campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    result = bindings.validate_record(
        path, data_root=features.DEFAULT_DATA_ROOT
    )
    assert result["all_bindings_passed"] is True
    spec, observed_sha256 = campaign.load_campaign(path)
    assert observed_sha256 == CAMPAIGN_SHA256
    assert campaign.build_trial_catalog(spec) == [
        {
            "trial_id": (
                "wf038_single__"
                "intraday_half_session_chord_adherence_240m"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [features.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_campaign038_folds_search_and_stress_boundary_are_closed() -> None:
    spec, _ = campaign.load_campaign(
        campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert len(spec["walkforward_folds"]) == 3
    assert (
        spec["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    )
    assert spec["search_space"]["expected_trial_count"] == 1
    assert spec["search_space"]["weight_fitting"] is False
    assert spec["search_space"]["threshold_search"] is False
    assert spec["search_space"]["year_subset_search"] is False
    assert spec["search_space"]["filter_search"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["current_scoring_allowed"] is False
    assert (
        spec["research_output_boundary"][
            "campaign037_rescue_or_reweight_allowed"
        ]
        is False
    )
    assert spec["exposed_stress_replay"]["opening_rule"] == (
        "Open only after the single frozen Campaign038 development trial is "
        "retained and the survivor record is frozen."
    )


def test_campaign038_status_is_terminal_with_closed_stress() -> None:
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


def test_campaign038_survivor_reporting_uses_one_feature_complexity(
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
            "feature_set": [features.FACTOR_NAME],
            "window_transform_threshold_filter_and_weight_configuration": {
                "kind": "single_factor"
            },
        },
        {},
    )
    assert decision["development_survivor_gate_passed"] is False
    assert decision["complexity"] == 1
