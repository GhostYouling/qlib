import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_amount_lead_return_correlation as RESEARCH


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


def closes_from_half_returns(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
    *,
    morning_start: float = 100.0,
    afternoon_start: float = 100.0,
) -> np.ndarray:
    assert morning_returns.shape == (119,)
    assert afternoon_returns.shape == (119,)
    morning = morning_start * np.exp(
        np.concatenate(([0.0], np.cumsum(morning_returns)))
    )
    afternoon = afternoon_start * np.exp(
        np.concatenate(([0.0], np.cumsum(afternoon_returns)))
    )
    return np.concatenate((morning, afternoon))


def amounts_from_predictors(predictors: np.ndarray) -> np.ndarray:
    assert predictors.shape == (238,)
    morning = np.concatenate((np.expm1(predictors[:119]), [1.0]))
    afternoon = np.concatenate((np.expm1(predictors[119:]), [1.0]))
    return np.concatenate((morning, afternoon))


def candidate_inputs(response_sign: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    predictors = np.linspace(0.05, 4.0, 238)
    responses = response_sign * predictors * 1e-4
    closes = closes_from_half_returns(responses[:119], responses[119:])
    return closes, amounts_from_predictors(predictors)


def test_preregistration_freezes_lead_return_correlation_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    grid = candidate["bar_grid"]
    validity = candidate["validity"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 36
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert grid["within_morning_lead_return_pairs"] == 119
    assert grid["within_afternoon_lead_return_pairs"] == 119
    assert grid["total_lead_return_pairs"] == 238
    assert grid["lunch_break_pair_included"] is False
    assert validity["allowed_closed_interval"] == [-1, 1]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 12
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert [item["score_direction"] for item in comparisons] == list(
        RESEARCH.COMPARISON_DIRECTIONS
    )
    assert spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "all_twelve_comparisons_must_pass"
    ] is True
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_repository_chain_accepts_preregistered_predecessor_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    predecessor = evidence["preregistered_current_research_state"]
    assert predecessor["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 36
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert evidence["terminal_volatility_resolution_record"]["sha256"] == (
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
    assert snapshot["constant_preceding_amount_rows"] == 1
    assert snapshot["constant_next_return_rows"] == 29_410
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed"] is True
    assert uniqueness["all_twelve_comparisons_passed"] is True
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_terminal_record_binds_single_use_diagnostic_and_failed_dual_gate():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    assert record["factor"]["name"] == RESEARCH.FACTOR_NAME
    assert record["historical_artifacts"]["diagnostic"]["sha256"] == (
        RESEARCH.DIAGNOSTIC_SHA256
    )
    assert record["no_return_results"]["comparison_factor_count"] == 12
    assert record["no_return_results"]["all_twelve_uniqueness_gates_passed"]
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["aggregation_allowed"] is False
    assert record["decision"]["selection_allowed"] is False


def test_compute_partition_frame_perfect_positive_correlation():
    closes, amounts = candidate_inputs(1.0)
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "constant_preceding_amount_rows": 0,
        "constant_next_return_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "nonfinite_log1p_amount_rows": 0,
        "numerical_endpoint_canonicalization_rows": 0,
        "amount_lead_return_correlation_range_violation_rows": 0,
    }


def test_compute_partition_frame_perfect_negative_correlation():
    closes, amounts = candidate_inputs(-1.0)
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(-1.0)


def test_compute_partition_frame_is_invariant_to_common_price_scale():
    closes, amounts = candidate_inputs(1.0)
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes * 17.0, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_excludes_lunch_pair():
    closes, amounts = candidate_inputs(1.0)
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


def test_compute_partition_frame_excludes_standalone_0930_values():
    closes, amounts = candidate_inputs(1.0)
    raw = source_frame("2024-01-02", closes, amounts)
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "close"] = 9.9e99
    raw.loc[0, "amount"] = -9.9e99
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_constant_preceding_amount_stays_missing():
    closes, _ = candidate_inputs(1.0)
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["constant_preceding_amount_rows"] == 1


def test_compute_partition_frame_constant_next_return_stays_missing():
    predictors = np.linspace(0.05, 4.0, 238)
    closes = np.full(240, 100.0)
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts_from_predictors(predictors)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["constant_next_return_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_close_missing(invalid):
    closes, amounts = candidate_inputs(1.0)
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_value_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_amount_missing(invalid):
    closes, amounts = candidate_inputs(1.0)
    amounts[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes, amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_value_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    closes, amounts = candidate_inputs(1.0)
    raw = source_frame("2024-01-02", closes, amounts).iloc[:-1].copy()
    with pytest.raises(
        RESEARCH.IntradayAmountLeadReturnCorrelationError, match="241-row grid"
    ):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
