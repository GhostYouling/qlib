from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign295 as campaign


def _score(
    sumd: np.ndarray,
    cord: np.ndarray,
    *,
    finite_count: np.ndarray | None = None,
    feature_support: np.ndarray | None = None,
    model_support: np.ndarray | None = None,
):
    rows = len(sumd)
    if finite_count is None:
        finite_count = np.full(rows, campaign.FEATURE_COUNT, dtype=np.uint8)
    if feature_support is None:
        feature_support = finite_count >= campaign.MINIMUM_ALPHA158_FINITE_FEATURES
    if model_support is None:
        model_support = feature_support.copy()
    return campaign.price_volume_directional_confirmation(
        keys=np.arange(1, rows + 1, dtype=np.int64),
        sumd=np.asarray(sumd, dtype=np.float64),
        cord=np.asarray(cord, dtype=np.float64),
        finite_count=finite_count,
        feature_support=feature_support,
        quality_listing=np.ones(rows, dtype=bool),
        model_support=model_support,
    )


def test_price_direction_is_preserved_and_confirmation_is_bounded() -> None:
    frame = _score(
        np.asarray([1.0, -1.0, 0.5, -0.5]),
        np.asarray([1.0, 1.0, -1.0, 0.0]),
    )
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert frame[campaign.FACTOR_NAME].tolist() == pytest.approx(
        [1.0, -1.0, 0.0, -0.25]
    )
    assert frame["finite_required_input_count"].tolist() == [2, 2, 2, 2]


def test_nonfinite_or_out_of_interval_inputs_are_missing_without_clipping() -> None:
    frame = _score(
        np.asarray([np.nan, 1.0 + 2 * campaign.INPUT_TOLERANCE, 0.5]),
        np.asarray([0.0, 0.0, -1.0 - 2 * campaign.INPUT_TOLERANCE]),
    )
    assert not frame[f"{campaign.FACTOR_NAME}_eligible"].any()
    assert frame[campaign.FACTOR_NAME].isna().all()
    assert frame["finite_required_input_count"].tolist() == [1, 2, 2]


def test_model_support_false_keeps_quality_row_but_makes_score_missing() -> None:
    frame = _score(
        np.asarray([0.5, 0.5]),
        np.asarray([0.5, 0.5]),
        model_support=np.asarray([True, False]),
    )
    assert frame[campaign.FACTOR_NAME].tolist()[0] == pytest.approx(0.375)
    assert np.isnan(frame[campaign.FACTOR_NAME].tolist()[1])
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True, False]


def test_support_semantics_fail_closed() -> None:
    with pytest.raises(campaign.Campaign295Error):
        _score(
            np.asarray([0.5]),
            np.asarray([0.5]),
            finite_count=np.asarray([campaign.FEATURE_COUNT], dtype=np.uint8),
            feature_support=np.asarray([False]),
            model_support=np.asarray([False]),
        )


def test_protocol_and_candidate49_bindings_are_frozen() -> None:
    protocol, alpha, numeric = campaign.validate_protocol()
    assert protocol["ordered_numeric_uniqueness"]["comparator_count"] == 147
    assert protocol["factor_library"][0]["name"] == campaign.FACTOR_NAME
    assert protocol["factor_library"][0]["parameters"]["score"] == (
        "SUMD20 * (1 + CORD20) / 2"
    )
    assert len(alpha["feature_names"]) == 158
    assert {campaign.PRICE_DIRECTION_FEATURE, campaign.CONFIRMATION_FEATURE}.issubset(
        alpha["feature_names"]
    )
    assert len(numeric["feature_names"]) == 140
    assert campaign.file_sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign.file_sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_prior_numeric_comparison_helper_is_reachable_through_campaign292() -> None:
    assert hasattr(
        campaign.prior.prior.prior,
        "prior_campaign_comparison",
    )


def test_plan_is_metadata_only_after_implementation_freeze() -> None:
    result = campaign.plan()
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
    assert result["credential_loaded"] is False
    assert result["candidate49_ledgers_changed"] is False
