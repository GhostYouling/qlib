import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_market_amount_profile_synchronization as RESEARCH,
)


TRADE_DATE = pd.Timestamp("2024-01-02")
SYMBOL = "SH600000"


def normalized(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return values / values.sum()


def smooth_profiles() -> tuple[np.ndarray, np.ndarray]:
    angle = np.linspace(
        0.0,
        8.0 * np.pi,
        RESEARCH.PROFILE_POSITIONS,
        endpoint=False,
    )
    return normalized(1.0 + 0.5 * np.sin(angle)), normalized(1.0 + 0.5 * np.cos(angle))


def source_frame(profile: np.ndarray, *, auction_amount: float = 999.0) -> pd.DataFrame:
    profile = normalized(profile)
    minute_codes = sorted(RESEARCH.SOURCE_MINUTE_CODE_SET)
    timestamps = [
        TRADE_DATE + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in minute_codes
    ]
    amount_by_code = {
        code: amount
        for code, amount in zip(
            RESEARCH.CONTINUOUS_MINUTE_CODES,
            profile * 1_000_000.0,
            strict=True,
        )
    }
    amounts = [
        auction_amount if code == 570 else amount_by_code[code] for code in minute_codes
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": SYMBOL,
            "provider": "tushare",
            "amount": amounts,
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame() -> pd.DataFrame:
    return pd.DataFrame({"trade_date": [TRADE_DATE], "symbol": [SYMBOL]})


def benchmark(
    own_profile: np.ndarray,
    peer_profile: np.ndarray,
    *,
    peer_count: int = RESEARCH.MINIMUM_LEAVE_ONE_OUT_PEERS,
) -> RESEARCH.AmountProfileBenchmark:
    own_profile = normalized(own_profile)
    peer_profile = normalized(peer_profile)
    return RESEARCH.AmountProfileBenchmark(
        dates=pd.DatetimeIndex([TRADE_DATE]),
        profile_sums=(own_profile + peer_count * peer_profile).reshape(1, -1),
        valid_stock_counts=np.full(
            (1, RESEARCH.PROFILE_POSITIONS),
            peer_count + 1,
            dtype=np.int32,
        ),
        date_to_index={TRADE_DATE: 0},
        frame_sha256="unit-test-market-profile-benchmark",
    )


def compute(own_profile: np.ndarray, peer_profile: np.ndarray, *, peer_count=50):
    raw = source_frame(own_profile)
    _, extracted, valid, _ = RESEARCH.extract_partition_profiles(
        raw,
        base_frame(),
        symbol=SYMBOL,
    )
    assert valid.tolist() == [True]
    return RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(extracted[0], peer_profile, peer_count=peer_count),
        symbol=SYMBOL,
    )


def test_preregistration_freezes_cross_stock_amount_mechanism_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 47
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["bar_grid"]["09_30_included"] is False
    assert validity["minimum_leave_one_out_peers_at_every_position"] == 50
    assert validity["allowed_closed_interval"] == [-1, 1]
    assert len(comparisons) == 23
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
    assert snapshot["insufficient_leave_one_out_peer_rows"] == 0
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert uniqueness["all_twenty_three_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 23
    assert tuple(uniqueness["comparison_medians"]) == RESEARCH.COMPARISON_FACTORS
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_single_use_guard_rejects_existing_marker(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        RESEARCH.IntradayMarketAmountProfileSynchronizationError,
        match="already consumed",
    ):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_single_diagnostic_and_both_failed_gates():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    no_return = record["no_return_results"]
    results = record["return_results"]
    artifacts = record["historical_artifacts"]
    assert no_return["comparison_factor_count"] == 23
    assert no_return["all_twenty_three_uniqueness_gates_passed"] is True
    assert results["cohorts"] == 539
    assert results["mean_rank_ic"] == pytest.approx(-0.011744812824529938)
    assert results["association_stability_gate_passed"] is False
    assert results["topk_viability_gate_passed"] is False
    assert results["execution_aware_top3_net_cumulative_return"] == pytest.approx(
        -0.536413733053481
    )
    assert results["pilot_net_cumulative_return_at_ten_bp_each_side"] == pytest.approx(
        -0.1317638058590641
    )
    assert results["pilot_maximum_daily_amount_participation"] == pytest.approx(
        0.0004074745219262403
    )
    assert artifacts["diagnostic"]["sha256"] == RESEARCH.DIAGNOSTIC_SHA256
    assert (
        artifacts["single_use_consumption_marker"]["sha256"]
        == RESEARCH.CONSUMPTION_MARKER_SHA256
    )
    assert record["decision"]["aggregation_allowed"] is False


def test_perfect_profile_alignment_has_unit_synchronization():
    own, _ = smooth_profiles()
    output, quality = compute(own, own)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0, abs=1e-12)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_orthogonal_profiles_have_zero_synchronization():
    own, peers = smooth_profiles()
    output, quality = compute(own, peers)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0, abs=1e-12)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["range_violation_rows"] == 0


