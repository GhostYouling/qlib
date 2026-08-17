from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign151_features as c151
from scripts import a_share_three_day_walkforward_campaign151_formula as formula


def _minute_index(date: str) -> pd.DatetimeIndex:
    day = pd.Timestamp(date)
    return pd.DatetimeIndex(
        [day + pd.Timedelta(hours=9, minutes=30)]
        + list(
            pd.date_range(
                day + pd.Timedelta(hours=9, minutes=31), periods=120, freq="min"
            )
        )
        + list(
            pd.date_range(
                day + pd.Timedelta(hours=13, minutes=1), periods=120, freq="min"
            )
        )
    )


def _raw_day(
    date: str,
    amounts: np.ndarray,
    *,
    symbol: str = "SH600000",
) -> pd.DataFrame:
    assert amounts.shape == (240,)
    return pd.DataFrame(
        {
            "datetime": _minute_index(date),
            "symbol": symbol,
            "provider": "tushare",
            "amount": np.r_[0.0, amounts],
        }
    ).loc[:, c151.RAW_COLUMNS]


def _base(dates: list[str], *, symbol: str = "SH600000") -> pd.DataFrame:
    return pd.DataFrame({"trade_date": pd.to_datetime(dates), "symbol": symbol}).loc[
        :, c151.JOINT_COLUMNS
    ]


def test_campaign151_builder_protocol_is_metadata_only_and_frozen() -> None:
    spec = c151.load_builder_protocol()
    assert spec["source_contract"]["raw_projection"] == list(c151.RAW_COLUMNS)
    assert spec["exact_profile_extraction"]["selected_amount_positions"] == 240
    assert (
        spec["first_pass_peer_accumulator"][
            "no_candidate_comparator_price_or_return_value"
        ]
        is True
    )
    assert c151.output_root() == (
        c151.DEFAULT_DATA_ROOT
        / "derived/a_share/rich/tushare/minute_walkforward_campaign151_feature_library"
        / c151.OUTPUT_RUN_ID
    )


def test_campaign151_extracts_exact_raw_amount_profiles_and_retains_all_zero() -> None:
    first = np.arange(1.0, 241.0)
    second = np.zeros(240, dtype=np.float64)
    raw = pd.concat(
        [_raw_day("2021-01-04", first), _raw_day("2021-01-05", second)],
        ignore_index=True,
    )
    base, amounts, complete, quality = c151.extract_partition_amount_profiles(
        raw,
        _base(["2021-01-04", "2021-01-05"]),
        symbol="SH600000",
    )
    assert len(base) == 2
    assert amounts.shape == (2, 240)
    assert complete.tolist() == [True, True]
    assert np.array_equal(amounts[0], first)
    assert np.array_equal(amounts[1], second)
    assert quality == {
        "base_rows": 2,
        "invalid_required_amount_rows": 0,
        "complete_profile_rows": 2,
    }


def test_campaign151_empty_joint_partition_is_an_empty_contribution() -> None:
    raw = _raw_day("2019-01-02", np.ones(240, dtype=np.float64))
    base = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
        }
    ).loc[:, c151.JOINT_COLUMNS]
    observed_base, amounts, complete, quality = c151.extract_partition_amount_profiles(
        raw,
        base,
        symbol="SH600145",
    )
    assert observed_base.empty
    assert amounts.shape == (0, 240)
    assert complete.shape == (0,)
    assert quality == {
        "base_rows": 0,
        "invalid_required_amount_rows": 0,
        "complete_profile_rows": 0,
    }


def test_campaign151_extraction_rejects_grid_identity_and_invalid_amounts() -> None:
    amounts = np.ones(240, dtype=np.float64)
    raw = _raw_day("2021-01-04", amounts)
    invalid = raw.copy()
    invalid.loc[10, "amount"] = -1.0
    _base_frame, values, complete, quality = c151.extract_partition_amount_profiles(
        invalid, _base(["2021-01-04"]), symbol="SH600000"
    )
    assert complete.tolist() == [False]
    assert np.isnan(values).all()
    assert quality["invalid_required_amount_rows"] == 1

    with pytest.raises(c151.Campaign151FeatureError):
        c151.extract_partition_amount_profiles(
            raw.iloc[:-1].copy(),
            _base(["2021-01-04"]),
            symbol="SH600000",
        )
    with pytest.raises(c151.Campaign151FeatureError):
        c151.extract_partition_amount_profiles(
            raw.assign(close=1.0),
            _base(["2021-01-04"]),
            symbol="SH600000",
        )


