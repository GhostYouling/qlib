from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign066_features as campaign


def test_protocol_reconstructs_exact_96_numeric_order_without_source_rows(monkeypatch):
    monkeypatch.setattr(pd, "read_parquet", lambda *args, **kwargs: pytest.fail("protocol validation must not read source rows"))
    spec = campaign.load_protocol()
    comparisons = campaign.reconstruct_comparisons(spec)
    assert len(comparisons) == 96
    assert comparisons[-2:] == [
        {"name": "intraday_range_weak_order_entropy_236t", "score_direction": "higher"},
        {"name": campaign.C65_FACTOR, "score_direction": "higher"},
    ]
    assert campaign.C63_FACTOR not in [item["name"] for item in comparisons]
    assert campaign._comparison_order_digest(comparisons) == campaign.COMPARISON_ORDER_SHA256


def test_balance_formula_is_exact_bounded_and_strictly_finite():
    ranks = np.array([[0.2, 0.2, 0.2], [0.1, 0.5, 0.9], [0.0, 1.0, 0.5], [np.nan, 0.2, 0.3], [1.1, 0.2, 0.3]])
    values, eligible = campaign.compute_balance_values(ranks)
    assert values[:3].tolist() == pytest.approx([1.0, 0.2, 0.0])
    assert eligible.tolist() == [True, True, True, False, False]
    assert np.isnan(values[3:]).all()


def test_daily_average_tie_ranks_and_mean_preserving_spread():
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02"] * 4),
            "symbol": ["SH1", "SH2", "SH3", "SH4"],
            "provider": ["tushare"] * 4,
            "roe": [1.0, 2.0, 2.0, 4.0],
            "profit_yoy": [1.0, 2.0, 3.0, 4.0],
            "revenue_yoy": [1.0, 3.0, 2.0, 4.0],
        }
    )
    result = campaign.rank_and_balance_year_frame(frame)
    assert result.loc[0, campaign.FACTOR_NAME] == 1.0
    assert result.loc[3, campaign.FACTOR_NAME] == 1.0
    assert result.loc[1, campaign.FACTOR_NAME] == pytest.approx(0.75)
    assert result.loc[2, campaign.FACTOR_NAME] == pytest.approx(0.75)
    assert result[f"{campaign.FACTOR_NAME}_eligible"].all()


def test_prepare_events_uses_strict_next_session_dedup_and_independent_fill():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]))
    events = pd.DataFrame(
        {
            "instrument": ["SH1", "SH1", "SH1"],
            "report_date": pd.to_datetime(["2019-09-30", "2019-12-30", "2019-12-31"]),
            "announcement_date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-03"]),
            "roe": [1.0, 2.0, 3.0],
            "profit_yoy": [10.0, np.nan, 30.0],
            "revenue_yoy": [5.0, 8.0, np.nan],
        }
    ).loc[:, campaign.EVENT_FIELDS]
    prepared = campaign.prepare_events(events, calendar)
    positions, states = prepared["SH1"]
    assert positions.tolist() == [1, 2]
    assert states[0].tolist() == [1.0, 10.0, 5.0]
    assert states[1].tolist() == [3.0, 30.0, 5.0]


def test_attach_states_never_backfills_before_effective_date_or_cross_symbol():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]))
    base = pd.DataFrame({"trade_date": calendar, "symbol": ["SH1"] * 3, "provider": ["tushare"] * 3})
    events = {"SH1": (np.array([1], dtype=np.int64), np.array([[2.0, 3.0, 4.0]]))}
    result = campaign.attach_states(base, symbol="SH1", calendar=calendar, events_by_symbol=events)
    assert result.loc[0, list(campaign.STATE_FIELDS)].isna().all()
    assert result.loc[1, list(campaign.STATE_FIELDS)].tolist() == [2.0, 3.0, 4.0]
    other = base.assign(symbol="SH2")
    other_result = campaign.attach_states(other, symbol="SH2", calendar=calendar, events_by_symbol=events)
    assert other_result.loc[:, list(campaign.STATE_FIELDS)].isna().all().all()


def test_empty_bound_partition_is_preserved_with_state_schema():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2020-01-02"]))
    empty = pd.DataFrame({
        "trade_date": pd.Series(dtype="datetime64[ns]"),
        "symbol": pd.Series(dtype="object"),
        "provider": pd.Series(dtype="object"),
    })
    result = campaign.attach_states(empty, symbol="SH600145", calendar=calendar, events_by_symbol={})
    assert result.empty
    assert tuple(result.columns) == ("trade_date", "symbol", "provider", *campaign.STATE_FIELDS)


def test_manifest_validator_rejects_return_or_candidate49_mutation(monkeypatch):
    monkeypatch.setattr(campaign, "EXPECTED_PARTITIONS", 1)
    monkeypatch.setattr(campaign, "EXPECTED_ROWS", 2)
    manifest = {
        "kind": "a_share_three_day_walkforward_campaign066_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "partitions": 1,
        "rows": 2,
        "files": [{}],
        "factor_names": [campaign.FACTOR_NAME],
        "factor_directions": {campaign.FACTOR_NAME: "higher"},
        "factor_formulas": {campaign.FACTOR_NAME: campaign.FACTOR_FORMULA},
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": campaign.MECHANISM_AUDIT_SHA256,
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "comparison_factor_values_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    }
    campaign._validate_manifest(manifest)
    changed = json.loads(json.dumps(manifest))
    changed["forward_return_fields_read"] = True
    with pytest.raises(campaign.Campaign066FeatureError, match="snapshot semantics"):
        campaign._validate_manifest(changed)


def test_status_is_no_source_row_no_value_boundary(monkeypatch):
    monkeypatch.setattr(pd, "read_parquet", lambda *args, **kwargs: pytest.fail("status must not read source rows"))
    result = campaign.status(campaign.DEFAULT_DATA_ROOT)
    assert result["candidate_or_comparison_values_read_by_status"] is False
    assert result["daily_price_fields_read_by_status"] == []
    assert result["historical_forward_return_fields_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
