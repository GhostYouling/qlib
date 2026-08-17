from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "a_share_tushare_limit_up_queue_persistence.py"
SPEC = importlib.util.spec_from_file_location("campaign115_limit_queue", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def frame(rows: list[list[object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=MODULE.RAW_FIELDS)


def test_campaign115_contract_is_exactly_fingerprint_bound(tmp_path: Path) -> None:
    contract = MODULE.load_contract()
    assert contract["factor"]["name"] == MODULE.FACTOR_NAME
    changed = json.loads(MODULE.DEFAULT_CONTRACT.read_text(encoding="utf-8"))
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(MODULE.LimitQueueContractError, match="alternate"):
        MODULE.load_contract(changed_path)


@pytest.mark.parametrize(
    ("last_time", "expected"),
    [
        ("092500", 245),
        ("113000", 120),
        ("130000", 120),
        ("145500", 5),
        ("145933", 0),
        ("150000", 0),
    ],
)
def test_remaining_session_minutes_uses_frozen_clock(
    last_time: str, expected: int
) -> None:
    assert MODULE.remaining_session_minutes(last_time) == expected


def test_canonicalizer_maps_u_queue_and_valid_non_events_to_full_universe() -> None:
    raw = frame(
        [
            ["600519.SH", "20260713", "U", "130000", 1],
            ["000001.SZ", "20260713", "D", None, None],
            ["300750.SZ", "20260713", "Z", None, None],
            ["688981.SH", "20260713", "U", 145500, 0],
        ]
    )
    result, quality = MODULE.canonicalize_limit_queue_response(
        raw,
        trade_date=dt.date(2026, 7, 13),
        active_instruments=["SH600519", "SZ000001", "SZ300750", "SH688981", "SZ000002"],
    )
    scores = result.set_index("instrument")[MODULE.FACTOR_NAME]
    assert scores["SH600519"] == pytest.approx(120 / (245 * 2))
    assert scores["SH688981"] == pytest.approx(5 / 245)
    assert scores["SZ000001"] == 0.0
    assert scores["SZ300750"] == 0.0
    assert scores["SZ000002"] == 0.0
    assert quality["valid_upper_limit_names"] == 2
    assert quality["daily_prices_or_forward_returns_read"] is False


def test_empty_exact_schema_is_a_valid_zero_event_cross_section() -> None:
    result, quality = MODULE.canonicalize_limit_queue_response(
        frame([]),
        trade_date=dt.date(2026, 7, 13),
        active_instruments=["SH600519", "SZ000001"],
    )
    assert result[MODULE.FACTOR_NAME].tolist() == [0.0, 0.0]
    assert quality["source_rows"] == 0


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            [
                ["600519.SH", "20260713", "U", "145500", 0],
                ["600519.SH", "20260713", "U", "145500", 0],
            ],
            "duplicate",
        ),
        ([["600519.SH", "20260712", "U", "145500", 0]], "another trade_date"),
        ([["600519.SH", "20260713", "X", "145500", 0]], "unknown limit state"),
        ([["600519.SH", "20260713", "U", "120000", 0]], "outside the frozen"),
        ([["600519.SH", "20260713", "U", "145500", -1]], "nonnegative integer"),
    ],
)
def test_canonicalizer_fails_closed_on_invalid_source_semantics(
    rows: list[list[object]], message: str
) -> None:
    with pytest.raises(MODULE.LimitQueueContractError, match=message):
        MODULE.canonicalize_limit_queue_response(
            frame(rows),
            trade_date=dt.date(2026, 7, 13),
            active_instruments=["SH600519"],
        )


def test_canonicalizer_rejects_extra_or_reordered_fields() -> None:
    raw = frame([["600519.SH", "20260713", "U", "145500", 0]])
    with pytest.raises(MODULE.LimitQueueContractError, match="field order"):
        MODULE.canonicalize_limit_queue_response(
            raw.loc[:, list(reversed(MODULE.RAW_FIELDS))],
            trade_date=dt.date(2026, 7, 13),
            active_instruments=["SH600519"],
        )
