from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign058_features as campaign


def _raw_identity(symbol: str, date: str) -> pd.DataFrame:
    morning = pd.date_range(f"{date} 09:30", periods=121, freq="1min")
    afternoon = pd.date_range(f"{date} 13:01", periods=120, freq="1min")
    times = morning.append(afternoon)
    return pd.DataFrame(
        {
            "datetime": times,
            "symbol": symbol,
            "provider": "tushare",
        }
    ).loc[:, campaign.RAW_COLUMNS]


def test_protocol_is_compact_but_reconstructs_exact_89_factor_order(monkeypatch):
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("protocol validation must not read source rows"),
    )
    spec = campaign.load_protocol()
    comparisons = campaign._reconstruct_comparisons(spec)
    assert len(comparisons) == 89
    assert comparisons[-9:] == [
        {
            "name": "intraday_day_over_day_absolute_return_profile_similarity_238b",
            "score_direction": "higher",
        },
        {"name": "quality_roe", "score_direction": "higher"},
        {"name": "quality_profit", "score_direction": "higher"},
        {"name": "quality_revenue", "score_direction": "higher"},
        {"name": "quality_growth", "score_direction": "higher"},
        {"name": "quality_score", "score_direction": "higher"},
        {"name": "roe_change", "score_direction": "higher"},
        {"name": "revenue_yoy_acceleration", "score_direction": "higher"},
        {"name": "profit_yoy_acceleration", "score_direction": "higher"},
    ]
    assert campaign._comparison_order_digest(comparisons) == campaign.COMPARISON_ORDER_SHA256


def test_spread_formula_is_raw_profit_minus_revenue_with_strict_finiteness():
    values, eligible, quality = campaign.compute_spread_values(
        np.array([30.0, 10.0, np.nan, np.finfo(np.float64).max]),
        np.array([20.0, 25.0, 5.0, -np.finfo(np.float64).max]),
    )
    assert values[:2].tolist() == [10.0, -15.0]
    assert eligible.tolist() == [True, True, False, False]
    assert np.isnan(values[2:]).all()
    assert quality == {
        "rows": 4,
        "eligible_rows": 2,
        "nonfinite_profit_state_rows": 1,
        "nonfinite_revenue_state_rows": 0,
        "nonfinite_subtraction_rows": 1,
    }


def test_extract_uses_latest_effective_state_without_future_or_cross_symbol_fill(monkeypatch):
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"])
    calendar_values = pd.DatetimeIndex(dates).to_numpy(dtype="datetime64[ns]")
    monkeypatch.setattr(
        campaign,
        "_QUARTERLY_CACHE",
        (
            calendar_values,
            {
                "SH600000": (
                    np.array([1, 2], dtype=np.int64),
                    np.array([5.0, -3.0], dtype=np.float64),
                )
            },
        ),
    )
    raw = pd.concat(
        [_raw_identity("SH600000", date.strftime("%Y-%m-%d")) for date in dates],
        ignore_index=True,
    )
    states, quality = campaign.extract_quarterly_spread_states(raw, symbol="SH600000")
    assert np.isnan(states[pd.Timestamp("2020-01-02")])
    assert states[pd.Timestamp("2020-01-03")] == 5.0
    assert states[pd.Timestamp("2020-01-06")] == -3.0
    assert quality["sessions_without_prior_effective_quarterly_event"] == 1
    assert quality["sessions_with_finite_growth_spread_state"] == 2


def test_raw_identity_requires_exact_241_row_grid(monkeypatch):
    date = pd.Timestamp("2020-01-02")
    monkeypatch.setattr(
        campaign,
        "_QUARTERLY_CACHE",
        (
            pd.DatetimeIndex([date]).to_numpy(dtype="datetime64[ns]"),
            {},
        ),
    )
    raw = _raw_identity("SZ000001", "2020-01-02").iloc[:-1].copy()
    with pytest.raises(campaign.Campaign058FeatureError, match="241-row identity grid"):
        campaign.extract_quarterly_spread_states(raw, symbol="SZ000001")


def test_output_alignment_keeps_missing_state_missing_and_reads_no_prior_session():
    base = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "symbol": ["SH600000", "SH600000"],
            "provider": ["tushare", "tushare"],
        }
    ).loc[:, campaign.BASE_COLUMNS]
    frame, quality = campaign.compute_output_frame(
        base,
        {
            pd.Timestamp("2020-01-02"): np.nan,
            pd.Timestamp("2020-01-03"): 7.5,
        },
        {pd.Timestamp("2020-01-03"): pd.Timestamp("2020-01-02")},
        symbol="SH600000",
    )
    assert frame[campaign.FACTOR_NAME].isna().tolist() == [True, False]
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [False, True]
    assert frame.loc[1, campaign.FACTOR_NAME] == 7.5
    assert set(frame["provider"]) == {"eastmoney_quarterly_quality"}
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 1


def test_engine_build_functions_are_bound_to_campaign058_overrides():
    globals_ = campaign.build_snapshot.__globals__
    assert globals_["RAW_COLUMNS"] == campaign.RAW_COLUMNS
    assert globals_["FACTOR_NAME"] == campaign.FACTOR_NAME
    assert globals_["extract_amount_profiles"] is campaign.extract_quarterly_spread_states
    assert globals_["compute_output_frame"] is campaign.compute_output_frame
    assert globals_["_validate_manifest"] is campaign._validate_manifest
    assert globals_["_load_protocol"] is campaign.load_protocol


def test_manifest_validator_requires_quarterly_source_and_no_price_return_reads(monkeypatch):
    monkeypatch.setattr(campaign, "EXPECTED_PARTITIONS", 1)
    monkeypatch.setattr(campaign, "EXPECTED_ROWS", 2)
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign058_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": campaign.OUTPUT_RUN_ID,
        "source_fields_read": list(campaign.RAW_COLUMNS),
        "source_open_high_low_close_volume_read": False,
        "source_close_read": False,
        "source_amount_read": False,
        "quarterly_value_fields_read": ["revenue_yoy", "profit_yoy"],
        "quarterly_source_path": str(campaign.QUARTERLY_PATH.resolve()),
        "quarterly_source_sha256": campaign.QUARTERLY_SHA256,
        "quarterly_manifest_path": str(campaign.QUARTERLY_MANIFEST_PATH.resolve()),
        "quarterly_manifest_sha256": campaign.QUARTERLY_MANIFEST_SHA256,
        "quarterly_fields_read": list(campaign.EVENT_FIELDS),
        "cross_session_lookback": 0,
        "quarterly_state_rule": "strict_next_session_then_independent_per_field_forward_fill",
        "factor_names": [campaign.FACTOR_NAME],
        "factor_directions": campaign.FACTOR_DIRECTIONS,
        "factor_formulas": campaign.FACTOR_FORMULAS,
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": campaign.MECHANISM_AUDIT_SHA256,
        "partitions": 1,
        "rows": 2,
        "files": [{}],
        "quality": {"base_rows": 2, f"{campaign.FACTOR_NAME}__eligible_rows": 1},
        "factor_eligible_rows": {campaign.FACTOR_NAME: 1},
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "comparison_factor_values_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "prospective_candidate_activation_created": False,
        "provider_request_issued": False,
    }
    campaign._validate_manifest(manifest)
    changed = json.loads(json.dumps(manifest))
    changed["quarterly_value_fields_read"] = ["profit_yoy", "revenue_yoy"]
    with pytest.raises(campaign.Campaign058FeatureError, match="snapshot semantics"):
        campaign._validate_manifest(changed)


def test_status_is_no_source_row_no_price_no_return_boundary(monkeypatch):
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("status must not read source rows"),
    )
    result = campaign.status(campaign.DEFAULT_DATA_ROOT)
    assert result["minute_price_or_activity_fields_read_by_build"] is False
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
