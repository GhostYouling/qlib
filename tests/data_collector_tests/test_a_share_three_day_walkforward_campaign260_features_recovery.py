from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign260_features as base
from scripts import a_share_three_day_walkforward_campaign260_features_recovery as recovery


def _raw(amount: np.ndarray) -> pd.DataFrame:
    minutes = [pd.Timestamp("2024-01-02 09:30")]
    minutes.extend(pd.date_range("2024-01-02 09:31", "2024-01-02 11:30", freq="min"))
    minutes.extend(pd.date_range("2024-01-02 13:01", "2024-01-02 15:00", freq="min"))
    return pd.DataFrame(
        {
            "datetime": minutes,
            "symbol": "SH600000",
            "provider": "tushare",
            "amount": amount,
        }
    )


def test_recovery_preserves_candidate_value_exactly() -> None:
    raw = _raw(np.arange(1.0, 242.0))
    original, _ = base.extract_amount_clock_third_central_moment(
        raw, symbol="SH600000"
    )
    recovered, _ = recovery.extract_amount_clock_third_central_moment(
        raw, symbol="SH600000"
    )
    assert recovered.equals(original)


def test_recovery_adds_exact_inherited_support_counters() -> None:
    amounts = np.ones(241, dtype=np.float64)
    amounts[10] = 0.0
    _, quality = recovery.extract_amount_clock_third_central_moment(
        _raw(amounts), symbol="SH600000"
    )
    assert quality["positive_amount_bars"] == 239
    assert quality["zero_amount_bars"] == 1


def test_invalid_session_contributes_no_support_counters() -> None:
    amounts = np.zeros(241, dtype=np.float64)
    _, quality = recovery.extract_amount_clock_third_central_moment(
        _raw(amounts), symbol="SH600000"
    )
    assert quality["positive_amount_bars"] == 0
    assert quality["zero_amount_bars"] == 0
