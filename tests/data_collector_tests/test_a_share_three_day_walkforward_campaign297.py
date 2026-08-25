from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign297 as campaign


def _score(
    upper: np.ndarray,
    lower: np.ndarray,
    maximum: np.ndarray,
    minimum: np.ndarray,
    *,
    finite_count: np.ndarray | None = None,
    feature_support: np.ndarray | None = None,
    model_support: np.ndarray | None = None,
):
    rows = len(upper)
    if finite_count is None:
        finite_count = np.full(rows, campaign.FEATURE_COUNT, dtype=np.uint8)
    if feature_support is None:
        feature_support = finite_count >= campaign.MINIMUM_ALPHA158_FINITE_FEATURES
    if model_support is None:
        model_support = feature_support.copy()
    return campaign.interquantile_envelope_occupancy(
        keys=np.arange(1, rows + 1, dtype=np.int64),
        upper=np.asarray(upper, dtype=np.float64),
        lower=np.asarray(lower, dtype=np.float64),
        maximum=np.asarray(maximum, dtype=np.float64),
        minimum=np.asarray(minimum, dtype=np.float64),
        finite_count=finite_count,
        feature_support=feature_support,
        quality_listing=np.ones(rows, dtype=bool),
        model_support=model_support,
    )


def test_central_close_range_is_normalized_by_full_envelope() -> None:
    frame = _score(
        np.asarray([1.2, 1.0, 1.1]),
        np.asarray([0.8, 0.9, 0.7]),
        np.asarray([1.4, 1.2, 1.1]),
        np.asarray([0.6, 0.8, 0.7]),
    )
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert frame[campaign.FACTOR_NAME].tolist() == pytest.approx([0.5, 0.25, 1.0])
    assert frame["finite_required_input_count"].tolist() == [4, 4, 4]


def test_invalid_width_or_nonfinite_input_is_missing_without_repair() -> None:
    frame = _score(
        np.asarray([1.0, 0.7, np.nan, 1.2]),
        np.asarray([0.8, 0.8, 0.7, 0.6]),
        np.asarray([1.0, 1.0, 1.0, 1.0]),
        np.asarray([1.0, 0.5, 0.5, 0.5]),
    )
    assert not frame[f"{campaign.FACTOR_NAME}_eligible"].any()
    assert frame[campaign.FACTOR_NAME].isna().all()
    assert frame["finite_required_input_count"].tolist() == [4, 4, 3, 4]


def test_tolerance_accepts_unclipped_boundary_identity() -> None:
    frame = _score(
        np.asarray([1.0 + 0.5 * campaign.INPUT_TOLERANCE]),
        np.asarray([0.5]),
        np.asarray([1.0]),
        np.asarray([0.5]),
    )
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(
        1.0 + campaign.INPUT_TOLERANCE
    )


def test_model_support_false_keeps_quality_row_but_makes_score_missing() -> None:
    frame = _score(
        np.asarray([1.0, 1.0]),
        np.asarray([0.5, 0.5]),
        np.asarray([1.2, 1.2]),
        np.asarray([0.2, 0.2]),
        model_support=np.asarray([True, False]),
    )
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(0.5)
    assert np.isnan(frame[campaign.FACTOR_NAME].iloc[1])
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True, False]


def test_support_semantics_fail_closed() -> None:
    with pytest.raises(campaign.Campaign297Error):
        _score(
            np.asarray([1.0]),
            np.asarray([0.5]),
            np.asarray([1.2]),
            np.asarray([0.2]),
            finite_count=np.asarray([campaign.FEATURE_COUNT], dtype=np.uint8),
            feature_support=np.asarray([False]),
            model_support=np.asarray([False]),
        )


def test_protocol_and_candidate49_bindings_are_frozen() -> None:
    protocol, alpha, numeric = campaign.validate_protocol()
    assert protocol["ordered_numeric_uniqueness"]["comparator_count"] == 149
    assert protocol["factor_library"][0]["name"] == campaign.FACTOR_NAME
    assert protocol["factor_library"][0]["parameters"]["score"] == (
        "(QTLU20 - QTLD20) / (MAX20 - MIN20)"
    )
    assert len(alpha["feature_names"]) == 158
    assert {
        campaign.UPPER_FEATURE,
        campaign.LOWER_FEATURE,
        campaign.MAX_FEATURE,
        campaign.MIN_FEATURE,
    }.issubset(alpha["feature_names"])
    assert len(numeric["feature_names"]) == 140
    assert campaign.file_sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign.file_sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_frozen_comparator_order_contains_all_149_definitions() -> None:
    _, _, numeric = campaign.validate_protocol()
    definitions = campaign.comparison_definitions(numeric)
    assert len(definitions) == campaign.EXPECTED_COMPARATOR_COUNT
    assert definitions[-1] == campaign.CAMPAIGN296_FACTOR
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


def test_campaign296_comparator_is_explicitly_unbounded() -> None:
    assert campaign.CAMPAIGN296_FACTOR == "alpha158_linear_trend_quality_10d"
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
