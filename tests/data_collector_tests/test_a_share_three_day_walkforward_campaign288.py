from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign288 as campaign


def test_deterministic_sampler_selects_exactly_96_per_retained_session() -> None:
    dates = pd.date_range("2020-01-01", periods=61, freq="D")
    rows = []
    for date_position, date in enumerate(dates):
        for security in range(100):
            rows.append(
                {
                    "trade_date": date,
                    "instrument": f"SZ{security:06d}",
                    "stock_day_key": date_position * 4_000_000 + 2_000_000 + security,
                }
            )
    identities = pd.DataFrame(rows)
    eligible = np.ones(len(identities), dtype=bool)

    first, stats = campaign.deterministic_sample_positions(identities, eligible)
    second, _ = campaign.deterministic_sample_positions(identities, eligible)

    assert np.array_equal(first, second)
    assert stats["retained_training_sessions"] == 61
    assert stats["sampled_rows"] == 61 * 96
    assert identities.iloc[first].groupby("trade_date").size().eq(96).all()


def test_session_ordinal_transform_handles_ties_missing_and_ineligible() -> None:
    raw = np.asarray([1.0, 2.0, 2.0, np.nan, *range(3, 599), 9.0])
    matrix = np.tile(raw[:, None], (1, 158))
    matrix = matrix.astype(np.float32)
    dates = pd.to_datetime(["2020-01-01"] * len(matrix))
    eligible = np.ones(len(matrix), dtype=bool)
    eligible[-1] = False

    stats = campaign.session_ordinal_transform_inplace(matrix, dates, eligible)

    expected = np.asarray(
        [1 / 599 - 0.5, 2.5 / 599 - 0.5, 2.5 / 599 - 0.5, 0.0],
        dtype=np.float32,
    )
    assert np.allclose(matrix[:4, 0], expected)
    assert matrix[-1, 0] == 0.0
    assert np.isfinite(matrix).all()
    assert stats["minimum_total_finite_observations_per_feature"] == 599


def test_random_fourier_basis_and_projection_are_deterministic() -> None:
    first_weights, first_phases, first_stats = campaign.random_fourier_basis()
    second_weights, second_phases, second_stats = campaign.random_fourier_basis()
    matrix = np.zeros((5, campaign.FEATURE_COUNT), dtype=np.float64)

    assert np.array_equal(first_weights, second_weights)
    assert np.array_equal(first_phases, second_phases)
    assert first_stats == second_stats
    assert np.array_equal(
        campaign.random_fourier_features(matrix, first_weights, first_phases),
        campaign.random_fourier_features(matrix, second_weights, second_phases),
    )


def test_random_fourier_ridge_recovers_fixed_basis_signal() -> None:
    rng = np.random.default_rng(11)
    matrix = rng.uniform(-0.5, 0.5, size=(512, campaign.FEATURE_COUNT))
    weights, phases, _ = campaign.random_fourier_basis()
    projection = campaign.random_fourier_features(matrix, weights, phases)
    center = projection.mean(axis=0)
    truth = np.zeros(campaign.RFF_DIMENSION)
    truth[:3] = [0.8, -0.5, 0.3]
    target = (projection - center) @ truth + 0.2
    sample_weight = np.full(len(matrix), 1.0 / len(matrix))

    model = campaign.RandomFourierRidgeRegressor(
        dict(campaign.MODEL_PARAMETERS), center
    ).fit(matrix, target, sample_weight)
    prediction = model.predict(matrix)

    assert model.fit_statistics_ is not None
    assert np.mean(np.square(prediction - target)) < np.var(target)
    assert np.isfinite(prediction).all()


def test_session_equal_target_weights_preserve_equal_daily_mass() -> None:
    dates = np.repeat(pd.date_range("2020-01-01", periods=60, freq="D"), 96)
    target = np.linspace(0.01, 0.99, len(dates))
    sampled = np.ones(len(dates), dtype=bool)

    valid, weights, stats = campaign.session_equal_target_weights(
        dates, target, sampled
    )

    assert valid.all()
    assert stats["training_sessions"] == 60
    frame = pd.DataFrame({"date": dates, "weight": weights})
    daily = frame.groupby("date")["weight"].sum().to_numpy()
    assert np.allclose(daily, np.full(60, 1.0 / 60))


def test_frozen_common_context_is_valid() -> None:
    protocol, manifest = campaign.validate_common()

    assert protocol["model_trial"]["trial_id"] == campaign.TRIAL_ID
    assert manifest["dataset_sha256"] == campaign.campaign286.DESIGN_DATASET_SHA256
