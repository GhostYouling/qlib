import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_amount_center_of_mass as RESEARCH


def source_frame(date: str, continuous_amounts: np.ndarray) -> pd.DataFrame:
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


def test_preregistration_freezes_amount_center_of_mass_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 37
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["source_fields_forbidden"] == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "any_daily_price",
        "any_forward_return",
    ]
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 13
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
    assert predecessor["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 37
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert evidence["terminal_amount_lead_return_correlation_record"]["sha256"] == (
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
    assert snapshot["eligible_rows"] == 7_724_498
    assert snapshot["zero_total_amount_rows"] == 0
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed"] is True
    assert uniqueness["all_thirteen_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 13
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
    assert record["no_return_results"]["comparison_factor_count"] == 13
    assert record["no_return_results"]["all_thirteen_uniqueness_gates_passed"]
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["aggregation_allowed"] is False
    assert record["decision"]["selection_allowed"] is False


def test_compute_partition_frame_uniform_amount_has_midpoint_center():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_total_amount_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_weighted_sum_rows": 0,
        "numerical_endpoint_canonicalization_rows": 0,
        "amount_center_of_mass_range_violation_rows": 0,
    }


def test_compute_partition_frame_observation_endpoints():
    first = np.zeros(240)
    first[0] = 1.0
    last = np.zeros(240)
    last[-1] = 1.0
    early, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", first),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    late, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", last),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert early.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert late.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)


def test_compute_partition_frame_is_invariant_to_common_amount_scale():
    amounts = np.linspace(1.0, 100.0, 240)
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts * 37.0),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_excludes_standalone_0930_amount():
    raw = source_frame("2024-01-02", np.linspace(1.0, 10.0, 240))
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "amount"] = -9.9e99
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_uses_only_joint_base_dates():
    raw = pd.concat(
        [
            source_frame("2024-01-02", np.ones(240)),
            source_frame("2024-01-03", np.linspace(1.0, 10.0, 240)),
        ],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-03"), symbol="SH600000"
    )
    assert output["trade_date"].tolist() == [pd.Timestamp("2024-01-03")]
    assert quality["base_rows"] == 1
    assert quality["eligible_rows"] == 1


def test_compute_partition_frame_zero_total_amount_stays_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.zeros(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_total_amount_rows"] == 1


@pytest.mark.parametrize("invalid", [np.nan, -1.0, np.inf])
def test_compute_partition_frame_invalid_required_amount_stays_missing(invalid):
    amounts = np.ones(240)
    amounts[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["invalid_required_value_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    raw = source_frame("2024-01-02", np.ones(240)).iloc[:-1].copy()
    with pytest.raises(RESEARCH.IntradayAmountCenterOfMassError, match="241-row grid"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )
