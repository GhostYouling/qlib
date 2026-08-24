from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd
import pytest

from scripts import (
    a_share_three_day_walkforward_campaign265_convertible_premium as adapter,
)


ROOT = Path(__file__).resolve().parents[2]
CALENDAR = (
    "2024-01-02",
    "2024-01-03",
    "2024-01-04",
    "2024-01-05",
    "2024-01-08",
)
SIGNAL_SESSION = "2024-01-08"
LAG_SESSION = "2024-01-03"


def basic_frame(rows: list[dict] | None = None) -> pd.DataFrame:
    values = rows or [
        {
            "ts_code": "110001.SH",
            "cb_type": "CB",
            "stk_code": "600000.SH",
            "list_date": "20200101",
            "delist_date": None,
            "exchange": "SSE",
        }
    ]
    return pd.DataFrame(values, columns=adapter.CB_BASIC_FIELDS)


def daily_frame(session: str, rows: list[tuple]) -> pd.DataFrame:
    values = [
        {
            "ts_code": bond,
            "trade_date": session.replace("-", ""),
            "amount": amount,
            "cb_over_rate": premium,
        }
        for bond, amount, premium in rows
    ]
    return pd.DataFrame(values, columns=adapter.CB_DAILY_FIELDS)


def compute(
    basic: pd.DataFrame,
    lag: pd.DataFrame,
    signal: pd.DataFrame,
    universe: tuple[str, ...] = ("SH600000",),
) -> tuple[pd.DataFrame, dict]:
    return adapter.compute_factor_on_session(
        basic,
        lag,
        signal,
        accepted_calendar=CALENDAR,
        factor_universe=universe,
        signal_session=SIGNAL_SESSION,
    )


def test_contract_fingerprint_and_zero_network_boundary_are_exact() -> None:
    assert hashlib.sha256(adapter.SOURCE_CONTRACT.read_bytes()).hexdigest() == (
        adapter.SOURCE_CONTRACT_SHA256
    )
    contract = adapter.load_source_contract()
    assert contract["single_factor_definition"]["name"] == adapter.FACTOR_NAME
    assert contract["single_factor_definition"]["score_direction"] == "higher"
    assert (
        contract["mandatory_next_stage"]["provider_request_authorized_by_this_contract"]
        is False
    )
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import requests",
        "import tushare",
        "TUSHARE_TOKEN",
        "load_dotenv",
        "os.environ",
        "read_parquet",
        "read_csv",
    ):
        assert forbidden not in source


def test_basic_canonicalization_uses_nfkc_uppercase_exact_cb_and_exchange_aliases() -> (
    None
):
    raw = basic_frame(
        [
            {
                "ts_code": " １１０００１．ｓｈ ",
                "cb_type": " ｃｂ ",
                "stk_code": " ６０００００．ｓｈ ",
                "list_date": "２０２００１０１",
                "delist_date": None,
                "exchange": " ｓｓｅ ",
            },
            {
                "ts_code": "123001.sz",
                "cb_type": "EB",
                "stk_code": None,
                "list_date": "20200102",
                "delist_date": "20240108",
                "exchange": "sz",
            },
        ]
    )
    frame, stats = adapter.canonicalize_cb_basic(raw)
    assert frame["bond_code"].tolist() == ["110001.SH", "123001.SZ"]
    assert frame["instrument"].tolist()[0] == "SH600000"
    assert pd.isna(frame["instrument"].tolist()[1])
    assert frame["exchange"].tolist() == ["SH", "SZ"]
    assert stats["exact_cb_rows"] == 1
    assert stats["rejected_non_cb_or_missing_type_rows"] == 1
    assert stats["network_or_credential_access_performed"] is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda frame: frame.assign(extra=1),
        lambda frame: frame.rename(columns={"stk_code": "stock_code"}),
        lambda frame: pd.concat([frame, frame], ignore_index=True),
        lambda frame: frame.assign(exchange="SZSE"),
        lambda frame: frame.assign(stk_code="300001.SZ"),
        lambda frame: frame.assign(list_date="20240230"),
        lambda frame: frame.assign(delist_date="20190101"),
    ],
)
def test_basic_schema_identity_mapping_and_date_fail_closed(mutator) -> None:
    with pytest.raises(adapter.Campaign265AdapterError):
        adapter.canonicalize_cb_basic(mutator(basic_frame()))


def test_daily_projection_date_uniqueness_and_endpoint_eligibility_are_exact() -> None:
    raw = daily_frame(
        LAG_SESSION,
        [
            (" １１０００１．ｓｈ ", "100.5", "20.25"),
            ("123001.SZ", 0.0, 30.0),
            ("123002.SZ", math.inf, None),
        ],
    )
    frame, stats = adapter.canonicalize_cb_daily(raw, LAG_SESSION)
    assert frame["bond_code"].tolist() == ["110001.SH", "123001.SZ", "123002.SZ"]
    assert frame.loc[0, "amount"] == 100.5
    assert frame.loc[0, "cb_over_rate"] == 20.25
    assert stats["finite_positive_amount_and_premium_rows"] == 1
    assert stats["ineligible_endpoint_rows"] == 2

    with pytest.raises(adapter.Campaign265AdapterError):
        adapter.canonicalize_cb_daily(raw.assign(extra=1), LAG_SESSION)
    with pytest.raises(adapter.Campaign265AdapterError):
        adapter.canonicalize_cb_daily(
            pd.concat([raw.iloc[[0]], raw.iloc[[0]]], ignore_index=True), LAG_SESSION
        )
    with pytest.raises(adapter.Campaign265AdapterError):
        adapter.canonicalize_cb_daily(raw.iloc[[0]], SIGNAL_SESSION)


def test_exact_t_minus_three_and_per_bond_compression_are_used() -> None:
    frame, stats = compute(
        basic_frame(),
        daily_frame(LAG_SESSION, [("110001.SH", 100.0, 25.0)]),
        daily_frame(SIGNAL_SESSION, [("110001.SH", 200.0, 16.5)]),
    )
    assert frame.loc[0, "lag_session"] == LAG_SESSION
    assert frame.loc[0, "signal_session"] == SIGNAL_SESSION
    assert frame.loc[0, "factor_value"] == 8.5
    assert frame.loc[0, "active_cb_count"] == 1
    assert frame.loc[0, "eligible_cb_count"] == 1
    assert stats["denominator_equity_count"] == 1
    assert stats["eligible_equity_count"] == 1


def test_active_interval_and_missing_endpoint_remain_missing_not_zero() -> None:
    basics = basic_frame(
        [
            {
                "ts_code": "110001.SH",
                "cb_type": "CB",
                "stk_code": "600000.SH",
                "list_date": "20240105",
                "delist_date": None,
                "exchange": "SH",
            },
            {
                "ts_code": "110002.SH",
                "cb_type": "CB",
                "stk_code": "600001.SH",
                "list_date": "20200101",
                "delist_date": "20240105",
                "exchange": "SSE",
            },
        ]
    )
    frame, stats = compute(
        basics,
        daily_frame(LAG_SESSION, [("110001.SH", 100.0, 20.0)]),
        daily_frame(SIGNAL_SESSION, [("110001.SH", 0.0, 10.0)]),
        ("SH600000", "SH600001"),
    )
    assert frame["instrument"].tolist() == ["SH600000"]
    assert frame.loc[0, "active_cb_count"] == 1
    assert frame.loc[0, "eligible_cb_count"] == 0
    assert math.isnan(frame.loc[0, "factor_value"])
    assert stats["denominator_equity_count"] == 1
    assert stats["eligible_equity_count"] == 0
    assert stats["missing_factor_is_zero"] is False


