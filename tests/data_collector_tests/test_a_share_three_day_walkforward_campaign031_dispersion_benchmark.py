from pathlib import Path

import numpy as np

import scripts.a_share_three_day_walkforward_campaign031_dispersion_benchmark as benchmark


def test_protocol_is_bound_before_benchmark_values() -> None:
    spec = benchmark.load_protocol()
    assert (
        spec["research_boundary"][
            "binding_validation_required_before_dispersion_benchmark_or_candidate_values"
        ]
        is True
    )
    assert spec["research_boundary"]["forward_return_fields_read_before_admissibility"] is False
    assert spec["research_boundary"]["provider_request_allowed"] is False


def test_accumulate_returns_requires_complete_vectors() -> None:
    sums = np.zeros((2, benchmark.RETURN_POSITIONS), dtype=float)
    sum_squares = np.zeros_like(sums)
    counts = np.zeros_like(sums, dtype=np.int32)
    first = np.linspace(-0.02, 0.03, benchmark.RETURN_POSITIONS)
    incomplete = first.copy()
    incomplete[19] = np.nan
    invalid = benchmark.accumulate_returns(
        indices=np.array([0, 1]),
        returns=np.vstack([first, incomplete]),
        return_sums=sums,
        return_sum_squares=sum_squares,
        valid_counts=counts,
    )
    assert invalid == 1
    np.testing.assert_allclose(sums[0], first)
    np.testing.assert_allclose(sum_squares[0], first * first)
    assert np.array_equal(counts[0], np.ones(benchmark.RETURN_POSITIONS))
    assert np.array_equal(sums[1], np.zeros(benchmark.RETURN_POSITIONS))
    assert np.array_equal(sum_squares[1], np.zeros(benchmark.RETURN_POSITIONS))
    assert np.array_equal(counts[1], np.zeros(benchmark.RETURN_POSITIONS))


def test_status_never_claims_candidate_or_return_values(tmp_path: Path) -> None:
    result = benchmark.status(tmp_path)
    assert result["benchmark_exists"] is False
    assert result["candidate_values_computed"] is False
    assert result["forward_return_fields_read"] is False
    assert result["provider_request_issued"] is False
