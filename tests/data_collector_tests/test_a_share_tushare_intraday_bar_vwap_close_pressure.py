import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_bar_vwap_close_pressure as RESEARCH,
)


def source_frame(date: str = "2024-01-02") -> pd.DataFrame:
    day = pd.Timestamp(date)
    minute_codes = sorted(RESEARCH.SOURCE_MINUTE_CODE_SET)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in minute_codes
    ]
    rows = len(timestamps)
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.full(rows, 10.0),
            "volume": np.full(rows, 100.0),
            "amount": np.full(rows, 1000.0),
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


def test_preregistration_freezes_pressure_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 43
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert validity["zero_volume_zero_amount_bar_policy"] == ("inactive_zero_weight")
    assert validity["one_sided_zero_activity_pair_policy"] == ("stock_day_missing")
    assert validity["minimum_active_bar_count"] is None
    assert len(comparisons) == 19
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
    assert snapshot["one_sided_zero_activity_pair_rows"] == 47
    assert evidence["ordered_audit"]["sha256"] == (RESEARCH.NO_RETURN_AUDIT_SHA256)
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert uniqueness["all_nineteen_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 19
    assert tuple(uniqueness["comparison_medians"]) == (RESEARCH.COMPARISON_FACTORS)
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_terminal_record_preserves_both_gate_rejections():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    assert record["status"] == (
        "terminal_rejected_at_association_stability_and_executable_topk_gates"
    )
    assert record["no_return_results"]["comparison_factor_count"] == 19
    assert record["no_return_results"]["all_nineteen_uniqueness_gates_passed"] is True
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["mean_rank_ic"] == pytest.approx(
        -0.002435563591825198
    )
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["return_results"][
        "execution_aware_top3_net_cumulative_return"
    ] == pytest.approx(-0.8136576734464045)
    assert record["return_results"][
        "pilot_net_cumulative_return_at_ten_bp_each_side"
    ] == pytest.approx(-0.2616304469064341)


def test_repository_chain_binds_skewness_terminal_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    assert (
        evidence["preregistered_current_research_state"][
            "terminal_mechanism_count_before_this_candidate"
        ]
        == 43
    )
    assert (
        evidence["return_skewness_terminal_record"]["sha256"]
        == RESEARCH.PREVIOUS_TERMINAL_RECORD_SHA256
    )
    assert (
        evidence["bar_vwap_close_pressure_mechanism_overlap_audit"]["sha256"]
        == RESEARCH.MECHANISM_AUDIT_SHA256
    )


def test_equal_close_and_bar_vwap_has_zero_pressure():
    output, quality = compute(source_frame())
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_one_close_above_bar_vwap_has_positive_pressure():
    raw = source_frame()
    raw.loc[continuous_index(raw, 0), "close"] = 11.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(np.log(1.1) / 240.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] > 0
    assert quality["eligible_rows"] == 1


def test_one_close_below_bar_vwap_has_negative_pressure():
    raw = source_frame()
    raw.loc[continuous_index(raw, 120), "close"] = 9.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(np.log(0.9) / 240.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] < 0
    assert quality["eligible_rows"] == 1


def test_amount_weights_the_same_bar_gap():
    raw = source_frame()
    first = continuous_index(raw, 0)
    second = continuous_index(raw, 1)
    raw.loc[first, ["close", "volume", "amount"]] = [11.0, 100.0, 1000.0]
    raw.loc[second, ["close", "volume", "amount"]] = [9.0, 1000.0, 10000.0]
    output, _ = compute(raw)
    expected = (1000.0 * np.log(1.1) + 10000.0 * np.log(0.9)) / (239000.0 + 10000.0)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)


def test_common_price_scale_leaves_pressure_unchanged():
    raw = source_frame()
    raw.loc[continuous_index(raw, 10), "close"] = 10.5
    first, _ = compute(raw)
    scaled = raw.copy()
    scaled["close"] *= 37.0
    scaled["amount"] *= 37.0
    second, _ = compute(scaled)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_common_activity_scale_leaves_pressure_unchanged():
    raw = source_frame()
    raw.loc[continuous_index(raw, 10), "close"] = 10.5
    first, _ = compute(raw)
    scaled = raw.copy()
    scaled["volume"] *= 17.0
    scaled["amount"] *= 17.0
    second, _ = compute(scaled)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_zero_zero_activity_bar_is_inactive_without_minimum_count():
    raw = source_frame()
    index = continuous_index(raw, 20)
    raw.loc[index, ["volume", "amount"]] = 0.0
    raw.loc[continuous_index(raw, 21), "close"] = 11.0
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(np.log(1.1) / 239.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["inactive_zero_zero_bars"] == 1


@pytest.mark.parametrize(
    ("volume", "amount"),
    [(0.0, 1000.0), (100.0, 0.0)],
)
def test_one_sided_zero_activity_pair_makes_day_missing(volume, amount):
    raw = source_frame()
    raw.loc[continuous_index(raw, 20), ["volume", "amount"]] = [
        volume,
        amount,
    ]
    output, quality = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["one_sided_zero_activity_pair_rows"] == 1


def test_all_zero_zero_activity_bars_leave_day_missing():
    raw = source_frame()
    for index in range(len(raw)):
        if raw.loc[index, "datetime"].strftime("%H:%M") != "09:30":
            raw.loc[index, ["volume", "amount"]] = 0.0
    output, quality = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["zero_total_active_amount_rows"] == 1


@pytest.mark.parametrize(
    ("column", "invalid"),
    [
        ("close", np.nan),
        ("close", 0.0),
        ("close", -1.0),
        ("volume", np.nan),
        ("volume", -1.0),
        ("amount", np.inf),
        ("amount", -1.0),
    ],
)
def test_invalid_required_continuous_value_stays_missing(column, invalid):
    raw = source_frame()
    raw.loc[continuous_index(raw, 20), column] = invalid
    output, _ = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_standalone_0930_values_are_excluded():
    raw = source_frame()
    first, _ = compute(raw)
    raw.loc[0, ["close", "volume", "amount"]] = [np.nan, 0.0, 1000.0]
    second, _ = compute(raw)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_duplicate_timestamp_is_rejected():
    raw = source_frame()
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayBarVwapClosePressureError,
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


def test_daily_directional_rank_correlation_respects_lower_direction():
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
        frame, "comparison", "lower", 50
    )
    assert result.loc[0, "rank_correlation"] == pytest.approx(-1.0)