def test_multiple_bonds_use_exact_odd_and_even_arithmetic_medians() -> None:
    basics = basic_frame(
        [
            {
                "ts_code": bond,
                "cb_type": "CB",
                "stk_code": "600000.SH",
                "list_date": "20200101",
                "delist_date": None,
                "exchange": "SH",
            }
            for bond in ("110001.SH", "110002.SH", "110003.SH")
        ]
    )
    lag = daily_frame(
        LAG_SESSION,
        [
            ("110001.SH", 1.0, 20.0),
            ("110002.SH", 1.0, 10.0),
            ("110003.SH", 1.0, 30.0),
        ],
    )
    signal = daily_frame(
        SIGNAL_SESSION,
        [
            ("110001.SH", 1.0, 10.0),
            ("110002.SH", 1.0, 4.0),
            ("110003.SH", 0.0, 10.0),
        ],
    )
    even, _ = compute(basics, lag, signal)
    assert even.loc[0, "eligible_cb_count"] == 2
    assert even.loc[0, "factor_value"] == 8.0

    signal.loc[signal["ts_code"].eq("110003.SH"), "amount"] = 1.0
    odd, _ = compute(basics, lag, signal)
    assert odd.loc[0, "eligible_cb_count"] == 3
    assert odd.loc[0, "factor_value"] == 10.0


def test_exact_cb_denominator_respects_factor_universe_and_unknown_daily_bond_fails() -> (
    None
):
    basics = basic_frame(
        [
            {
                "ts_code": "110001.SH",
                "cb_type": "CB",
                "stk_code": "600000.SH",
                "list_date": "20200101",
                "delist_date": None,
                "exchange": "SSE",
            },
            {
                "ts_code": "123001.SZ",
                "cb_type": "CB",
                "stk_code": "300001.SZ",
                "list_date": "20200101",
                "delist_date": None,
                "exchange": "SZSE",
            },
            {
                "ts_code": "110002.SH",
                "cb_type": "EB",
                "stk_code": None,
                "list_date": "20200101",
                "delist_date": None,
                "exchange": "SH",
            },
        ]
    )
    lag = daily_frame(
        LAG_SESSION,
        [("110001.SH", 1.0, 20.0), ("123001.SZ", 1.0, 30.0)],
    )
    signal = daily_frame(
        SIGNAL_SESSION,
        [("110001.SH", 1.0, 10.0), ("123001.SZ", 1.0, 25.0)],
    )
    frame, _ = compute(basics, lag, signal, ("SZ300001",))
    assert frame["instrument"].tolist() == ["SZ300001"]
    assert frame["factor_value"].tolist() == [5.0]

    unknown = daily_frame(SIGNAL_SESSION, [("123999.SZ", 1.0, 1.0)])
    with pytest.raises(adapter.Campaign265AdapterError):
        compute(basics, lag, unknown, ("SZ300001",))


def test_calendar_and_universe_must_be_exact_unique_ordered_sequences() -> None:
    lag = daily_frame(LAG_SESSION, [("110001.SH", 1.0, 2.0)])
    signal = daily_frame(SIGNAL_SESSION, [("110001.SH", 1.0, 1.0)])
    for calendar in (
        tuple(reversed(CALENDAR)),
        CALENDAR + (SIGNAL_SESSION,),
        CALENDAR[:3],
    ):
        with pytest.raises(adapter.Campaign265AdapterError):
            adapter.compute_factor_on_session(
                basic_frame(),
                lag,
                signal,
                accepted_calendar=calendar,
                factor_universe=("SH600000",),
                signal_session=SIGNAL_SESSION,
            )
    with pytest.raises(adapter.Campaign265AdapterError):
        compute(basic_frame(), lag, signal, ("SH600000", "SH600000"))


def test_all_outputs_are_synthetic_and_research_boundaries_stay_false() -> None:
    _, stats = compute(
        basic_frame(),
        daily_frame(LAG_SESSION, [("110001.SH", 1.0, 2.0)]),
        daily_frame(SIGNAL_SESSION, [("110001.SH", 1.0, 1.0)]),
    )
    assert stats["network_or_credential_access_performed"] is False
    assert stats["candidate49_or_return_data_read"] is False
    assert stats["cb_basic"]["forbidden_fields_read"] is False
    assert stats["lag_cb_daily"]["forbidden_fields_read"] is False
    assert stats["signal_cb_daily"]["forbidden_fields_read"] is False
