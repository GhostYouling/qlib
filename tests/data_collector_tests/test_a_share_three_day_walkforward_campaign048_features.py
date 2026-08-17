from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign048_features as campaign


def _balanced(rows: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    opens = np.full((rows, 240), 2.0)
    highs = np.full((rows, 240), 4.0)
    lows = np.full((rows, 240), 1.0)
    closes = np.full((rows, 240), 2.0)
    return opens, highs, lows, closes


def test_campaign048_protocol_is_finite_and_binding_valid() -> None:
    spec = campaign.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert spec["kind"] == "a_share_three_day_walkforward_campaign048_no_return_preregistration"
    assert [item["name"] for item in gate["comparison_factors"]][-1] == campaign.C47_FACTOR_NAME
    assert len(gate["comparison_factors"]) == 71
    assert spec["finite_post_admissibility_search"]["development_trial_count"] == 1


def test_campaign048_balanced_wicks_score_one() -> None:
    opens, highs, lows, closes = _balanced()
    values, eligible, quality = campaign.compute_factor_values(
        opens=opens, highs=highs, lows=lows, closes=closes
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 1


def test_campaign048_one_sided_wicks_score_zero() -> None:
    opens, highs, lows, closes = _balanced()
    highs[:] = 2.0
    values, eligible, _ = campaign.compute_factor_values(
        opens=opens, highs=highs, lows=lows, closes=closes
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(0.0)


def test_campaign048_requires_frozen_positive_range_support() -> None:
    opens = np.ones((1, 240))
    highs = np.ones((1, 240))
    lows = np.ones((1, 240))
    closes = np.ones((1, 240))
    highs[:, :119] = 2.0
    values, eligible, quality = campaign.compute_factor_values(
        opens=opens, highs=highs, lows=lows, closes=closes
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[f"{campaign.FACTOR_NAME}__below_minimum_positive_range_rows"] == 1


def test_campaign048_rejects_invalid_own_bar_ordering() -> None:
    opens, highs, lows, closes = _balanced()
    highs[0, 7] = 1.5
    values, eligible, quality = campaign.compute_factor_values(
        opens=opens, highs=highs, lows=lows, closes=closes
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[f"{campaign.FACTOR_NAME}__invalid_ohlc_order_rows"] == 1


def test_campaign048_partition_uses_exact_241_row_source_grid() -> None:
    date = pd.Timestamp("2021-01-04")
    codes = [570] + list(campaign.market.CONTINUOUS_MINUTE_CODES)
    datetimes = [date + pd.Timedelta(minutes=int(code // 60 * 60 + code % 60)) for code in codes]
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SZ000001",
            "provider": "tushare",
            "open": 2.0,
            "high": 4.0,
            "low": 1.0,
            "close": 2.0,
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SZ000001"]})
    frame, quality = campaign.compute_partition_frame(raw, base, None, symbol="SZ000001")
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert bool(frame[f"{campaign.FACTOR_NAME}_eligible"].iloc[0]) is True
    assert quality["base_rows"] == 1


def test_campaign048_v1_cannot_build_before_additive_freeze_binding() -> None:
    assert campaign.IMPLEMENTATION_FREEZE_SHA256 == ""
    with pytest.raises(campaign.Campaign048FeatureError, match="implementation freeze"):
        campaign._load_implementation_freeze()


def test_campaign048_prevalue_records_disclose_no_value_or_return_read() -> None:
    for path in (
        Path("docs/a_share_three_day_walkforward_campaign_048_concept_scouting.json"),
        Path("docs/a_share_three_day_walkforward_campaign_048_mechanism_overlap_audit.json"),
        Path("docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"),
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
