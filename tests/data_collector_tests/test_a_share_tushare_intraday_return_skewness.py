import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_return_skewness as RESEARCH


def continuous_closes_from_moves(moves: np.ndarray) -> np.ndarray:
    assert moves.shape == (2, 119)
    halves = [
        100.0 * np.exp(np.concatenate(([0.0], np.cumsum(half))))
        for half in moves
    ]
    return np.concatenate(halves)


def source_frame(date: str, continuous_closes: np.ndarray) -> pd.DataFrame:
    assert continuous_closes.shape == (240,)
    day = pd.Timestamp(date)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.previous.SOURCE_MINUTE_CODES
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.concatenate(([99.0], continuous_closes)),
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def compute(moves: np.ndarray):
    return RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", continuous_closes_from_moves(moves)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )


def population_skewness(values: np.ndarray) -> float:
    centered = values - values.mean()
    m2 = np.mean(centered**2)
    m3 = np.mean(centered**3)
    return float(m3 / m2**1.5)


def test_preregistration_freezes_skewness_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    grid = candidate["bar_grid"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 42
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert grid["return_observations"] == 238
    assert grid["cross_lunch_return_included"] is False
    assert validity["theoretical_range"] == "unbounded_real"
    assert validity["fisher_finite_sample_bias_correction_applied"] is False
    assert len(comparisons) == 18
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_repository_chain_binds_entropy_terminal_state():
    evidence = RESEARCH.validate_repository_chain(
        RESEARCH.load_preregistration()
    )
    assert evidence["preregistered_current_research_state"][
        "terminal_mechanism_count_before_this_candidate"
    ] == 42
    assert evidence["return_variance_entropy_terminal_record"][
        "sha256"
    ] == RESEARCH.PREVIOUS_TERMINAL_RECORD_SHA256
    assert evidence["return_skewness_mechanism_overlap_audit"][
        "sha256"
    ] == RESEARCH.MECHANISM_AUDIT_SHA256


def test_one_positive_tail_move_has_positive_population_skewness():
    moves = np.zeros((2, 119))
    moves[0, 0] = 0.01
    output, quality = compute(moves)
    expected = population_skewness(moves.reshape(-1))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)
    assert output.loc[0, RESEARCH.FACTOR_NAME] > 0
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["zero_second_centered_moment_rows"] == 0


def test_one_negative_tail_move_has_negative_population_skewness():
    moves = np.zeros((2, 119))
    moves[1, -1] = -0.01
    output, quality = compute(moves)
    expected = population_skewness(moves.reshape(-1))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)
    assert output.loc[0, RESEARCH.FACTOR_NAME] < 0
    assert quality["eligible_rows"] == 1


def test_symmetric_returns_have_zero_skewness():
    moves = np.tile(np.array([-0.002, 0.002]), 119).reshape(2, 119)
    output, quality = compute(moves)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        0.0, abs=1e-11
    )
    assert quality["eligible_rows"] == 1


def test_factor_is_invariant_to_common_price_scale():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    closes = continuous_closes_from_moves(moves)
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes * 37.0),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_factor_is_invariant_to_common_return_magnitude():
    moves = np.linspace(-0.001, 0.003, 238).reshape(2, 119)
    first, _ = compute(moves)
    second, _ = compute(moves * 4.0)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_cross_lunch_transition_is_excluded():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    closes = continuous_closes_from_moves(moves)
    shifted = closes.copy()
    shifted[120:] *= 100.0
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", shifted),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_standalone_0930_close_is_excluded():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(moves)
    )
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "close"] = np.nan
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_zero_second_centered_moment_stays_missing():
    output, quality = compute(np.zeros((2, 119)))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_second_centered_moment_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_invalid_required_close_stays_missing(invalid):
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    closes = continuous_closes_from_moves(moves)
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_close_rows"] == 1


def test_only_joint_base_dates_are_used():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    closes = continuous_closes_from_moves(moves)
    raw = pd.concat(
        [
            source_frame("2024-01-02", closes),
            source_frame("2024-01-03", closes),
        ],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-03"), symbol="SH600000"
    )
    assert output["trade_date"].tolist() == [pd.Timestamp("2024-01-03")]
    assert quality["eligible_rows"] == 1


def test_extra_source_field_is_rejected():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(moves)
    )
    raw["amount"] = 1.0
    with pytest.raises(RESEARCH.IntradayReturnSkewnessError, match="columns"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )


def test_grid_loss_is_rejected():
    moves = np.linspace(-0.002, 0.004, 238).reshape(2, 119)
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(moves)
    ).iloc[:-1]
    with pytest.raises(
        RESEARCH.IntradayReturnSkewnessError, match="241-row grid"
    ):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