def test_campaign151_accumulator_adds_only_complete_profiles() -> None:
    sums = np.zeros((2, 240), dtype=np.float64)
    counts = np.zeros(2, dtype=np.int32)
    amounts = np.vstack(
        [
            np.ones(240, dtype=np.float64),
            np.full(240, 2.0, dtype=np.float64),
            np.full(240, np.nan, dtype=np.float64),
        ]
    )
    c151.accumulate_complete_profiles(
        sums,
        counts,
        np.array([0, 1, 0], dtype=np.int64),
        amounts,
        np.array([True, True, False]),
    )
    assert np.array_equal(counts, [1, 1])
    assert np.array_equal(sums[0], np.ones(240))
    assert np.array_equal(sums[1], np.full(240, 2.0))


def test_campaign151_partition_uses_exact_leave_one_out_peer_mean() -> None:
    date = pd.Timestamp("2021-01-04")
    own = np.arange(1.0, 241.0)
    peer = np.ones(240, dtype=np.float64)
    benchmark = c151.PeerBenchmark(
        dates=pd.DatetimeIndex([date]),
        amount_sums=(own + 51.0 * peer)[None, :],
        valid_counts=np.array([52], dtype=np.int32),
        date_to_index={date: 0},
        frame_sha256="a" * 64,
    )
    output, quality = c151.compute_partition_frame(
        _raw_day("2021-01-04", own),
        _base(["2021-01-04"]),
        benchmark,
        symbol="SH600000",
    )
    expected = formula.compute_relative_amount_share_clock_center(
        own[None, :], peer[None, :]
    )[0][0]
    assert output[f"{c151.FACTOR_NAME}_eligible"].tolist() == [True]
    assert output[c151.FACTOR_NAME].tolist() == pytest.approx([expected], abs=1e-15)
    assert quality["eligible_rows"] == 1
    assert quality["insufficient_leave_one_out_peer_rows"] == 0


def test_campaign151_partition_fails_closed_on_support_boundaries() -> None:
    dates = pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-06"])
    own = np.ones(240, dtype=np.float64)
    raw = pd.concat(
        [
            _raw_day("2021-01-04", np.zeros(240)),
            _raw_day("2021-01-05", own),
            _raw_day("2021-01-06", own),
        ],
        ignore_index=True,
    )
    sums = np.vstack(
        [
            51.0 * own,
            49.0 * own + own,
            51.0 * own + own,
        ]
    )
    sums[2, 10] = own[10]
    benchmark = c151.PeerBenchmark(
        dates=pd.DatetimeIndex(dates),
        amount_sums=sums,
        valid_counts=np.array([52, 50, 52], dtype=np.int32),
        date_to_index={pd.Timestamp(value): index for index, value in enumerate(dates)},
        frame_sha256="b" * 64,
    )
    output, quality = c151.compute_partition_frame(
        raw,
        _base(["2021-01-04", "2021-01-05", "2021-01-06"]),
        benchmark,
        symbol="SH600000",
    )
    assert output[f"{c151.FACTOR_NAME}_eligible"].tolist() == [False, False, False]
    assert output[c151.FACTOR_NAME].isna().all()
    assert quality["nonpositive_relative_total_rows"] == 1
    assert quality["insufficient_leave_one_out_peer_rows"] == 1
    assert quality["nonpositive_peer_clock_rows"] == 1


def test_campaign151_accumulator_checkpoint_round_trip_and_tamper_fail_closed(
    tmp_path,
) -> None:
    dates = pd.DatetimeIndex(pd.to_datetime(["2021-01-04", "2021-01-05"]))
    sums = np.arange(480, dtype=np.float64).reshape(2, 240)
    counts = np.array([51, 52], dtype=np.int32)
    path = tmp_path / "accumulator.npz"
    c151._atomic_write_accumulator(
        path,
        dates=dates,
        amount_sums=sums,
        valid_counts=counts,
        processed_symbols={"SH600000"},
    )
    observed_sums, observed_counts, processed = c151._load_or_create_accumulator(
        path, dates
    )
    assert np.array_equal(observed_sums, sums)
    assert np.array_equal(observed_counts, counts)
    assert processed == {"SH600000"}

    with path.open("wb") as handle:
        handle.write(b"not-an-npz")
    with pytest.raises(c151.Campaign151FeatureError):
        c151._load_or_create_accumulator(path, dates)


def test_campaign151_build_requires_explicit_confirmation_before_any_read() -> None:
    with pytest.raises(c151.Campaign151FeatureError, match="confirmed"):
        c151.build_snapshot(workers=1, confirm_build=False)
