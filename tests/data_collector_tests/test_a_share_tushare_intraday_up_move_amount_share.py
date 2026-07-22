import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_up_move_amount_share as RESEARCH


def continuous_closes_from_moves(moves: np.ndarray) -> np.ndarray:
    assert moves.shape == (2, 119)
    sessions = []
    for session_moves in moves:
        sessions.append(
            100.0 * np.exp(np.concatenate(([0.0], np.cumsum(session_moves))))
        )
    return np.concatenate(sessions)


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
    )


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def compute(moves: np.ndarray, amounts: np.ndarray | None = None):
    closes = continuous_closes_from_moves(moves)
    if amounts is None:
        amounts = np.ones(240)
    return RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )


def test_preregistration_freezes_up_move_amount_share_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 38
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["source_fields_forbidden"] == [
        "open",
        "high",
        "low",
        "volume",
        "any_daily_price",
        "any_forward_return",
    ]
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 14
    assert [item["name"] for item in comparisons] == list(RESEARCH.COMPARISON_FACTORS)
    assert (
        spec["research_boundary"][
            "candidate_factor_values_observed_before_registration"
        ]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_repository_chain_accepts_preregistered_predecessor_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    predecessor = evidence["preregistered_current_research_state"]
    assert predecessor["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 38
    assert (
        predecessor["historical_binding_not_reinterpreted_as_current_file_bytes"]
        is True
    )
    assert evidence["terminal_amount_center_of_mass_record"]["sha256"] == (
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
    assert snapshot["zero_nonzero_move_amount_denominator_rows"] == 29_410
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed"] is True
    assert uniqueness["all_fourteen_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 14
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_terminal_record_binds_single_use_diagnostic_and_failed_dual_gate():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    assert record["factor"]["name"] == RESEARCH.FACTOR_NAME
    assert record["historical_artifacts"]["diagnostic"]["sha256"] == (
        RESEARCH.DIAGNOSTIC_SHA256
    )
    assert record["no_return_results"]["comparison_factor_count"] == 14
    assert record["no_return_results"]["all_fourteen_uniqueness_gates_passed"]
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["aggregation_allowed"] is False
    assert record["decision"]["selection_allowed"] is False


def test_compute_partition_frame_all_up_is_one():
    output, quality = compute(np.full((2, 119), 0.0001))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_nonzero_move_amount_denominator_rows": 0,
        "invalid_required_close_rows": 0,
        "invalid_required_amount_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "nonfinite_amount_sum_or_result_rows": 0,
        "numerical_endpoint_canonicalization_rows": 0,
        "up_move_amount_share_range_violation_rows": 0,
    }


def test_compute_partition_frame_all_down_is_zero():
    output, _ = compute(np.full((2, 119), -0.0001))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)


def test_compute_partition_frame_uses_destination_amount_and_ignores_magnitude():
    moves = np.zeros((2, 119))
    moves[0, 0] = 0.02
    moves[0, 1] = -0.50
    amounts = np.zeros(240)
    amounts[1] = 3.0
    amounts[2] = 1.0
    output, _ = compute(moves, amounts)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.75)


def test_compute_partition_frame_excludes_zero_move_amount_from_denominator():
    moves = np.zeros((2, 119))
    moves[0, 0] = 0.01
    moves[0, 1] = -0.01
    amounts = np.ones(240)
    amounts[10] = 1.0e12
    output, _ = compute(moves, amounts)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)


def test_compute_partition_frame_excludes_cross_lunch_jump():
    moves = np.zeros((2, 119))
    closes = continuous_closes_from_moves(moves)
    closes[120:] *= 2.0
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["zero_nonzero_move_amount_denominator_rows"] == 1


def test_compute_partition_frame_excludes_standalone_0930_fields():
    moves = np.full((2, 119), 0.0001)
    raw = source_frame("2024-01-02", continuous_closes_from_moves(moves), np.ones(240))
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "close"] = np.nan
    raw.loc[0, "amount"] = -9.9e99
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_is_invariant_to_common_destination_amount_scale():
    moves = np.zeros((2, 119))
    moves[0, :20] = np.where(np.arange(20) % 2 == 0, 0.01, -0.01)
    amounts = np.linspace(1.0, 100.0, 240)
    first, _ = compute(moves, amounts)
    second, _ = compute(moves, amounts * 37.0)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_all_zero_returns_stays_missing():
    output, quality = compute(np.zeros((2, 119)))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_nonzero_move_amount_denominator_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_compute_partition_frame_invalid_required_close_stays_missing(invalid):
    moves = np.full((2, 119), 0.0001)
    closes = continuous_closes_from_moves(moves)
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_close_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, -1.0, np.inf])
def test_compute_partition_frame_invalid_destination_amount_stays_missing(invalid):
    moves = np.full((2, 119), 0.0001)
    amounts = np.ones(240)
    amounts[20] = invalid
    output, quality = compute(moves, amounts)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_amount_rows"] == 1


def test_compute_partition_frame_does_not_require_session_open_amounts():
    moves = np.full((2, 119), 0.0001)
    amounts = np.ones(240)
    amounts[0] = np.nan
    amounts[120] = -1.0
    output, quality = compute(moves, amounts)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert quality["invalid_required_amount_rows"] == 0


def test_compute_partition_frame_uses_only_joint_base_dates():
    moves = np.full((2, 119), 0.0001)
    closes = continuous_closes_from_moves(moves)
    raw = pd.concat(
        [
            source_frame("2024-01-02", closes, np.ones(240)),
            source_frame("2024-01-03", closes, np.ones(240)),
        ],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-03"), symbol="SH600000"
    )
    assert output["trade_date"].tolist() == [pd.Timestamp("2024-01-03")]
    assert quality["eligible_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    moves = np.full((2, 119), 0.0001)
    raw = source_frame(
        "2024-01-02", continuous_closes_from_moves(moves), np.ones(240)
    ).iloc[:-1]
    with pytest.raises(RESEARCH.IntradayUpMoveAmountShareError, match="241-row grid"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
