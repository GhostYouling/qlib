from __future__ import annotations

import numpy as np
import pandas as pd

import scripts.a_share_three_day_walkforward_campaign052_features_v2 as frozen


c52 = frozen.runner


def test_campaign052_protocol_and_implementation_are_bound() -> None:
    spec = c52.load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 75
    assert comparisons[-1] == {
        "name": "intraday_close_range_occupancy_entropy_10b",
        "score_direction": "higher",
    }
    assert c52._load_implementation_freeze()["status"] == (
        "frozen_before_campaign052_candidate_values"
    )


def test_campaign052_formula_rewards_equal_reporting_delay() -> None:
    values, eligible, quality = c52.compute_factor_values(
        delays=np.array([[30.0, 30.0, 30.0, 30.0], [20.0, 30.0, 40.0, 50.0]]),
        consecutive_quarters=np.array([True, True]),
    )
    observed = values[c52.FACTOR_NAME]
    assert observed[0] == 1.0
    assert 0.0 < observed[1] < observed[0]
    assert eligible[c52.FACTOR_NAME].tolist() == [True, True]
    assert quality[f"{c52.FACTOR_NAME}__zero_dispersion_rows"] == 1


def test_campaign052_formula_rejects_nonconsecutive_or_negative_delay() -> None:
    values, eligible, quality = c52.compute_factor_values(
        delays=np.array([[20.0, 30.0, 40.0, 50.0], [20.0, -1.0, 40.0, 50.0]]),
        consecutive_quarters=np.array([False, True]),
    )
    assert np.isnan(values[c52.FACTOR_NAME]).all()
    assert not eligible[c52.FACTOR_NAME].any()
    assert quality[f"{c52.FACTOR_NAME}__nonconsecutive_quarter_rows"] == 1
    assert quality[f"{c52.FACTOR_NAME}__negative_delay_rows"] == 1


def test_campaign052_partition_reads_identity_and_disclosure_dates_only(
    monkeypatch,
) -> None:
    trade_date = pd.Timestamp("2021-05-06")
    calendar_values = pd.DatetimeIndex(
        ["2021-05-05", "2021-05-06"]
    ).to_numpy(dtype="datetime64[ns]")
    event = {
        "quarter_ordinal": np.array([200, 201, 202, 203], dtype=np.int64),
        "effective_position": np.array([0, 0, 0, 0], dtype=np.int64),
        "delay_days": np.array([30.0, 30.0, 30.0, 30.0]),
        "is_exact_quarter_end": np.array([True, True, True, True]),
    }
    monkeypatch.setattr(
        c52,
        "_load_disclosure_events",
        lambda: (calendar_values, {"SH600000": event}),
    )
    minute_codes = sorted(c52.market.SOURCE_MINUTE_CODE_SET)
    raw = pd.DataFrame(
        {
            "datetime": [
                trade_date
                + pd.Timedelta(hours=code // 60, minutes=code % 60)
                for code in minute_codes
            ],
            "symbol": "SH600000",
            "provider": "tushare",
        }
    )
    base = pd.DataFrame({"trade_date": [trade_date], "symbol": ["SH600000"]})
    frame, quality = c52.compute_partition_frame(
        raw, base, None, symbol="SH600000"
    )
    assert tuple(raw.columns) == c52.RAW_COLUMNS
    assert tuple(frame.columns) == c52.OUTPUT_COLUMNS
    assert frame.loc[0, c52.FACTOR_NAME] == 1.0
    assert bool(frame.loc[0, f"{c52.FACTOR_NAME}_eligible"])
    assert quality[f"{c52.FACTOR_NAME}__eligible_rows"] == 1


def test_campaign052_status_prohibits_prices_returns_and_second_candidate() -> None:
    payload = c52.status(c52.DEFAULT_DATA_ROOT, c52.DEFAULT_EXPERIMENT_ROOT)
    assert payload["quarterly_value_fields_read_by_status"] == []
    assert payload["minute_price_volume_amount_fields_read_by_status"] == []
    assert payload["daily_price_fields_read_by_status"] is False
    assert payload["forward_return_fields_read_by_status"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["second_prospective_candidate_created"] is False
