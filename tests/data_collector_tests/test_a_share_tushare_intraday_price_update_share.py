import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_price_update_share as RESEARCH


def source_frame(date: str = "2024-01-02") -> pd.DataFrame:
    day = pd.Timestamp(date)
    minute_codes = sorted(RESEARCH.SOURCE_MINUTE_CODE_SET)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in minute_codes
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.full(len(timestamps), 10.0),
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def compute(raw: pd.DataFrame):
    return RESEARCH.compute_partition_frame(
        raw,
        base_frame("2024-01-02"),
        symbol="SH600000",
    )


def continuous_index(raw: pd.DataFrame, offset: int) -> int:
    continuous = [
        index
        for index, timestamp in enumerate(raw["datetime"])
        if timestamp.strftime("%H:%M") != "09:30"
    ]
    return continuous[offset]


def test_preregistration_freezes_update_share_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 44
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert validity["fixed_pair_denominator"] == 238
    assert validity["constant_close_day_policy"] == "valid_zero"
    assert (
        validity["exact_close_equality_without_rounding_epsilon_or_tolerance"] is True
    )
    assert len(comparisons) == 20
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


def test_diagnostic_protocol_binds_passed_no_return_evidence():
    spec = RESEARCH.load_diagnostic_preregistration()
    evidence = spec["no_return_evidence"]
    snapshot = evidence["candidate_snapshot"]
    uniqueness = evidence["uniqueness"]
    assert evidence["protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert snapshot["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    assert snapshot["dataset_sha256"] == RESEARCH.CANDIDATE_DATASET_SHA256
    assert snapshot["eligible_rows"] == RESEARCH.EXPECTED_ELIGIBLE_ROWS
    assert snapshot["exact_price_update_pairs"] == 1_177_277_526
    assert snapshot["exact_unchanged_price_pairs"] == 661_152_998
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert uniqueness["all_twenty_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 20
    assert tuple(uniqueness["comparison_medians"]) == RESEARCH.COMPARISON_FACTORS
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_single_use_guard_rejects_existing_marker(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        RESEARCH.IntradayPriceUpdateShareError,
        match="already consumed",
    ):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_single_diagnostic_and_both_failed_gates():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    no_return = record["no_return_results"]
    results = record["return_results"]
    artifacts = record["historical_artifacts"]
    assert no_return["comparison_factor_count"] == 20
    assert no_return["all_twenty_uniqueness_gates_passed"] is True
    assert results["cohorts"] == 539
    assert results["mean_rank_ic"] == pytest.approx(-0.027741031269307864)
    assert results["association_stability_gate_passed"] is False
    assert results["topk_viability_gate_passed"] is False
    assert results["execution_aware_top3_net_cumulative_return"] == pytest.approx(
        4.151344445674202
    )
    assert results["pilot_net_cumulative_return_at_ten_bp_each_side"] == pytest.approx(
        -0.01381171680384985
    )
    assert artifacts["diagnostic"]["sha256"] == RESEARCH.DIAGNOSTIC_SHA256
    assert (
        artifacts["single_use_consumption_marker"]["sha256"]
        == RESEARCH.CONSUMPTION_MARKER_SHA256
    )
    assert record["decision"]["aggregation_allowed"] is False


def test_constant_close_day_is_valid_zero():
    output, quality = compute(source_frame())
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["exact_price_update_pairs"] == 0
    assert quality["exact_unchanged_price_pairs"] == 238


def test_one_boundary_close_change_counts_one_update():
    raw = source_frame()
    raw.loc[continuous_index(raw, 0), "close"] = 11.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0 / 238.0)
    assert quality["exact_price_update_pairs"] == 1
    assert quality["exact_unchanged_price_pairs"] == 237


def test_one_interior_close_change_counts_two_updates():
    raw = source_frame()
    raw.loc[continuous_index(raw, 20), "close"] = 11.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(2.0 / 238.0)
    assert quality["exact_price_update_pairs"] == 2


def test_lunch_boundary_is_excluded():
    raw = source_frame()
    raw.loc[continuous_index(raw, 119), "close"] = 11.0
    raw.loc[continuous_index(raw, 120), "close"] = 12.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(2.0 / 238.0)
    assert quality["exact_price_update_pairs"] == 2


def test_exact_equality_uses_no_epsilon():
    raw = source_frame()
    raw.loc[continuous_index(raw, 0), "close"] = np.nextafter(10.0, 11.0)
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0 / 238.0)
    assert quality["exact_price_update_pairs"] == 1


def test_common_positive_price_scale_leaves_share_unchanged():
    raw = source_frame()
    raw.loc[continuous_index(raw, 10), "close"] = 10.5
    first, _ = compute(raw)
    scaled = raw.copy()
    scaled["close"] *= 37.0
    second, _ = compute(scaled)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_standalone_0930_close_is_excluded():
    raw = source_frame()
    first, _ = compute(raw)
    raw.loc[0, "close"] = np.nan
    second, _ = compute(raw)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


@pytest.mark.parametrize("invalid", [np.nan, np.inf, 0.0, -1.0])
def test_invalid_required_continuous_close_stays_missing(invalid):
    raw = source_frame()
    raw.loc[continuous_index(raw, 20), "close"] = invalid
    output, quality = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_close_rows"] == 1


def test_duplicate_timestamp_is_rejected():
    raw = source_frame()
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayPriceUpdateShareError,
        match="identity or timestamp",
    ):
        compute(raw)


def test_daily_directional_rank_correlation_respects_higher_direction():
    dates = pd.to_datetime(["2024-01-02"] * 50)
    values = np.arange(50, dtype=float)
    frame = pd.DataFrame(
        {
            "trade_date": dates,
            RESEARCH.FACTOR_NAME: values,
            "comparison": values,
        }
    )
    result = RESEARCH._daily_directional_rank_correlations(
        frame, "comparison", "higher", 50
    )
    assert result.loc[0, "rank_correlation"] == pytest.approx(1.0)
