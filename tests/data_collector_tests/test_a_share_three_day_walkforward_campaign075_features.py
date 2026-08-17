from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign075_features as candidate


def _calendar(periods: int = 25) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-02", periods=periods)


def _identity(calendar: pd.DatetimeIndex, symbol: str = "SZ000001") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": calendar,
            "symbol": symbol,
            "provider": "tushare",
        }
    )


def test_session_youth_uses_inclusive_accepted_session_clock() -> None:
    calendar = _calendar()
    result = candidate.compute_session_youth(
        _identity(calendar),
        accepted_start=calendar[0],
        accepted_end=calendar[-1],
        calendar=calendar,
        symbol="SZ000001",
    )
    factor = candidate.FACTOR_NAME
    assert result.loc[:18, factor].isna().all()
    assert not result.loc[:18, f"{factor}_eligible"].any()
    assert result.loc[19, factor] == -20.0
    assert result.loc[24, factor] == -25.0
    assert result.loc[19:, f"{factor}_eligible"].all()
    assert candidate.validate_value_semantics(result) == (25, 6)


def test_nonaccepted_calendar_days_do_not_change_age() -> None:
    calendar = _calendar()
    result = candidate.compute_session_youth(
        _identity(calendar[[19, 20]]),
        accepted_start=calendar[0],
        accepted_end=calendar[-1],
        calendar=calendar,
        symbol="SZ000001",
    )
    assert result[candidate.FACTOR_NAME].tolist() == [-20.0, -21.0]


def test_identity_outside_instrument_interval_fails_closed() -> None:
    calendar = _calendar()
    with pytest.raises(candidate.Campaign075FeatureError):
        candidate.compute_session_youth(
            _identity(calendar),
            accepted_start=calendar[1],
            accepted_end=calendar[-1],
            calendar=calendar,
            symbol="SZ000001",
        )


def test_duplicate_identity_fails_closed() -> None:
    calendar = _calendar()
    identity = pd.concat([_identity(calendar), _identity(calendar[[0]])])
    with pytest.raises(candidate.Campaign075FeatureError):
        candidate.compute_session_youth(
            identity,
            accepted_start=calendar[0],
            accepted_end=calendar[-1],
            calendar=calendar,
            symbol="SZ000001",
        )


def test_value_semantics_reject_noninteger_or_too_young_values() -> None:
    factor = candidate.FACTOR_NAME
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02"]),
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            factor: [-19.5],
            f"{factor}_eligible": [True],
        }
    ).loc[:, candidate.OUTPUT_COLUMNS]
    with pytest.raises(candidate.Campaign075FeatureError):
        candidate.validate_value_semantics(frame)


def test_protocol_and_definition_orders_are_bound_without_source_values() -> None:
    spec = candidate.load_protocol()
    assert spec["candidate"]["name"] == candidate.FACTOR_NAME
    assert len(candidate.reconstruct_comparisons()) == 105
    assert len(candidate.reconstruct_complete_definitions()) == 106
    assert candidate.reconstruct_comparisons()[-1] == {
        "name": candidate.C74_FACTOR,
        "score_direction": "higher",
    }


def test_status_is_read_only_before_snapshot() -> None:
    payload = candidate.status(candidate.DEFAULT_DATA_ROOT)
    assert payload["source_rows_or_candidate_values_read_by_status"] is False
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
