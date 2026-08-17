from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign102_design as design


def test_complete_numeric_source_order_is_exact_v58_order() -> None:
    sources = design.reconstruct_numeric_sources()
    assert len(sources) == 130
    assert design.c101._order_digest(sources) == design.NUMERIC_ORDER_SHA256
    assert sources[-1] == {
        "name": "full_numeric_library_directional_lower_quartile_consensus_129f",
        "score_direction": "higher",
    }
    assert len({item["name"] for item in sources}) == 130


def test_support_threshold_preserves_missingness_and_exact_boundary() -> None:
    matrix = np.full((4, 130), 0.5, dtype=np.float32)
    matrix[1, :32] = np.nan  # 98 finite: eligible
    matrix[2, :33] = np.nan  # 97 finite: ineligible
    matrix[3, :129] = np.nan
    finite_count, eligible = design.support_state(matrix)
    assert finite_count.tolist() == [130, 98, 97, 1]
    assert eligible.tolist() == [True, True, False, False]
    assert np.isnan(matrix[1, 0])


def test_model_matrix_maps_missing_to_zero_only_for_supported_rows() -> None:
    matrix = np.full((2, 130), 0.75, dtype=np.float64)
    matrix[0, 0] = np.nan
    matrix[1, :40] = np.nan
    finite_count, eligible = design.support_state(matrix)
    assert finite_count.tolist() == [129, 90]
    result = design.model_matrix(matrix, eligible)
    assert result[0, 0] == 0.0
    assert np.isfinite(result[0]).all()
    assert np.isnan(result[1]).all()


def test_support_state_rejects_invalid_component_range() -> None:
    matrix = np.full((1, 130), 0.5, dtype=np.float64)
    matrix[0, 9] = 0.0
    with pytest.raises(design.Campaign102DesignError, match="escaped"):
        design.support_state(matrix)
    matrix[0, 9] = 1.01
    with pytest.raises(design.Campaign102DesignError, match="escaped"):
        design.support_state(matrix)


def test_canonical_matrix_hash_is_stable_across_nan_payloads() -> None:
    keys = np.array([1, 2], dtype=np.int64)
    left = np.full((2, 130), 0.5, dtype=np.float32)
    right = left.copy()
    left[0, 0] = np.nan
    right.view(np.uint32)[0, 0] = np.uint32(0x7FC01234)
    finite_count, eligible = design.support_state(left)
    assert design._canonical_matrix_sha256(
        keys, left, finite_count, eligible
    ) == design._canonical_matrix_sha256(keys, right, finite_count, eligible)


def test_protocol_freezes_return_blind_design_and_finite_model_catalog() -> None:
    protocol = json.loads(design.DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    matrix = protocol["design_matrix"]
    assert matrix["source_factor_count"] == 130
    assert matrix["minimum_originally_finite_components"] == 98
    assert matrix["historical_daily_price_or_return_fields_permitted_during_build"] == []
    assert protocol["model_family"]["regularization_grid"] == [0.0, 0.1, 1.0]
    assert len(protocol["finite_development_catalog"]) == 3
    assert protocol["research_boundary"]["candidate49_ledgers_may_change"] is False


def test_status_is_read_only_even_before_snapshot_exists(tmp_path) -> None:
    payload = design.status(data_root=tmp_path)
    assert payload["campaign102_design_matrix_values_read_by_status"] is False
    assert payload["model_fitting_performed_by_status"] is False
    assert payload["historical_daily_price_or_return_values_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
