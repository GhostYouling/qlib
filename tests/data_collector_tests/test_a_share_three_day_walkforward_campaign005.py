from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign005 as campaign005  # noqa: E402


def _campaign(names: list[str]) -> dict:
    canonical = sorted(names)
    expected = len(canonical) + 3 * (len(canonical) * (len(canonical) - 1) // 2)
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


def test_campaign005_catalog_is_exactly_one_frozen_single() -> None:
    trials = campaign005.build_trial_catalog(
        _campaign([campaign005.ADMITTED_FACTOR])
    )

    assert trials == [
        {
            "trial_id": (
                "wf005_single__intraday_zero_return_amount_intensity_238m"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [
                "intraday_zero_return_amount_intensity_238m"
            ],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_candidate49_cannot_enter_campaign005_catalog() -> None:
    with pytest.raises(
        campaign005.Campaign005Error,
        match="admissible factor library",
    ):
        campaign005.build_trial_catalog(
            _campaign(["intraday_cumulative_vwap_crossing_rate_240m"])
        )


def test_campaign005_engine_source_is_byte_bound_and_campaign004_unchanged() -> None:
    assert (
        campaign005._sha256(campaign005.CAMPAIGN004_RUNNER)
        == campaign005.CAMPAIGN004_RUNNER_SHA256
    )
    assert campaign005.CAMPAIGN_ID == "a_share_three_day_walkforward_campaign_005"


def test_zero_survivor_record_never_opens_stress_or_candidate49() -> None:
    ledger = {"entries": [], "chain_tip_sha256": "0" * 64}
    survivors = {"selected_survivor_count": 0}
    record = campaign005._generated["_zero_survivor_stress_record"](
        Path("/tmp/campaign005.json"),
        "a" * 64,
        ledger,
        survivors,
    )

    assert record["stress_interval_opened"] is False
    assert record["stress_return_fields_read"] is False
    assert record["candidate49_historical_return_read"] is False
    assert record["current_scoring_selection_sizing_or_orders_allowed"] is False
