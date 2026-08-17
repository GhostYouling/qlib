from pathlib import Path

import numpy as np

from scripts import a_share_three_day_walkforward_campaign133 as campaign


def test_protocol_binding_and_single_configuration_are_exact() -> None:
    assert campaign.base.file_sha256(campaign.PROTOCOL_PATH) == campaign.PROTOCOL_SHA256
    protocol = campaign.base.load_json(campaign.PROTOCOL_PATH)
    assert [item["trial_id"] for item in protocol["trial_catalog"]] == [
        campaign.TRIAL_ID
    ]
    assert protocol["search_multiplicity"] == {
        "trial_count": 1,
        "bin_count": 10,
        "anchor_weight_on_fitted_pava_level": 0.5,
        "anchor_weight_on_original_favorable_percentile": 0.5,
        "alternative_bin_counts_or_anchor_weights_allowed": False,
        "component_subset_or_weight_search_allowed": False,
        "validation_driven_refit_or_rescue_allowed": False,
    }


def test_weighted_pava_merges_adjacent_violations_with_weights() -> None:
    fitted = campaign.weighted_pava(
        np.array([0.8, 0.2, 0.9]), np.array([1.0, 3.0, 1.0])
    )
    np.testing.assert_allclose(fitted, np.array([0.35, 0.35, 0.9]))


def test_fit_calibration_interpolates_empty_bins_and_preserves_monotonicity() -> None:
    row_values = np.array([0.0, 0.2, 0.8, 1.0])
    matrix = np.repeat(row_values[:, None], campaign.design.FEATURE_COUNT, axis=1)
    levels, statistics = campaign.fit_calibration(
        matrix,
        np.array([0.1, 0.4, 0.6, 0.9]),
        np.full(4, 0.25),
        np.ones(4, dtype=bool),
    )
    assert levels.shape == (campaign.design.FEATURE_COUNT, campaign.BIN_COUNT)
    assert statistics["minimum_observed_bins_per_feature"] == 4
    np.testing.assert_allclose(levels[:, 0], 0.1)
    np.testing.assert_allclose(levels[:, 1], 0.25)
    np.testing.assert_allclose(levels[:, 9], 0.9)
    assert np.all(levels[:, 1:] >= levels[:, :-1])


def test_anchor_makes_each_favorable_component_strictly_contribute() -> None:
    levels = np.repeat(
        np.linspace(0.1, 0.9, campaign.BIN_COUNT)[None, :],
        campaign.design.FEATURE_COUNT,
        axis=0,
    )
    matrix = np.full((2, campaign.design.FEATURE_COUNT), 0.1)
    matrix[1, 0] = 0.2
    scores = campaign.calibration_scores(levels, matrix, np.ones(2, dtype=bool))
    assert scores[1] > scores[0]
    assert scores[1] - scores[0] >= 0.5 * 0.1 / campaign.design.FEATURE_COUNT


def test_neutral_fill_and_ineligible_row_semantics() -> None:
    levels = np.full((campaign.design.FEATURE_COUNT, campaign.BIN_COUNT), 0.5)
    matrix = np.full((2, campaign.design.FEATURE_COUNT), np.nan)
    scores = campaign.calibration_scores(
        levels, matrix, np.array([True, False], dtype=bool)
    )
    assert scores[0] == 0.5
    assert np.isnan(scores[1])


def test_campaign133_runner_has_no_lockbox_command() -> None:
    parser = campaign.parser()
    actions = next(
        action for action in parser._actions if getattr(action, "choices", None)
    )
    assert set(actions.choices) == {"status", "plan", "run-development"}
    assert not Path(campaign.DEFAULT_OUTPUT_ROOT / "lockbox_report.json").exists()
