import json
from pathlib import Path

import numpy as np
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign031_features as features


REPO_ROOT = Path(__file__).resolve().parents[2]


def _magnitude_path() -> np.ndarray:
    return np.linspace(0.0001, 0.0238, features.RETURN_POSITIONS)


def test_dispersion_decoupling_exact_correlation_endpoints() -> None:
    magnitude = _magnitude_path()
    stock = np.vstack((magnitude, magnitude))
    variances = np.vstack((magnitude**2, magnitude[::-1] ** 2))
    values, eligible, quality = features.compute_factor_values(
        within_half_returns=stock,
        leave_one_out_variances=variances,
        sufficient_peers=np.ones(2, dtype=bool),
    )
    assert eligible[features.FACTOR_NAME].tolist() == [True, True]
    assert values[features.FACTOR_NAME].tolist() == pytest.approx([-1.0, 1.0])
    assert quality[f"{features.FACTOR_NAME}__eligible_rows"] == 2


def test_zero_and_tiny_negative_dispersion_remain_frozen_support() -> None:
    stock = _magnitude_path()
    stock[8:13] = 0.0
    dispersion = _magnitude_path()[::-1]
    variance = dispersion**2
    variance[17] = -0.5 * features.NEGATIVE_VARIANCE_TOLERANCE
    values, eligible, quality = features.compute_factor_values(
        within_half_returns=stock[None, :],
        leave_one_out_variances=variance[None, :],
        sufficient_peers=np.array([True]),
    )
    assert eligible[features.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[features.FACTOR_NAME]).all()
    assert (
        quality[f"{features.FACTOR_NAME}__exact_zero_stock_return_positions"]
        == 5
    )
    assert (
        quality[
            f"{features.FACTOR_NAME}__tiny_negative_variance_positions_canonicalized"
        ]
        == 1
    )
    assert (
        quality[f"{features.FACTOR_NAME}__exact_zero_dispersion_positions"]
        == 1
    )


def test_peer_material_negative_and_vector_variance_gates_fail_closed() -> None:
    magnitude = _magnitude_path()
    constant = np.ones(features.RETURN_POSITIONS)
    material_negative = magnitude**2
    material_negative[5] = -2 * features.NEGATIVE_VARIANCE_TOLERANCE
    stock = np.vstack((magnitude, magnitude, constant, magnitude))
    variances = np.vstack(
        (magnitude**2, material_negative, magnitude**2, constant)
    )
    values, eligible, quality = features.compute_factor_values(
        within_half_returns=stock,
        leave_one_out_variances=variances,
        sufficient_peers=np.array([False, True, True, True]),
    )
    assert eligible[features.FACTOR_NAME].tolist() == [False] * 4
    assert np.isnan(values[features.FACTOR_NAME]).all()
    assert quality[f"{features.FACTOR_NAME}__insufficient_peer_rows"] == 1
    assert (
        quality[f"{features.FACTOR_NAME}__material_negative_variance_rows"]
        == 1
    )
    assert (
        quality[
            f"{features.FACTOR_NAME}__degenerate_stock_magnitude_variance_rows"
        ]
        == 1
    )
    assert (
        quality[
            f"{features.FACTOR_NAME}__degenerate_dispersion_variance_rows"
        ]
        == 1
    )


def test_invalid_array_shape_is_rejected() -> None:
    with pytest.raises(features.Campaign031FeatureError):
        features.compute_factor_values(
            within_half_returns=np.ones((1, 237)),
            leave_one_out_variances=np.ones((1, 237)),
            sufficient_peers=np.array([True]),
        )


def test_all_campaign031_freeze_bindings_pass_before_candidate_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_031_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_031_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_031_no_return_preregistration.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_031_dispersion_benchmark_freeze_20260730.json",
    ]
    for record in records:
        result = bindings.validate_record(
            record, data_root=features.DEFAULT_DATA_ROOT
        )
        assert result["all_bindings_passed"] is True
    protocol = features.load_protocol()
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 52
    assert comparisons[-1]["name"] == features.C30_FACTOR_NAMES[0]


def test_frozen_dispersion_benchmark_replays_without_outcomes() -> None:
    benchmark = features._load_dispersion_benchmark(
        features.DEFAULT_DATA_ROOT
    )
    assert len(benchmark.dates) == 1699
    assert benchmark.return_sums.shape == (1699, features.RETURN_POSITIONS)
    assert benchmark.return_sum_squares.shape == (
        1699,
        features.RETURN_POSITIONS,
    )
    assert int(benchmark.valid_stock_counts.min()) == 3549
    freeze = json.loads(features.BENCHMARK_FREEZE_PATH.read_text())
    assert freeze["research_boundary"]["candidate_values_computed"] is False
    assert freeze["research_boundary"]["forward_returns_read"] is False
    assert freeze["research_boundary"]["provider_request_issued"] is False


def test_campaign031_status_reports_squared_sum_schema() -> None:
    result = features.status(
        features.DEFAULT_DATA_ROOT,
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/"
        "campaign_031/no_return",
    )
    assert result["snapshot_exists"] is True
    assert result["snapshot_sha256_bound"] is True
    assert result["market_benchmark_fields_read_by_status"] == [
        "trade_date",
        "return_position",
        "return_sum",
        "return_sum_squares",
        "valid_stock_count",
    ]
    assert result["forward_return_fields_read_by_status"] is False