def test_candidate_stock_is_removed_from_market_profile_sum():
    own, peers = smooth_profiles()
    output, _ = compute(own, peers)
    expected = np.corrcoef(own, peers)[0, 1]
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)


def test_other_stocks_change_factor_while_own_profile_stays_fixed():
    own, orthogonal = smooth_profiles()
    coupled, _ = compute(own, own)
    independent, _ = compute(own, orthogonal)
    assert coupled.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0, abs=1e-12)
    assert independent.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0, abs=1e-12)


def test_fewer_than_fifty_leave_one_out_peers_is_missing():
    own, peers = smooth_profiles()
    output, quality = compute(own, peers, peer_count=49)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["insufficient_leave_one_out_peer_rows"] == 1


def test_constant_own_profile_is_missing():
    _, peers = smooth_profiles()
    own = np.ones(RESEARCH.PROFILE_POSITIONS)
    output, quality = compute(own, peers)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_own_profile_rows"] == 1


def test_constant_leave_one_out_market_profile_is_missing():
    own, _ = smooth_profiles()
    peers = np.ones(RESEARCH.PROFILE_POSITIONS)
    output, quality = compute(own, peers)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_market_profile_rows"] == 1


def test_standalone_0930_amount_is_excluded():
    own, peers = smooth_profiles()
    first = source_frame(own, auction_amount=0.0)
    second = source_frame(own, auction_amount=9_999_999_999.0)
    _, first_profile, first_valid, _ = RESEARCH.extract_partition_profiles(
        first,
        base_frame(),
        symbol=SYMBOL,
    )
    _, second_profile, second_valid, _ = RESEARCH.extract_partition_profiles(
        second,
        base_frame(),
        symbol=SYMBOL,
    )
    assert first_valid.tolist() == [True]
    assert second_valid.tolist() == [True]
    np.testing.assert_allclose(first_profile, second_profile, atol=1e-15)
    output, quality = RESEARCH.compute_partition_frame(
        second,
        base_frame(),
        benchmark(own, peers),
        symbol=SYMBOL,
    )
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_amount_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -1.0])
def test_invalid_required_continuous_amount_stays_missing(invalid):
    own, peers = smooth_profiles()
    raw = source_frame(own)
    continuous_mask = raw["datetime"].dt.strftime("%H:%M") != "09:30"
    raw.loc[raw.index[continuous_mask][20], "amount"] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(own, peers),
        symbol=SYMBOL,
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_amount_rows"] == 1


def test_zero_continuous_session_total_stays_missing():
    _, peers = smooth_profiles()
    raw = source_frame(np.ones(RESEARCH.PROFILE_POSITIONS))
    raw.loc[raw["datetime"].dt.strftime("%H:%M") != "09:30", "amount"] = 0.0
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(np.ones(RESEARCH.PROFILE_POSITIONS), peers),
        symbol=SYMBOL,
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["nonpositive_total_amount_rows"] == 1


def test_duplicate_timestamp_is_rejected():
    own, peers = smooth_profiles()
    raw = source_frame(own)
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayMarketAmountProfileSynchronizationError,
        match="identity or timestamp",
    ):
        RESEARCH.compute_partition_frame(
            raw,
            base_frame(),
            benchmark(own, peers),
            symbol=SYMBOL,
        )
