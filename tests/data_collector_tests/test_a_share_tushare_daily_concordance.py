"""Offline tests for the independent Tushare/BaoStock daily comparison."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "a_share_tushare_daily_concordance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a_share_tushare_daily_concordance", SCRIPT_PATH
)
DAILY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = DAILY
SPEC.loader.exec_module(DAILY)


def provider_frame() -> pd.DataFrame:
    rows = []
    for index, code in enumerate(sorted(DAILY.REPRESENTATIVE_CODES)):
        close = 10.0 + index
        rows.append(
            {
                "ts_code": code,
                "trade_date": "20251231",
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "pre_close": close - 0.05,
                "change": 0.05,
                "pct_chg": 0.5,
                "vol": 1234.0,
                "amount": 5678.0,
            }
        )
    return pd.DataFrame(rows)


def test_canonicalize_acceptance_requires_exact_schema_and_representatives() -> None:
    result = DAILY.canonicalize_tushare_daily(
        provider_frame(), DAILY.ACCEPTANCE_DATE, require_representatives=True
    )

    assert tuple(result.columns) == DAILY.FIELDS
    assert len(result) == 4
    assert result["trade_date"].dtype == "datetime64[ns]"


def test_canonicalize_rejects_invalid_ohlc_envelope() -> None:
    frame = provider_frame()
    frame.loc[0, "high"] = frame.loc[0, "close"] - 1.0

    with pytest.raises(DAILY.DailyConcordanceError, match="OHLC envelope"):
        DAILY.canonicalize_tushare_daily(frame, DAILY.ACCEPTANCE_DATE)


def test_canonicalize_preserves_null_auxiliary_change_fields() -> None:
    frame = provider_frame()
    frame.loc[0, ["pre_close", "change", "pct_chg"]] = np.nan

    result = DAILY.canonicalize_tushare_daily(frame, DAILY.ACCEPTANCE_DATE)

    observed = result.loc[
        result["ts_code"] == frame.loc[0, "ts_code"], "pre_close"
    ]
    assert observed.isna().all()


def test_normalization_converts_amount_but_keeps_lot_volume() -> None:
    canonical = DAILY.canonicalize_tushare_daily(
        provider_frame(), DAILY.ACCEPTANCE_DATE
    )
    normalized = DAILY.normalize_tushare_for_comparison(canonical)

    assert normalized.loc[0, "volume"] == pytest.approx(1234.0)
    assert normalized.loc[0, "amount"] == pytest.approx(5_678_000.0)
    assert normalized["symbol"].str.match(r"^(SH|SZ|BJ)\d{6}$").all()


def test_relative_error_handles_zero_reference_and_summarizes_bands() -> None:
    errors = DAILY.relative_error(
        np.asarray([10.0, 10.02, 0.0, 1.0]),
        np.asarray([10.0, 10.0, 0.0, 0.0]),
    )
    summary = DAILY.summarize_errors(errors)

    assert errors[0] == 0.0
    assert errors[1] == pytest.approx(0.002)
    assert errors[2] == 0.0
    assert np.isinf(errors[3])
    assert summary["exact_rows"] == 2
    assert summary["infinite_relative_error_rows"] == 1
