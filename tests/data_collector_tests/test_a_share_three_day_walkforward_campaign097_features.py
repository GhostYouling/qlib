from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign097_features as campaign


def _raw_profile(values: np.ndarray, *, symbol: str = "000001.SZ") -> pd.DataFrame:
    date = pd.Timestamp("2025-01-02")
    minute_codes = list(campaign.base.SOURCE_MINUTE_CODE_SET)
    minute_codes.sort()
    continuous = list(campaign.base.CONTINUOUS_MINUTE_CODES)
    lookup = {code: float(values[index]) for index, code in enumerate(continuous)}
    rows = []
    for code in minute_codes:
        q = lookup.get(code, 0.0)
        rows.append(
            {
                "datetime": date + pd.Timedelta(hours=code // 60, minutes=code % 60),
                "symbol": symbol,
                "provider": "tushare",
                "high": float(np.exp(q)),
                "low": 1.0,
            }
        )
    return pd.DataFrame(rows).loc[:, campaign.RAW_COLUMNS]


def _base(symbol: str = "000001.SZ") -> pd.DataFrame:
    return pd.DataFrame(
        {"trade_date": [pd.Timestamp("2025-01-02")], "symbol": [symbol]}
    )


def test_protocol_and_v41_orders_are_frozen() -> None:
    spec = campaign.load_protocol()
    assert spec["protocol_revision"] == 2
    complete = campaign.reconstruct_complete_definitions()
    comparisons = campaign.reconstruct_comparisons()
    assert len(complete) == 128
    assert len(comparisons) == 125
    assert complete[-1] == {
        "name": "intraday_intrabar_close_location_total_variation_238p",
        "score_direction": "higher",
    }
    assert comparisons[-1] == complete[-1]


def test_zero_ranges_remain_fixed_support_and_one_positive_range_is_enough() -> None:
    q = np.zeros(240, dtype=float)
    q[17] = 0.02
    base, profiles, valid, quality = campaign.extract_partition_profiles(
        _raw_profile(q), _base(), symbol="000001.SZ"
    )
    assert len(base) == 1
    assert valid.tolist() == [True]
    assert profiles.shape == (1, 240)
    assert profiles[0, 17] == pytest.approx(1.0)
    assert np.count_nonzero(profiles[0]) == 1
    assert quality["invalid_required_amount_rows"] == 0
    assert quality["nonpositive_total_amount_rows"] == 0


def test_all_zero_ranges_are_missing_without_epsilon() -> None:
    _, profiles, valid, quality = campaign.extract_partition_profiles(
        _raw_profile(np.zeros(240)), _base(), symbol="000001.SZ"
    )
    assert valid.tolist() == [False]
    assert np.isnan(profiles).all()
    assert quality["nonpositive_total_amount_rows"] == 1


def test_invalid_ordered_range_fails_closed() -> None:
    raw = _raw_profile(np.linspace(0.0, 0.02, 240))
    raw.loc[10, "high"] = 0.5
    raw.loc[10, "low"] = 1.0
    _, profiles, valid, quality = campaign.extract_partition_profiles(
        raw, _base(), symbol="000001.SZ"
    )
    assert valid.tolist() == [False]
    assert np.isnan(profiles).all()
    assert quality["invalid_required_amount_rows"] == 1


def test_aligned_leave_one_out_profile_has_unit_correlation() -> None:
    own = np.arange(1.0, 241.0)
    own /= own.sum()
    profiles = own[None, :]
    peer = own.copy()
    sums = profiles + 50.0 * peer[None, :]
    counts = np.full((1, 240), 51, dtype=np.int64)
    values, eligible, quality = campaign.compute_profile_correlations(
        profiles, np.array([True]), sums, counts
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(1.0)
    assert quality["insufficient_leave_one_out_peer_rows"] == 0


def test_peer_minimum_and_constant_peer_profile_fail_closed() -> None:
    own = np.arange(1.0, 241.0)
    own /= own.sum()
    profiles = own[None, :]
    peer = own[::-1].copy()
    insufficient_sums = profiles + 49.0 * peer[None, :]
    insufficient_counts = np.full((1, 240), 50, dtype=np.int64)
    values, eligible, quality = campaign.compute_profile_correlations(
        profiles, np.array([True]), insufficient_sums, insufficient_counts
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])
    assert quality["insufficient_leave_one_out_peer_rows"] == 1

    constant = np.full(240, 1.0 / 240.0)
    sums = profiles + 50.0 * constant[None, :]
    counts = np.full((1, 240), 51, dtype=np.int64)
    values, eligible, quality = campaign.compute_profile_correlations(
        profiles, np.array([True]), sums, counts
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])
    assert quality["constant_market_profile_rows"] == 1


def test_feature_build_declares_no_prices_returns_or_candidate49_mutation() -> None:
    status = campaign.status(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
    assert status["comparison_values_read_by_feature_build"] is False
    assert status["daily_price_or_forward_return_read_by_feature_build"] is False
    protocol = json.loads(campaign.DEFAULT_PROTOCOL.read_text())
    boundary = protocol["research_boundary"]
    assert boundary["candidate49_ledgers_may_change"] is False
    assert boundary["provider_request_issued"] is False
