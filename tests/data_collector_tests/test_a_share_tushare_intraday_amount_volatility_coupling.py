import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_amount_volatility_coupling as RESEARCH


def continuous_closes_from_moves(moves: np.ndarray) -> np.ndarray:
    assert moves.shape == (2, 119)
    halves = [
        100.0 * np.exp(np.concatenate(([0.0], np.cumsum(half))))
        for half in moves
    ]
    return np.concatenate(halves)


def continuous_amounts_from_destination_log1p(values: np.ndarray) -> np.ndarray:
    assert values.shape == (2, 119)
    halves = [np.concatenate(([1.0], np.expm1(half))) for half in values]
    return np.concatenate(halves)


def source_frame(
    date: str,
    continuous_closes: np.ndarray,
    continuous_amounts: np.ndarray,
) -> pd.DataFrame:
    assert continuous_closes.shape == (240,)
    assert continuous_amounts.shape == (240,)
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
            "amount": np.concatenate(([0.0], continuous_amounts)),
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"trade_date": pd.to_datetime(list(dates)), "symbol": "SH600000"}
    )


def candidate_inputs(direction: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    magnitudes = np.linspace(0.0001, 0.002, 238).reshape(2, 119)
    signs = np.where(np.arange(238).reshape(2, 119) % 2 == 0, 1.0, -1.0)
    closes = continuous_closes_from_moves(signs * magnitudes)
    if direction > 0:
        destination_log1p_amount = 10.0 + 1000.0 * magnitudes
    else:
        destination_log1p_amount = 20.0 - 1000.0 * magnitudes
    amounts = continuous_amounts_from_destination_log1p(destination_log1p_amount)
    return closes, amounts


def compute(direction: float = 1.0):
    closes, amounts = candidate_inputs(direction)
    return RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )


def test_preregistration_freezes_coupling_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    grid = candidate["bar_grid"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 40
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert grid["return_amount_pairs"] == 238
    assert grid["cross_lunch_return_or_pair_included"] is False
    assert validity["theoretical_closed_interval"] == [-1, 1]
    assert len(comparisons) == 16
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
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 40
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert evidence["terminal_diffusive_variation_ratio_record"]["sha256"] == (
        RESEARCH.previous.TERMINAL_RECORD_SHA256
    )


def test_perfect_positive_coupling():
    output, quality = compute(1.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["invalid_required_value_rows"] == 0
    assert quality["constant_absolute_return_rows"] == 0
    assert quality["constant_log1p_amount_rows"] == 0
    assert quality["amount_volatility_coupling_range_violation_rows"] == 0


def test_perfect_negative_coupling():
    output, _ = compute(-1.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(-1.0)


def test_factor_is_invariant_to_common_price_scale():
    closes, amounts = candidate_inputs()
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes * 37.0, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_factor_is_invariant_to_affine_log1p_amount_shift():
    closes, amounts = candidate_inputs()
    shifted_amounts = (amounts + 1.0) * 17.0 - 1.0
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, shifted_amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_cross_lunch_transition_is_excluded():
    closes, amounts = candidate_inputs()
    shifted = closes.copy()
    shifted[120:] *= 100.0
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", shifted, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_standalone_0930_values_are_excluded():
    closes, amounts = candidate_inputs()
    raw = source_frame("2024-01-02", closes, amounts)
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "close"] = np.nan
    raw.loc[0, "amount"] = -1.0
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_first_continuous_amount_in_each_half_is_not_a_destination():
    closes, amounts = candidate_inputs()
    amounts[[0, 120]] = -1.0
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_destination_amount_rows"] == 0


def test_constant_absolute_returns_stay_missing():
    closes = np.full(240, 100.0)
    _, amounts = candidate_inputs()
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_absolute_return_rows"] == 1


def test_constant_destination_amounts_stay_missing():
    closes, _ = candidate_inputs()
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_log1p_amount_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_invalid_required_close_stays_missing(invalid):
    closes, amounts = candidate_inputs()
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_close_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, -1.0, np.inf])
def test_invalid_destination_amount_stays_missing(invalid):
    closes, amounts = candidate_inputs()
    amounts[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_destination_amount_rows"] == 1


def test_only_joint_base_dates_are_used():
    closes, amounts = candidate_inputs()
    raw = pd.concat(
        [
            source_frame("2024-01-02", closes, amounts),
            source_frame("2024-01-03", closes, amounts),
        ],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-03"), symbol="SH600000"
    )
    assert output["trade_date"].tolist() == [pd.Timestamp("2024-01-03")]
    assert quality["eligible_rows"] == 1


def test_extra_source_field_is_rejected():
    closes, amounts = candidate_inputs()
    raw = source_frame("2024-01-02", closes, amounts)
    raw["volume"] = 1.0
    with pytest.raises(RESEARCH.IntradayAmountVolatilityCouplingError, match="columns"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )


def test_grid_loss_is_rejected():
    closes, amounts = candidate_inputs()
    raw = source_frame("2024-01-02", closes, amounts).iloc[:-1]
    with pytest.raises(
        RESEARCH.IntradayAmountVolatilityCouplingError, match="241-row grid"
    ):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
