from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign049_features as campaign


def _active_amounts(rows: int = 1) -> np.ndarray:
    profile = np.arange(1.0, 121.0)
    return np.tile(np.concatenate([profile, profile]), (rows, 1))


def test_campaign049_protocol_is_finite_and_binding_valid() -> None:
    spec = campaign.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert (
        spec["kind"]
        == "a_share_three_day_walkforward_campaign049_no_return_preregistration"
    )
    assert gate["comparison_factors"][-1] == {
        "name": campaign.C48_FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(gate["comparison_factors"]) == 72
    assert campaign._comparison_order_digest(gate["comparison_factors"]) == (
        campaign.COMPARISON_ORDER_SHA256
    )
    assert spec["finite_post_admissibility_search"]["development_trial_count"] == 1


def test_campaign049_identical_half_profiles_score_one() -> None:
    values, eligible, quality = campaign.compute_factor_values(
        amounts=_active_amounts()
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 1


def test_campaign049_half_scale_does_not_change_profile_similarity() -> None:
    amounts = _active_amounts()
    amounts[:, 120:] *= 17.0
    values, eligible, _ = campaign.compute_factor_values(amounts=amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)


def test_campaign049_disjoint_supported_profiles_score_zero() -> None:
    amounts = np.zeros((1, 240))
    amounts[:, :60] = 1.0
    amounts[:, 180:] = 1.0
    values, eligible, _ = campaign.compute_factor_values(amounts=amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(0.0)


def test_campaign049_requires_sixty_positive_bars_in_each_half() -> None:
    amounts = np.ones((1, 240))
    amounts[:, 59:120] = 0.0
    values, eligible, quality = campaign.compute_factor_values(amounts=amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert (
        quality[
            f"{campaign.FACTOR_NAME}__below_minimum_positive_morning_bars_rows"
        ]
        == 1
    )


def test_campaign049_rejects_negative_amount() -> None:
    amounts = _active_amounts()
    amounts[0, 7] = -1.0
    values, eligible, quality = campaign.compute_factor_values(amounts=amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[f"{campaign.FACTOR_NAME}__negative_amount_rows"] == 1


def test_campaign049_partition_uses_exact_241_row_source_grid() -> None:
    date = pd.Timestamp("2021-01-04")
    codes = [570] + list(campaign.market.CONTINUOUS_MINUTE_CODES)
    datetimes = [
        date + pd.Timedelta(minutes=int(code // 60 * 60 + code % 60))
        for code in codes
    ]
    amount = np.concatenate([[1.0], _active_amounts()[0]])
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SZ000001",
            "provider": "tushare",
            "amount": amount,
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SZ000001"]})
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert bool(frame[f"{campaign.FACTOR_NAME}_eligible"].iloc[0]) is True
    assert quality["base_rows"] == 1


def test_campaign049_v1_cannot_build_before_additive_freeze_binding() -> None:
    assert campaign.IMPLEMENTATION_FREEZE_SHA256 == ""
    with pytest.raises(campaign.Campaign049FeatureError, match="implementation freeze"):
        campaign._load_implementation_freeze()


def test_campaign049_prevalue_records_disclose_no_value_or_return_read() -> None:
    for path in (
        Path("docs/a_share_three_day_walkforward_campaign_049_concept_scouting.json"),
        Path("docs/a_share_three_day_walkforward_campaign_049_mechanism_overlap_audit.json"),
        Path("docs/a_share_three_day_walkforward_campaign_049_no_return_preregistration.json"),
    ):
        record = json.loads(path.read_text(encoding="utf-8"))
        boundary = record["research_boundary"]
        assert boundary.get("provider_request_issued") is False
        assert boundary.get("candidate49_ledgers_changed") is False
        assert not any(
            value is True
            for key, value in boundary.items()
            if "value" in key or "price" in key or "return" in key
        )
