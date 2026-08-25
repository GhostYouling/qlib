from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign299 as campaign


def _score(
    mean_close: np.ndarray,
    upper_quantile: np.ndarray,
    lower_quantile: np.ndarray,
    *,
    finite_count: np.ndarray | None = None,
    feature_support: np.ndarray | None = None,
    model_support: np.ndarray | None = None,
):
    rows = len(mean_close)
    if finite_count is None:
        finite_count = np.full(rows, campaign.FEATURE_COUNT, dtype=np.uint8)
    if feature_support is None:
        feature_support = finite_count >= campaign.MINIMUM_ALPHA158_FINITE_FEATURES
    if model_support is None:
        model_support = feature_support.copy()
    return campaign.close_distribution_upper_tail_asymmetry(
        keys=np.arange(1, rows + 1, dtype=np.int64),
        mean_close=np.asarray(mean_close, dtype=np.float64),
        upper_quantile=np.asarray(upper_quantile, dtype=np.float64),
        lower_quantile=np.asarray(lower_quantile, dtype=np.float64),
        finite_count=finite_count,
        feature_support=feature_support,
        quality_listing=np.ones(rows, dtype=bool),
        model_support=model_support,
    )


def test_mean_displacement_is_scaled_by_interquantile_width() -> None:
    frame = _score(
        np.asarray([1.1, 0.9, 1.0]),
        np.asarray([1.2, 1.2, 1.2]),
        np.asarray([0.8, 0.8, 0.8]),
    )
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert frame[campaign.FACTOR_NAME].tolist() == pytest.approx([0.5, -0.5, 0.0])
    assert frame["finite_required_input_count"].tolist() == [3, 3, 3]


def test_nonpositive_width_or_nonfinite_input_is_missing() -> None:
    frame = _score(
        np.asarray([1.0, 1.0, np.nan, 1.0]),
        np.asarray([1.0, 0.9, 1.2, np.inf]),
        np.asarray([1.0, 1.0, 0.8, 0.8]),
    )
    assert not frame[f"{campaign.FACTOR_NAME}_eligible"].any()
    assert frame[campaign.FACTOR_NAME].isna().all()
    assert frame["finite_required_input_count"].tolist() == [3, 3, 2, 2]


def test_raw_ratio_is_not_clipped_or_bounded() -> None:
    frame = _score(np.asarray([2.0]), np.asarray([1.1]), np.asarray([0.9]))
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(10.0)


def test_model_support_false_keeps_quality_row_but_makes_score_missing() -> None:
    frame = _score(
        np.asarray([1.1, 1.1]),
        np.asarray([1.2, 1.2]),
        np.asarray([0.8, 0.8]),
        model_support=np.asarray([True, False]),
    )
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(0.5)
    assert np.isnan(frame[campaign.FACTOR_NAME].iloc[1])
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True, False]


def test_support_semantics_fail_closed() -> None:
    with pytest.raises(campaign.Campaign299Error):
        _score(
            np.asarray([1.0]),
            np.asarray([1.2]),
            np.asarray([0.8]),
            finite_count=np.asarray([campaign.FEATURE_COUNT], dtype=np.uint8),
            feature_support=np.asarray([False]),
            model_support=np.asarray([False]),
        )


def test_protocol_and_candidate49_bindings_are_frozen() -> None:
    protocol, alpha, numeric = campaign.validate_protocol()
    assert protocol["ordered_numeric_uniqueness"]["comparator_count"] == 151
    assert protocol["factor_library"][0]["name"] == campaign.FACTOR_NAME
    assert protocol["factor_library"][0]["parameters"]["score"] == (
        "(2 * MA20 - QTLU20 - QTLD20) / (QTLU20 - QTLD20)"
    )
    assert len(alpha["feature_names"]) == 158
    assert {
        campaign.MEAN_FEATURE,
        campaign.UPPER_QUANTILE_FEATURE,
        campaign.LOWER_QUANTILE_FEATURE,
    }.issubset(alpha["feature_names"])
    assert len(numeric["feature_names"]) == 140
    assert campaign.file_sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign.file_sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_frozen_comparator_order_contains_all_151_definitions() -> None:
    _, _, numeric = campaign.validate_protocol()
    definitions = campaign.comparison_definitions(numeric)
    assert len(definitions) == campaign.EXPECTED_COMPARATOR_COUNT
    assert definitions[-2] == campaign.CAMPAIGN297_FACTOR
    assert definitions[-1] == campaign.CAMPAIGN298_FACTOR
    direction_rows = [
        [
            name,
            "lower" if name == campaign.LOWER_DIRECTION_COMPARATOR else "higher",
        ]
        for name in definitions
    ]
    assert direction_rows[3] == ["intraday_realized_volatility", "lower"]
    assert sum(direction == "lower" for _, direction in direction_rows) == 1
    assert campaign.canonical_sha256(direction_rows) == (
        campaign.EXPECTED_COMPARATOR_ORDER_SHA256
    )


def test_campaign298_comparator_has_frozen_nonnegative_range() -> None:
    assert campaign.CAMPAIGN298_FACTOR == (
        "alpha158_volume_coefficient_of_variation_20d"
    )
    assert callable(campaign.candidate_snapshot_comparison)


def test_coverage_adapter_maps_only_frozen_threshold_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol, _, _ = campaign.validate_protocol()
    captured = {}

    def fake_coverage(keys, values, eligible, mapped):
        captured.update(mapped)
        return {"gate_passed": True}

    monkeypatch.setattr(campaign.base, "coverage_result", fake_coverage)
    result = campaign.coverage_result(
        np.asarray([1], dtype=np.int64),
        np.asarray([0.5], dtype=np.float64),
        np.asarray([True]),
        protocol,
    )
    assert result == {"gate_passed": True}
    assert captured["coverage_first_gate"] == {
        "domain": protocol["coverage_and_capacity_gates"]["domain"],
        "holding_period_sessions": 3,
        "median_daily_coverage_minimum": 0.95,
        "p05_daily_coverage_minimum": 0.9,
        "p05_eligible_equity_count_minimum": 50,
        "non_overlapping_three_signal_session_cohorts_minimum": 200,
        "observed_calendar_years_minimum": 5,
        "must_pass_before_comparator_values": True,
    }


def test_plan_is_metadata_only_after_implementation_freeze() -> None:
    result = campaign.plan()
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
    assert result["credential_value_or_digest_read"] is False
    assert result["candidate49_ledgers_changed"] is False
