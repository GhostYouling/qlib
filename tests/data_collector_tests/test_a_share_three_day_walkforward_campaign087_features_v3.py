from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v2 as v2
from scripts import a_share_three_day_walkforward_campaign087_features_v3 as v3


def test_v3_repair_inputs_are_immutable() -> None:
    assert v3._sha256(v3.REPAIR_PROTOCOL) == v3.REPAIR_PROTOCOL_SHA256
    assert v3._sha256(v1.DEFAULT_IMPLEMENTATION_FREEZE) == v3.V1_FREEZE_SHA256
    assert v3._sha256(v2.DEFAULT_IMPLEMENTATION_FREEZE) == v3.V2_FREEZE_SHA256
    assert v3._sha256(v3.Path(v2.__file__).resolve()) == v3.V2_RUNNER_SHA256
    assert (
        v3._sha256(v3.Path(v3.c86_v3.__file__).resolve())
        == v3.C86_V3_RUNNER_SHA256
    )


def test_composed_context_returns_exact_empty_current_factor_schema() -> None:
    identity = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
        }
    ).loc[:, v1.IDENTITY_COLUMNS]
    values = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            v1.FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    original = c86.attach_values
    with v3._corrected_campaign086_builder():
        attached = c86.attach_values(identity, values, symbol="SH600145")
        assert tuple(attached.columns) == (*v1.IDENTITY_COLUMNS, v1.FACTOR_NAME)
        assert attached.empty
    assert c86.attach_values is original


def test_composed_context_preserves_nonempty_attachment() -> None:
    identity = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2023-06-01")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
        }
    ).loc[:, v1.IDENTITY_COLUMNS]
    values = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2023-06-01")],
            v1.FACTOR_NAME: [0.75],
        }
    )
    with v3._corrected_campaign086_builder():
        attached = c86.attach_values(identity, values, symbol="SH600000")
        assert attached[v1.FACTOR_NAME].tolist() == [0.75]
        assert attached["provider"].tolist() == ["tushare"]


def test_v3_changes_no_formula_order_or_gate() -> None:
    assert v1.FACTOR_NAME == "intraday_range_amount_profile_alignment_js_240m"
    assert v1.COMPARISON_COUNT == 116
    assert v1.FULL_DEFINITION_COUNT == 118
    assert v1.ENDPOINT_TOLERANCE == 1e-12
