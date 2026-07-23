import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_market_idiosyncratic_share as RESEARCH,
)


TRADE_DATE = pd.Timestamp("2024-01-02")
SYMBOL = "SH600000"


def source_frame(returns: np.ndarray) -> pd.DataFrame:
    returns = np.asarray(returns, dtype=float)
    assert returns.shape == (RESEARCH.RETURN_POSITIONS,)
    minute_codes = sorted(RESEARCH.SOURCE_MINUTE_CODE_SET)
    timestamps = [
        TRADE_DATE + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in minute_codes
    ]
    continuous_closes = np.empty(240, dtype=float)
    continuous_closes[0] = 10.0
    continuous_closes[1:120] = 10.0 * np.exp(np.cumsum(returns[:119]))
    continuous_closes[120] = 20.0
    continuous_closes[121:240] = 20.0 * np.exp(np.cumsum(returns[119:]))
    close_by_code = {
        code: close
        for code, close in zip(
            RESEARCH.CONTINUOUS_MINUTE_CODES,
            continuous_closes,
            strict=True,
        )
    }
    closes = [999.0 if code == 570 else close_by_code[code] for code in minute_codes]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": SYMBOL,
            "provider": "tushare",
            "close": closes,
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame() -> pd.DataFrame:
    return pd.DataFrame({"trade_date": [TRADE_DATE], "symbol": [SYMBOL]})


def benchmark(
    own_returns: np.ndarray,
    peer_returns: np.ndarray,
    *,
    peer_count: int = RESEARCH.MINIMUM_LEAVE_ONE_OUT_PEERS,
) -> RESEARCH.MarketBenchmark:
    own_returns = np.asarray(own_returns, dtype=float)
    peer_returns = np.asarray(peer_returns, dtype=float)
    return RESEARCH.MarketBenchmark(
        dates=pd.DatetimeIndex([TRADE_DATE]),
        return_sums=(own_returns + peer_count * peer_returns).reshape(1, -1),
        valid_stock_counts=np.full(
            (1, RESEARCH.RETURN_POSITIONS),
            peer_count + 1,
            dtype=np.int32,
        ),
        date_to_index={TRADE_DATE: 0},
        frame_sha256="unit-test-market-benchmark",
    )


def compute(own_returns: np.ndarray, peer_returns: np.ndarray, *, peer_count=50):
    raw = source_frame(own_returns)
    _, extracted, valid = RESEARCH.extract_partition_returns(
        raw, base_frame(), symbol=SYMBOL
    )
    assert valid.tolist() == [True]
    return RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(extracted[0], peer_returns, peer_count=peer_count),
        symbol=SYMBOL,
    )


def smooth_vectors() -> tuple[np.ndarray, np.ndarray]:
    angle = np.linspace(0.0, 8.0 * np.pi, RESEARCH.RETURN_POSITIONS, endpoint=False)
    return 0.001 * np.sin(angle), 0.001 * np.cos(angle)


def test_preregistration_freezes_cross_sectional_mechanism_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 45
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert validity["minimum_leave_one_out_peers_at_every_position"] == 50
    assert validity["ordinary_pearson_with_intercept"] is True
    assert len(comparisons) == 21
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
    assert snapshot["constant_stock_return_vector_rows"] == 29_410
    assert snapshot["insufficient_leave_one_out_peer_rows"] == 0
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert uniqueness["all_twenty_one_comparisons_passed"] is True
    assert len(uniqueness["comparison_medians"]) == 21
    assert tuple(uniqueness["comparison_medians"]) == RESEARCH.COMPARISON_FACTORS
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_single_use_guard_rejects_existing_marker(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        RESEARCH.IntradayMarketIdiosyncraticShareError,
        match="already consumed",
    ):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_single_diagnostic_and_both_failed_gates():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    repair = record["ordered_protocol"]["no_return_audit_infrastructure_repair"]
    no_return = record["no_return_results"]
    results = record["return_results"]
    artifacts = record["historical_artifacts"]
    assert repair["sha256"] == RESEARCH.NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR_SHA256
    assert repair["formula_direction_comparisons_order_or_gates_changed"] is False
    assert no_return["comparison_factor_count"] == 21
    assert no_return["all_twenty_one_uniqueness_gates_passed"] is True
    assert results["cohorts"] == 539
    assert results["mean_rank_ic"] == pytest.approx(-0.011522848933218546)
    assert results["association_stability_gate_passed"] is False
    assert results["topk_viability_gate_passed"] is False
    assert results["execution_aware_top3_net_cumulative_return"] == pytest.approx(
        -0.585483219525998
    )
    assert results["pilot_net_cumulative_return_at_ten_bp_each_side"] == pytest.approx(
        -0.18375337712907258
    )
    assert results["pilot_maximum_daily_amount_participation"] == pytest.approx(
        0.010161411961011476
    )
    assert artifacts["diagnostic"]["sha256"] == RESEARCH.DIAGNOSTIC_SHA256
    assert (
        artifacts["single_use_consumption_marker"]["sha256"]
        == RESEARCH.CONSUMPTION_MARKER_SHA256
    )
    assert record["decision"]["aggregation_allowed"] is False


