from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign051_features as campaign


def _uniform_ten_bin_closes() -> np.ndarray:
    locations: list[float] = [0.0] + [0.05] * 23
    for index in range(1, 9):
        locations.extend([index / 10.0 + 0.05] * 24)
    locations.extend([0.95] * 23 + [1.0])
    return np.exp(np.asarray(locations, dtype=float))[None, :]


def _two_bin_closes() -> np.ndarray:
    return np.exp(np.asarray([0.0] * 120 + [1.0] * 120, dtype=float))[None, :]


def _raw_day(closes: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    date = pd.Timestamp("2021-01-04")
    minute_codes = [570] + list(campaign.market.CONTINUOUS_MINUTE_CODES)
    datetimes = [
        date + pd.Timedelta(minutes=int(code)) for code in minute_codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SZ000001",
            "provider": "tushare",
            "close": np.concatenate([[0.01], closes[0]]),
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SZ000001"]})
    return raw, base


def test_campaign051_protocol_is_finite_and_binding_valid() -> None:
    spec = campaign.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert spec["kind"] == "a_share_three_day_walkforward_campaign051_no_return_preregistration"
    assert gate["comparison_factors"][-1] == {
        "name": campaign.C50_FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(gate["comparison_factors"]) == 74
    assert campaign._comparison_order_digest(gate["comparison_factors"]) == campaign.COMPARISON_ORDER_SHA256
    assert spec["finite_post_admissibility_search"]["development_trial_count"] == 1


def test_campaign051_uniform_occupancy_scores_one() -> None:
    values, eligible, quality = campaign.compute_factor_values(
        closes=_uniform_ten_bin_closes()
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{campaign.FACTOR_NAME}__empty_bin_positions"] == 0


def test_campaign051_two_equal_bins_score_log_two_over_log_ten() -> None:
    values, eligible, _ = campaign.compute_factor_values(closes=_two_bin_closes())
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(
        np.log(2.0) / np.log(10.0)
    )


def test_campaign051_exact_repeated_closes_are_retained() -> None:
    values, eligible, quality = campaign.compute_factor_values(
        closes=_two_bin_closes()
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__exact_repeated_close_positions"] == 238


def test_campaign051_flat_day_is_missing() -> None:
    values, eligible, quality = campaign.compute_factor_values(
        closes=np.ones((1, campaign.SELECTED_BAR_COUNT), dtype=float)
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[f"{campaign.FACTOR_NAME}__zero_log_close_range_rows"] == 1


def test_campaign051_rejects_nonpositive_and_nonfinite_closes() -> None:
    closes = np.vstack([_uniform_ten_bin_closes()[0]] * 2)
    closes[0, 7] = 0.0
    closes[1, 8] = np.nan
    values, eligible, quality = campaign.compute_factor_values(closes=closes)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__nonpositive_close_rows"] == 1
    assert quality[f"{campaign.FACTOR_NAME}__nonfinite_close_rows"] == 1


def test_campaign051_is_order_invariant() -> None:
    closes = _uniform_ten_bin_closes()
    permuted = closes[:, np.random.default_rng(51).permutation(closes.shape[1])]
    first, first_eligible, _ = campaign.compute_factor_values(closes=closes)
    second, second_eligible, _ = campaign.compute_factor_values(closes=permuted)
    assert first_eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert second_eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert first[campaign.FACTOR_NAME][0] == pytest.approx(
        second[campaign.FACTOR_NAME][0]
    )


def test_campaign051_partition_uses_exact_241_row_source_grid() -> None:
    raw, base = _raw_day(_uniform_ten_bin_closes())
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert bool(frame[f"{campaign.FACTOR_NAME}_eligible"].iloc[0]) is True
    assert quality["base_rows"] == 1


def test_campaign051_partition_rejects_wrong_source_projection() -> None:
    raw, base = _raw_day(_uniform_ten_bin_closes())
    with pytest.raises(campaign.Campaign051FeatureError, match="raw columns"):
        campaign.compute_partition_frame(
            raw.assign(open=1.0), base, None, symbol="SZ000001"
        )


def test_campaign051_empty_base_does_not_require_raw_identity() -> None:
    raw = pd.DataFrame(columns=campaign.RAW_COLUMNS)
    base = pd.DataFrame(columns=campaign.BASE_COLUMNS)
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame.empty
    assert quality == {"base_rows": 0}


def test_campaign051_v1_cannot_build_before_additive_freeze_binding() -> None:
    assert campaign.IMPLEMENTATION_FREEZE_SHA256 == ""
    with pytest.raises(campaign.Campaign051FeatureError, match="implementation freeze"):
        campaign._load_implementation_freeze()


def test_campaign051_prevalue_records_disclose_no_value_or_return_read() -> None:
    for path in (
        Path("docs/a_share_three_day_walkforward_campaign_051_concept_scouting.json"),
        Path("docs/a_share_three_day_walkforward_campaign_051_mechanism_overlap_audit.json"),
        Path("docs/a_share_three_day_walkforward_campaign_051_no_return_preregistration.json"),
        Path("docs/a_share_three_day_walkforward_campaign_051_preregistration_semantic_failure_20260801.json"),
        Path("docs/a_share_three_day_walkforward_campaign_051_no_return_preregistration_v2.json"),
    ):
        record = json.loads(path.read_text(encoding="utf-8"))
        boundary = record["research_boundary"]
        assert boundary.get("provider_request_issued") is False
        assert boundary.get("candidate49_ledgers_changed") is False
        assert boundary.get("second_prospective_candidate_created") is False
        assert not any(
            value is True
            for key, value in boundary.items()
            if "value" in key or "price" in key or "return" in key
        )
