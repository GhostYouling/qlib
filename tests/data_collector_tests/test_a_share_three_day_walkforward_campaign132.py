import numpy as np

from scripts import a_share_three_day_walkforward_campaign132 as campaign


def test_build_model_has_exact_frozen_parameters() -> None:
    model = campaign.build_model("pairwise")
    params = model.get_params()
    for name, value in campaign.MODEL_PARAMETERS.items():
        assert params[name] == value
    assert params["interaction_cst"] == "pairwise"
    assert np.array_equal(params["monotonic_cst"], np.ones(140, dtype=np.int8))


def test_training_weights_equalize_session_mass() -> None:
    dates = np.array(["2020-01-02"] * 50 + ["2020-01-03"] * 100, dtype="datetime64[D]")
    target = np.linspace(0.01, 1.0, 150)
    valid, weights, result = campaign.training_weights(
        dates, target, np.ones(150, dtype=bool)
    )
    assert valid.all()
    assert np.isclose(weights[:50].sum(), 0.5)
    assert np.isclose(weights[50:].sum(), 0.5)
    assert result["training_sessions"] == 2


def test_model_scores_neutral_fill_and_support_mask() -> None:
    rng = np.random.default_rng(132)
    matrix = rng.uniform(size=(1_100, 140))
    target = matrix[:, 0]
    model = campaign.build_model("no_interactions")
    model.fit(matrix, target)
    scored = matrix[:3].copy()
    scored[0, 5] = np.nan
    scores = campaign.model_scores(model, scored, np.array([True, False, True]))
    assert np.isfinite(scores[[0, 2]]).all()
    assert np.isnan(scores[1])


def test_uniqueness_audit_rejects_identical_component() -> None:
    sessions = np.repeat(np.arange(20000, 20003), 50)
    keys = sessions * 4_000_000 + np.tile(np.arange(50), 3)
    base = np.tile(np.arange(50, dtype=float), 3)
    matrix = np.column_stack([base, -base])
    result = campaign.uniqueness_audit(
        keys,
        matrix,
        base,
        ["same", "opposite"],
        minimum_names=50,
        minimum_sessions=3,
        strict_maximum_absolute_median=0.8,
    )
    assert result["comparison_count"] == 2
    assert result["all_required_comparisons_passed"] is False
    assert np.isclose(
        result["maximum_observed_absolute_median_daily_rank_correlation"], 1.0
    )


def test_rank_survivors_uses_frozen_configuration_order_as_final_tie_break() -> None:
    records = []
    for trial_id, _ in campaign.TRIALS[:2]:
        records.append(
            {
                "trial_id": trial_id,
                "decision": {
                    "passed": True,
                    "positive_pilot_10bp_return_fold_count": 3,
                    "median_validation_pilot_10bp_return": 0.1,
                    "median_validation_mean_rank_ic": 0.02,
                },
            }
        )
    assert campaign.rank_survivors(records) == [campaign.TRIALS[0][0]]