def test_perfect_market_coupling_has_zero_idiosyncratic_share():
    own, _ = smooth_vectors()
    output, quality = compute(own, own)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0, abs=1e-12)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_orthogonal_market_path_has_unit_idiosyncratic_share():
    own, peers = smooth_vectors()
    output, quality = compute(own, peers)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0, abs=1e-12)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["range_violation_rows"] == 0


def test_candidate_stock_is_removed_from_market_sum():
    own, peers = smooth_vectors()
    output, _ = compute(own, peers)
    expected = 1.0 - np.corrcoef(own, peers)[0, 1] ** 2
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)


def test_other_stocks_change_factor_while_own_path_stays_fixed():
    own, orthogonal = smooth_vectors()
    coupled, _ = compute(own, own)
    independent, _ = compute(own, orthogonal)
    assert coupled.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0, abs=1e-12)
    assert independent.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0, abs=1e-12)


def test_fewer_than_fifty_leave_one_out_peers_is_missing():
    own, peers = smooth_vectors()
    output, quality = compute(own, peers, peer_count=49)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["insufficient_leave_one_out_peer_rows"] == 1


def test_constant_stock_return_vector_is_missing():
    _, peers = smooth_vectors()
    own = np.zeros(RESEARCH.RETURN_POSITIONS)
    output, quality = compute(own, peers)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_stock_return_vector_rows"] == 1


def test_constant_leave_one_out_market_vector_is_missing():
    own, _ = smooth_vectors()
    peers = np.zeros(RESEARCH.RETURN_POSITIONS)
    output, quality = compute(own, peers)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert quality["constant_market_return_vector_rows"] == 1


def test_standalone_0930_and_lunch_price_level_are_excluded():
    own, peers = smooth_vectors()
    raw = source_frame(own)
    first_base, first_returns, first_valid = RESEARCH.extract_partition_returns(
        raw, base_frame(), symbol=SYMBOL
    )
    raw.loc[raw["datetime"].dt.strftime("%H:%M") == "09:30", "close"] = np.nan
    afternoon = raw["datetime"].dt.strftime("%H:%M").between("13:01", "15:00")
    raw.loc[afternoon, "close"] *= 37.0
    second_base, second_returns, second_valid = RESEARCH.extract_partition_returns(
        raw, base_frame(), symbol=SYMBOL
    )
    assert first_base.equals(second_base)
    assert first_valid.tolist() == [True]
    assert second_valid.tolist() == [True]
    np.testing.assert_allclose(first_returns, second_returns, atol=1e-14)
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(own, peers),
        symbol=SYMBOL,
    )
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_close_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, np.inf, 0.0, -1.0])
def test_invalid_required_continuous_close_stays_missing(invalid):
    own, peers = smooth_vectors()
    raw = source_frame(own)
    continuous_mask = raw["datetime"].dt.strftime("%H:%M") != "09:30"
    raw.loc[raw.index[continuous_mask][20], "close"] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame(),
        benchmark(own, peers),
        symbol=SYMBOL,
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_close_rows"] == 1


