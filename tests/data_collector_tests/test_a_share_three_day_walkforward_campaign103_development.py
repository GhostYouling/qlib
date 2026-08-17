from __future__ import annotations

import argparse
import json

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign103 as campaign


def test_trial_catalog_contains_exactly_one_higher_factor() -> None:
    spec, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    trials = campaign.build_trial_catalog(spec)
    assert trials == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.ADMITTED_FACTOR],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_candidate_manifest_binding_and_eligible_count() -> None:
    manifest = json.loads(campaign.CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    assert campaign._sha256(campaign.CANDIDATE_MANIFEST) == campaign.CANDIDATE_MANIFEST_SHA256
    assert manifest["dataset_sha256"] == campaign.CANDIDATE_DATASET_SHA256
    assert manifest["eligible_rows"] == campaign.EXPECTED_ELIGIBLE_ROWS == 1_315_573
    assert manifest["factor"] == campaign.ADMITTED_FACTOR


def test_compact_loader_reads_only_bound_factor_and_requested_dates() -> None:
    spec, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    dates = pd.DatetimeIndex(["2019-01-03", "2019-01-04"])
    panel = campaign._load_compact_factor_panel(spec, [2019], dates)
    assert set(panel.columns) == {
        "trade_date",
        "instrument",
        campaign.ADMITTED_FACTOR,
    }
    assert set(panel["trade_date"].unique()).issubset(set(dates))


def test_inherited_loader_context_uses_campaign103_loader() -> None:
    assert (
        campaign._temporary_compact_factor_loader.__wrapped__.__globals__[
            "_load_compact_factor_panel"
        ]
        is campaign._load_compact_factor_panel
    )


def test_inherited_loader_context_patches_and_restores_shared_base() -> None:
    original = campaign.base.load_factor_panel
    with campaign._temporary_compact_factor_loader():
        assert campaign.base.load_factor_panel is campaign._load_compact_factor_panel
    assert campaign.base.load_factor_panel is original


def test_existing_v8_ledger_header_is_validated_without_rewrite() -> None:
    ledger_path = (
        campaign.REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_103/"
        "walkforward/trial_ledger.json"
    )
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    validated = campaign._validate_campaign103_ledger(
        ledger,
        campaign.DEFAULT_PREREGISTRATION,
        campaign._sha256(campaign.DEFAULT_PREREGISTRATION),
    )
    assert validated == ledger
    assert ledger_path.read_bytes() == before


def test_v8_ledger_continuity_rejects_nonactive_campaign_hash() -> None:
    ledger_path = (
        campaign.REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_103/"
        "walkforward/trial_ledger.json"
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    with pytest.raises(campaign.Campaign103Error):
        campaign._validate_campaign103_ledger(
            ledger,
            campaign.DEFAULT_PREREGISTRATION,
            "0" * 64,
        )


def test_development_activation_fails_closed_before_binding_exists() -> None:
    if campaign.DEVELOPMENT_ACTIVATION_BINDING.exists():
        pytest.skip("activation binding has been frozen")
    with pytest.raises(campaign.Campaign103Error):
        campaign._load_development_activation()


def test_status_is_read_only_before_development(tmp_path) -> None:
    args = argparse.Namespace(
        campaign=str(campaign.DEFAULT_PREREGISTRATION),
        output_root=str(tmp_path),
    )
    payload = campaign.status(args)
    assert payload["expected_trial_count"] == 1
    assert payload["ledger_entry_count"] == 0
    assert payload["candidate49_historical_return_read"] is False
    assert payload["current_scoring_selection_sizing_or_orders_allowed"] is False
