import math

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_return_variance_entropy as RESEARCH


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
        for code in RESEARCH.SOURCE_MINUTE_CODES
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
        {"trade_date": pd.to_datetime(list(dates)), "symbol": "SH600000"}
    )


def compute(moves: np.ndarray):
    return RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", continuous_closes_from_moves(moves)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )


def test_preregistration_freezes_entropy_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    grid = candidate["bar_grid"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 41
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert grid["variance_contributions"] == 238
    assert grid["cross_lunch_return_included"] is False
    assert validity["theoretical_closed_interval"] == [0, 1]
    assert validity[
        "zero_variance_contribution_kept_in_support_with_zero_entropy_term"
    ] is True
    assert len(comparisons) == 17
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_repository_chain_accepts_preregistered_predecessor_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    predecessor = evidence["preregistered_current_research_state"]
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 41
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert evidence["terminal_amount_volatility_coupling_record"]["sha256"] == (
        RESEARCH.previous.TERMINAL_RECORD_SHA256
    )


def test_uniform_squared_returns_have_unit_entropy():
    signs = np.where(np.arange(238).reshape(2, 119) % 2 == 0, 1.0, -1.0)
    output, quality = compute(signs * 0.001)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["zero_realized_variance_rows"] == 0
    assert quality["return_variance_entropy_range_violation_rows"] == 0


def test_single_nonzero_return_has_zero_entropy():
    moves = np.zeros((2, 119))
    moves[0, 0] = 0.01
    output, quality = compute(moves)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_two_equal_nonzero_returns_use_full_238_position_normalizer():
    moves = np.zeros((2, 119))
    moves[0, 0] = 0.01
    moves[1, 0] = -0.01
    output, _ = compute(moves)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        math.log(2.0) / math.log(238.0)
    )


def test_factor_is_invariant_to_common_price_scale():
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
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
    moves = np.linspace(-0.001, 0.001, 238).reshape(2, 119)
    first, _ = compute(moves)
    second, _ = compute(moves * 4.0)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_cross_lunch_transition_is_excluded():
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
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
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
    raw = source_frame("2024-01-02", continuous_closes_from_moves(moves))
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


def test_zero_realized_variance_stays_missing():
    output, quality = compute(np.zeros((2, 119)))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_realized_variance_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_invalid_required_close_stays_missing(invalid):
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
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
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
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
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
    raw = source_frame("2024-01-02", continuous_closes_from_moves(moves))
    raw["amount"] = 1.0
    with pytest.raises(RESEARCH.IntradayReturnVarianceEntropyError, match="columns"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )


def test_grid_loss_is_rejected():
    moves = np.linspace(-0.002, 0.002, 238).reshape(2, 119)
    raw = source_frame("2024-01-02", continuous_closes_from_moves(moves)).iloc[:-1]
    with pytest.raises(
        RESEARCH.IntradayReturnVarianceEntropyError, match="241-row grid"
    ):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
