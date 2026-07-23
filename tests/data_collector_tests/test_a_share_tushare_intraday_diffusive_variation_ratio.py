import math

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_diffusive_variation_ratio as RESEARCH


def continuous_closes_from_moves(
    moves: np.ndarray, *, morning_level: float = 100.0, afternoon_level: float = 100.0
) -> np.ndarray:
    assert moves.shape == (2, 119)
    levels = (morning_level, afternoon_level)
    halves = [
        level * np.exp(np.concatenate(([0.0], np.cumsum(half_moves))))
        for level, half_moves in zip(levels, moves)
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


def test_preregistration_freezes_diffusive_variation_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 39
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert "amount" in candidate["source_fields_forbidden"]
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert len(comparisons) == 15
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
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 39
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert evidence["terminal_up_move_amount_share_record"]["sha256"] == (
        RESEARCH.previous.TERMINAL_RECORD_SHA256
    )


def test_diagnostic_protocol_binds_passed_no_return_evidence():
    spec = RESEARCH.load_diagnostic_preregistration()
    evidence = spec["no_return_evidence"]
    snapshot = evidence["candidate_snapshot"]
    coverage = evidence["coverage_and_capacity"]
    uniqueness = evidence["uniqueness"]
    assert evidence["protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert snapshot["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    assert snapshot["eligible_rows"] == 7_695_088
    assert snapshot["zero_realized_variance_rows"] == 29_410
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed"] is True
    assert uniqueness["all_fifteen_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 15
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_terminal_record_binds_single_diagnostic_and_rejection():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    assert record["status"] == (
        "terminal_rejected_at_association_stability_and_executable_topk_gates"
    )
    assert record["no_return_results"]["comparison_factor_count"] == 15
    assert record["no_return_results"][
        "all_fifteen_uniqueness_gates_passed"
    ] is True
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["mean_rank_ic"] == pytest.approx(
        -0.022508040256830272
    )
    assert record["return_results"][
        "execution_aware_top3_net_cumulative_return"
    ] == pytest.approx(-0.8559411398232839)
    assert record["return_results"][
        "pilot_net_cumulative_return_at_ten_bp_each_side"
    ] == pytest.approx(-0.23238649620750873)
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["selection_allowed"] is False
    assert record["research_boundary"][
        "same_history_combination_return_evaluation_performed"
    ] is False


def test_equal_returns_match_closed_form():
    output, quality = compute(np.full((2, 119), 0.0001))
    expected = (math.pi / 2.0) * (236.0 / 238.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_realized_variance_rows": 0,
        "invalid_required_close_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "nonfinite_realized_variance_or_bipower_rows": 0,
        "nonfinite_ratio_rows": 0,
        "numerical_endpoint_canonicalization_rows": 0,
        "diffusive_variation_ratio_range_violation_rows": 0,
    }


def test_isolated_jump_has_zero_bipower_share():
    moves = np.zeros((2, 119))
    moves[0, 40] = 0.02
    output, _ = compute(moves)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)


def test_known_adjacent_returns_match_formula():
    moves = np.zeros((2, 119))
    moves[0, 20:23] = [0.01, -0.02, 0.03]
    output, _ = compute(moves)
    expected = (math.pi / 2.0) * (0.01 * 0.02 + 0.02 * 0.03) / (
        0.01**2 + 0.02**2 + 0.03**2
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)


def test_factor_is_sign_blind():
    moves = np.zeros((2, 119))
    moves[0, 5:9] = [0.01, -0.03, 0.02, -0.015]
    first, _ = compute(moves)
    second, _ = compute(-moves)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_factor_is_invariant_to_common_price_scale():
    moves = np.full((2, 119), 0.0001)
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


def test_cross_lunch_jump_is_excluded():
    closes = continuous_closes_from_moves(
        np.zeros((2, 119)), morning_level=100.0, afternoon_level=200.0
    )
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["zero_realized_variance_rows"] == 1


def test_standalone_0930_close_is_excluded():
    moves = np.full((2, 119), 0.0001)
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


def test_zero_variation_stays_missing():
    output, quality = compute(np.zeros((2, 119)))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_realized_variance_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_invalid_required_close_stays_missing(invalid):
    closes = continuous_closes_from_moves(np.full((2, 119), 0.0001))
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_close_rows"] == 1


def test_only_joint_base_dates_are_used():
    closes = continuous_closes_from_moves(np.full((2, 119), 0.0001))
    raw = pd.concat(
        [source_frame("2024-01-02", closes), source_frame("2024-01-03", closes)],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-03"), symbol="SH600000"
    )
    assert output["trade_date"].tolist() == [pd.Timestamp("2024-01-03")]
    assert quality["eligible_rows"] == 1


def test_extra_source_field_is_rejected():
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(np.full((2, 119), 0.0001))
    )
    raw["amount"] = 1.0
    with pytest.raises(RESEARCH.IntradayDiffusiveVariationRatioError, match="columns"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )


def test_grid_loss_is_rejected():
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(np.full((2, 119), 0.0001))
    ).iloc[:-1]
    with pytest.raises(
        RESEARCH.IntradayDiffusiveVariationRatioError, match="241-row grid"
    ):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
