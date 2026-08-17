"""Synthetic and boundary tests for Campaign033 spectral entropy."""

from __future__ import annotations

import importlib

import numpy as np
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign033_features"
)


def _closes_from_returns(returns: np.ndarray) -> np.ndarray:
    log_closes = np.concatenate(([0.0], np.cumsum(returns)))
    return np.exp(log_closes)


def _two_half_closes(returns: np.ndarray) -> np.ndarray:
    half = _closes_from_returns(returns)
    return np.concatenate((half, half))[None, :]


def test_single_impulse_has_flat_positive_frequency_power_and_unit_entropy():
    returns = np.zeros(119, dtype=float)
    returns[0] = 0.01

    values, eligible, quality = MODULE.compute_factor_values(
        closes=_two_half_closes(returns)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1


def test_one_exact_frequency_has_zero_entropy():
    positions = np.arange(119, dtype=float)
    returns = 0.001 * np.sin(2.0 * np.pi * 7.0 * positions / 119.0)

    values, eligible, _ = MODULE.compute_factor_values(
        closes=_two_half_closes(returns)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-12)


def test_constant_close_halves_have_no_positive_frequency_power():
    values, eligible, quality = MODULE.compute_factor_values(
        closes=np.ones((1, 240), dtype=float)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_total_power_rows"] == 1


def test_invalid_shape_nonpositive_or_nonfinite_close_fails_closed():
    with pytest.raises(MODULE.Campaign033FeatureError):
        MODULE.compute_factor_values(closes=np.ones((1, 239)))

    rows = np.ones((2, 240), dtype=float)
    rows[0, 10] = 0.0
    rows[1, 10] = np.nan
    values, eligible, _ = MODULE.compute_factor_values(closes=rows)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()


def test_protocol_freezes_one_candidate_and_54_unique_comparisons():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 54
    assert len({item["name"] for item in comparisons}) == 54
    assert comparisons[-1]["name"] == "quarterly_announcement_timeliness_days"
    assert spec["candidates"][0]["name"] == MODULE.FACTOR_NAME
    assert (
        spec["finite_post_admissibility_search"]["trial"]["factor"]
        == MODULE.FACTOR_NAME
    )


def test_post_audit_status_binds_the_single_result_without_return_reads():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_exists"] is True
    assert result["snapshot_sha256_bound"] is True
    assert result["audit_count"] == 1
    assert result["no_return_audit_sha256_bound"] is True
    assert result["latest_audit_observed_sha256"] == MODULE.NO_RETURN_AUDIT_SHA256
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
