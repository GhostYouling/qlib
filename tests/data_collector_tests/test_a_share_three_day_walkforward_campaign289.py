from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign289 as campaign289


ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign289_preregistration_binds_finite_single_trial() -> None:
    protocol = json.loads(campaign289.PROTOCOL_PATH.read_text())
    concept = json.loads(campaign289.CONCEPT_PATH.read_text())
    overlap = json.loads(campaign289.OVERLAP_PATH.read_text())

    assert _sha(campaign289.PROTOCOL_PATH) == campaign289.PROTOCOL_SHA256
    assert _sha(campaign289.CONCEPT_PATH) == campaign289.CONCEPT_SHA256
    assert _sha(campaign289.OVERLAP_PATH) == campaign289.OVERLAP_SHA256
    assert len(concept["finite_prevalue_concept_catalog"]) == 7
    assert (
        sum(
            item["decision"].startswith("selected")
            for item in concept["finite_prevalue_concept_catalog"]
        )
        == 1
    )
    assert overlap["fixed_mechanism_identity"]["hash_bits"] == 8
    assert protocol["model_trial"]["parameters"] == campaign289.MODEL_PARAMETERS
    assert protocol["model_trial"]["configuration_count"] == 1
    assert (
        protocol["complete_feature_library"]["feature_subset_search_allowed"] is False
    )
    assert protocol["locked_2024_2025_campaign_backtest"]["initially_closed"] is True


def test_session_binary_transform_uses_strict_session_median_states() -> None:
    rows = 600
    base = np.arange(rows, dtype=np.float32)
    matrix = np.column_stack(
        [base + column / 1000 for column in range(campaign289.FEATURE_COUNT)]
    ).astype(np.float32)
    dates = pd.DatetimeIndex(["2020-01-02"] * 300 + ["2020-01-03"] * 300)
    eligible = np.ones(rows, dtype=bool)

    stats = campaign289.session_binary_transform_inplace(matrix, dates, eligible)

    assert stats["session_count"] == 2
    assert stats["minimum_total_finite_observations_per_feature"] == rows
    assert set(np.unique(matrix)) == {-1.0, 1.0}
    assert np.all(matrix[:150] == -1.0)
    assert np.all(matrix[150:300] == 1.0)
    assert np.all(matrix[300:450] == -1.0)
    assert np.all(matrix[450:] == 1.0)


def test_random_hyperplane_hash_is_deterministic_and_bounded() -> None:
    weights_a, stats_a = campaign289.random_hyperplanes()
    weights_b, stats_b = campaign289.random_hyperplanes()
    states = np.resize(
        np.asarray([-1, 0, 1], dtype=np.float32), (257, campaign289.FEATURE_COUNT)
    )
    cells_a = campaign289.hash_cells(states, weights_a)
    cells_b = campaign289.hash_cells(states, weights_b)

    assert np.array_equal(weights_a, weights_b)
    assert stats_a == stats_b
    assert weights_a.shape == (campaign289.FEATURE_COUNT, campaign289.HASH_BITS)
    assert set(np.unique(weights_a)) == {-1, 1}
    assert np.array_equal(cells_a, cells_b)
    assert cells_a.dtype == np.uint16
    assert int(cells_a.min()) >= 0
    assert int(cells_a.max()) < campaign289.CELL_COUNT


def test_cell_mean_regressor_fits_continuous_weighted_means_and_global_fallback() -> (
    None
):
    cells = np.repeat(np.arange(64, dtype=np.uint16), 2)
    target = np.tile(np.asarray([0.2, 0.8], dtype=np.float64), 64)
    weight = np.ones(len(target), dtype=np.float64)
    model = campaign289.RandomHyperplaneCellMeanRegressor(
        dict(campaign289.MODEL_PARAMETERS)
    ).fit(cells, target, weight)

    observed = model.predict(np.asarray([0, 1, 63], dtype=np.uint16))
    unseen = model.predict(np.asarray([64, 255], dtype=np.uint16))
    assert np.allclose(observed, 0.5)
    assert np.allclose(unseen, 0.5)
    assert model.fit_statistics_["occupied_cell_count"] == 64
    assert model.fit_statistics_["unoccupied_cell_count"] == 192
    assert model.fit_statistics_["minimum_occupied_raw_count"] == 2


def test_campaign289_keeps_candidate49_and_current_use_out_of_scope() -> None:
    protocol = json.loads(campaign289.PROTOCOL_PATH.read_text())
    boundary = protocol["research_boundary"]
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["candidate49_ledgers_changed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )
    assert boundary["investment_advice"] is False
