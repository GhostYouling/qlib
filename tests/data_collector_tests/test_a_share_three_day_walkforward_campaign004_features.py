from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign004_features as campaign004  # noqa: E402


def _base_arrays(rows: int = 1) -> tuple[np.ndarray, ...]:
    closes = np.exp(
        np.tile(np.linspace(0.0, 0.12, 240, dtype=float), (rows, 1))
    )
    amounts = np.ones((rows, 240), dtype=float)
    within_half = np.ones((rows, 238), dtype=float)
    market = np.ones((rows, 238), dtype=float)
    sufficient = np.ones(rows, dtype=bool)
    return closes, amounts, within_half, market, sufficient


def test_market_neutral_late_residual_drift_uses_final_sixty_returns() -> None:
    closes, amounts, within_half, market, sufficient = _base_arrays()
    within_half[:, :178] = 2.0
    within_half[:, 178:] = 3.0

    values, eligible, quality = campaign004.compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half,
        leave_one_out_market_returns=market,
        sufficient_peers=sufficient,
    )

    factor = campaign004.MARKET_NEUTRAL_FACTOR
    assert eligible[factor].tolist() == [True]
    assert values[factor][0] == pytest.approx(0.5)
    assert quality[f"{factor}__eligible_rows"] == 1


def test_negative_return_absorption_is_destination_amount_weighted() -> None:
    closes, amounts, within_half, market, sufficient = _base_arrays()
    within_half[:] = 1.0
    within_half[:, 0] = -1.0
    within_half[:, 1] = 1.0
    within_half[:, 119] = -1.0
    within_half[:, 120] = 1.0
    amounts[:, 1] = 2.0
    amounts[:, 121] = 3.0

    values, eligible, _quality = campaign004.compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half,
        leave_one_out_market_returns=market,
        sufficient_peers=sufficient,
    )

    factor = campaign004.ABSORPTION_FACTOR
    assert eligible[factor].tolist() == [True]
    assert values[factor][0] == pytest.approx(1.0)


def test_absorption_zero_denominator_stays_missing() -> None:
    closes, amounts, within_half, market, sufficient = _base_arrays()

    values, eligible, quality = campaign004.compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half,
        leave_one_out_market_returns=market,
        sufficient_peers=sufficient,
    )

    factor = campaign004.ABSORPTION_FACTOR
    assert eligible[factor].tolist() == [False]
    assert np.isnan(values[factor][0])
    assert quality[f"{factor}__zero_negative_amount_denominator_rows"] == 1


def test_signed_path_efficiency_includes_collapsed_lunch_pair() -> None:
    closes, amounts, within_half, market, sufficient = _base_arrays()
    closes[:, 120:] *= np.exp(0.25)

    values, eligible, _quality = campaign004.compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half,
        leave_one_out_market_returns=market,
        sufficient_peers=sufficient,
    )

    factor = campaign004.PATH_EFFICIENCY_FACTOR
    assert eligible[factor].tolist() == [True]
    assert values[factor][0] == pytest.approx(1.0)


def test_market_neutral_zero_residual_path_stays_missing() -> None:
    closes, amounts, within_half, market, sufficient = _base_arrays()
    within_half[:] = 2.0

    values, eligible, quality = campaign004.compute_factor_values(
        closes=closes,
        amounts=amounts,
        within_half_returns=within_half,
        leave_one_out_market_returns=market,
        sufficient_peers=sufficient,
    )

    factor = campaign004.MARKET_NEUTRAL_FACTOR
    assert eligible[factor].tolist() == [False]
    assert np.isnan(values[factor][0])
    assert quality[f"{factor}__zero_residual_path_rows"] == 1


def test_protocol_is_fingerprint_bound_before_values() -> None:
    protocol = campaign004.load_protocol()
    assert protocol["status"] == (
        "frozen_before_campaign004_candidate_or_comparison_values_or_returns"
    )
    assert [item["name"] for item in protocol["candidates"]] == list(
        campaign004.FACTOR_NAMES
    )