def test_duplicate_timestamp_is_rejected():
    own, peers = smooth_vectors()
    raw = source_frame(own)
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayMarketIdiosyncraticShareError,
        match="identity or timestamp",
    ):
        RESEARCH.compute_partition_frame(
            raw,
            base_frame(),
            benchmark(own, peers),
            symbol=SYMBOL,
        )


def test_batched_comparison_scan_aligns_only_requested_stock_days(
    tmp_path, monkeypatch
):
    dates = pd.date_range("2024-01-02", periods=2, freq="B")
    symbols = [f"SH{600000 + index:06d}" for index in range(60)]
    frame = pd.DataFrame(
        [
            {
                "trade_date": trade_date,
                "symbol": symbol,
                "comparison_a": float(day_index * 100 + symbol_index),
            }
            for day_index, trade_date in enumerate(dates)
            for symbol_index, symbol in enumerate(symbols)
        ]
    )
    root = tmp_path / "partitions"
    root.mkdir()
    frame.iloc[:60].to_parquet(root / "first.parquet", index=False)
    frame.iloc[60:].to_parquet(root / "second.parquet", index=False)
    requested = frame.iloc[::3].copy()
    keys = np.sort(
        RESEARCH._compact_stock_day_keys(requested["trade_date"], requested["symbol"])
    )
    monkeypatch.setattr(
        RESEARCH.np,
        "isin",
        lambda *args, **kwargs: pytest.fail(
            "comparison scan must use sorted-key lookup"
        ),
    )
    aligned = RESEARCH._load_filtered_comparison_values(
        root,
        ["comparison_a"],
        keys,
        expected_total_rows=len(frame),
    )
    expected = requested.assign(
        key=RESEARCH._compact_stock_day_keys(
            requested["trade_date"], requested["symbol"]
        )
    ).sort_values("key")["comparison_a"]
    np.testing.assert_allclose(aligned["comparison_a"], expected.to_numpy())


def test_compact_aligned_correlation_matches_dataframe_reference():
    dates = pd.date_range("2023-01-03", periods=100, freq="B")
    symbols = [f"SH{600000 + index:06d}" for index in range(60)]
    candidate = pd.DataFrame(
        [
            {
                "trade_date": trade_date,
                "symbol": symbol,
                RESEARCH.FACTOR_NAME: float(symbol_index + 0.01 * np.sin(day_index)),
            }
            for day_index, trade_date in enumerate(dates)
            for symbol_index, symbol in enumerate(symbols)
        ]
    )
    comparison_name = "comparison_a"
    comparison = candidate[["trade_date", "symbol"]].copy()
    comparison[comparison_name] = candidate[RESEARCH.FACTOR_NAME].to_numpy() + np.tile(
        np.sin(np.arange(60)), len(dates)
    )
    gate = {
        "minimum_pairwise_names_per_session": 50,
        "minimum_pairwise_sessions_per_comparison": 100,
        "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
    }
    reference = RESEARCH._one_comparison_result(
        candidate,
        comparison,
        comparison_name,
        "higher",
        gate,
    )
    keys = RESEARCH._compact_stock_day_keys(
        candidate["trade_date"], candidate["symbol"]
    )
    order = np.argsort(keys, kind="stable")
    compact = RESEARCH._aligned_comparison_result(
        candidate_keys=keys[order],
        candidate_values=candidate[RESEARCH.FACTOR_NAME].to_numpy()[order],
        comparison_values=comparison[comparison_name].to_numpy()[order],
        comparison=comparison_name,
        direction="higher",
        gate=gate,
    )
    assert compact["pairwise_sessions"] == reference["pairwise_sessions"]
    assert (
        compact["minimum_pairwise_names_observed"]
        == reference["minimum_pairwise_names_observed"]
    )
    assert compact["median_daily_rank_correlation"] == pytest.approx(
        reference["median_daily_rank_correlation"]
    )
    assert compact["daily_rank_correlation_p05"] == pytest.approx(
        reference["daily_rank_correlation_p05"]
    )
    assert compact["daily_rank_correlation_p95"] == pytest.approx(
        reference["daily_rank_correlation_p95"]
    )
    assert compact["gate_passed"] == reference["gate_passed"]
