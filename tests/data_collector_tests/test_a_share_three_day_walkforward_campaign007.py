from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign007 as campaign007  # noqa: E402


def _campaign(names: list[str]) -> dict:
    canonical = sorted(names)
    expected = len(canonical) + 3 * (
        len(canonical) * (len(canonical) - 1) // 2
    )
    return {
        "factor_library": [{"name": name} for name in names],
        "search_space": {
            "admissible_factor_names_canonical": canonical,
            "pair_weight_grid_for_canonical_factor_order": [
                [0.25, 0.75],
                [0.50, 0.50],
                [0.75, 0.25],
            ],
            "expected_trial_count": expected,
        },
    }


def test_campaign007_catalog_is_exactly_one_frozen_single() -> None:
    trials = campaign007.build_trial_catalog(
        _campaign([campaign007.ADMITTED_FACTOR])
    )
    assert trials == [
        {
            "trial_id": (
                "wf007_single__"
                "intraday_share_volume_transaction_price_coupling_238p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [
                "intraday_share_volume_transaction_price_coupling_238p"
            ],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_candidate49_cannot_enter_campaign007_catalog() -> None:
    with pytest.raises(
        campaign007.Campaign007Error,
        match="admissible factor library",
    ):
        campaign007.build_trial_catalog(
            _campaign(["intraday_cumulative_vwap_crossing_rate_240m"])
        )


def test_campaign007_orchestration_source_is_byte_bound() -> None:
    assert (
        campaign007._sha256(campaign007.CAMPAIGN006_RUNNER)
        == campaign007.CAMPAIGN006_RUNNER_SHA256
    )
    assert (
        campaign007.engine_namespace["CAMPAIGN_ID"]
        == "a_share_three_day_walkforward_campaign_007"
    )


def test_zero_survivor_record_never_opens_stress_or_candidate49() -> None:
    ledger = {"entries": [], "chain_tip_sha256": "0" * 64}
    survivors = {"selected_survivor_count": 0}
    record = campaign007.engine_namespace["_zero_survivor_stress_record"](
        Path("/tmp/campaign007.json"),
        "a" * 64,
        ledger,
        survivors,
    )
    assert record["stress_interval_opened"] is False
    assert record["stress_return_fields_read"] is False
    assert record["candidate49_historical_return_read"] is False
    assert record["current_scoring_selection_sizing_or_orders_allowed"] is False
