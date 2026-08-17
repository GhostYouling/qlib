from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign004 as campaign004  # noqa: E402


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


def test_three_factor_catalog_is_exactly_twelve_trials() -> None:
    trials = campaign004.build_trial_catalog(
        _campaign(["factor_c", "factor_a", "factor_b"])
    )

    assert len(trials) == 12
    assert len({trial["trial_id"] for trial in trials}) == 12
    assert [trial["feature_set"] for trial in trials[:3]] == [
        ["factor_a"],
        ["factor_b"],
        ["factor_c"],
    ]
    assert sum(trial["kind"] == "single_factor" for trial in trials) == 3
    assert sum(trial["kind"] == "pair_rank_blend" for trial in trials) == 9


def test_one_factor_catalog_has_only_the_frozen_single() -> None:
    trials = campaign004.build_trial_catalog(_campaign(["only_factor"]))
    assert trials == [
        {
            "trial_id": "wf004_single__only_factor",
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": ["only_factor"],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_candidate49_is_forbidden_from_historical_catalog() -> None:
    with pytest.raises(
        campaign004.Campaign004Error,
        match="admissible factor library",
    ):
        campaign004.build_trial_catalog(
            _campaign(["intraday_cumulative_vwap_crossing_rate_240m"])
        )


def _stress_period() -> dict:
    return {
        "association": {
            "mean_rank_ic": 0.01,
            "positive_rank_ic_rate": 0.6,
            "mean_top3_minus_bottom3_gross_return": 0.01,
        },
        "normalized_execution": {
            "net_cumulative_return": 0.10,
            "maximum_drawdown": -0.10,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_execution_primary_10bp": {
            "net_cumulative_return": 0.05,
            "board_lot_affordability_rate": 0.95,
            "maximum_filled_trade_daily_amount_participation": 0.005,
            "filled_trade_amount_missing_count": 0,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_slippage_sensitivity": {
            "0.0020": {"net_cumulative_return": 0.01}
        },
    }


def _stress_gate() -> dict:
    return {
        "mean_rank_ic_gt": 0,
        "positive_rank_ic_rate_gt": 0.5,
        "mean_top3_minus_bottom3_spread_gt": 0,
        "each_year_mean_rank_ic_gt": 0,
        "normalized_return_gt": 0,
        "normalized_drawdown_gte": -0.2,
        "each_year_normalized_return_gt": 0,
        "normalized_terminal_unresolved_positions": 0,
        "pilot_10bp_return_gt": 0,
        "pilot_20bp_return_gt": 0,
        "each_year_pilot_10bp_return_gt": 0,
        "board_lot_affordability_gte": 0.9,
        "maximum_daily_amount_participation_lte": 0.01,
        "pilot_terminal_unresolved_positions": 0,
    }


def test_exposed_stress_gate_requires_every_frozen_condition() -> None:
    combined = _stress_period()
    yearly = {"2024": _stress_period(), "2025": _stress_period()}
    assert campaign004._apply_stress_gate(combined, yearly, _stress_gate()) == []

    combined["pilot_slippage_sensitivity"]["0.0020"][
        "net_cumulative_return"
    ] = -0.01
    assert "nonpositive_stress_pilot_20bp_return" in campaign004._apply_stress_gate(
        combined,
        yearly,
        _stress_gate(),
    )


def test_development_prefix_stays_stable_after_stress_append() -> None:
    development = {
        "phase": campaign004.DEVELOPMENT_PHASE,
        "entry_sha256": "a" * 64,
    }
    stress = {
        "phase": campaign004.STRESS_PHASE,
        "entry_sha256": "b" * 64,
    }
    prefix = campaign004._development_ledger_prefix(
        {"entries": [development, stress]}
    )
    assert prefix["entry_count"] == 1
    assert prefix["chain_tip_sha256"] == "a" * 64
