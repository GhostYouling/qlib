from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign059_features as campaign059


def test_protocol_reconstructs_exact_frozen_comparison_order() -> None:
    spec = campaign059.load_protocol()
    comparisons = campaign059.reconstruct_comparisons(spec)
    assert len(comparisons) == 90
    assert campaign059._comparison_order_digest(comparisons) == campaign059.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "quarterly_profit_revenue_growth_spread_pp",
        "score_direction": "higher",
    }


def test_sign_agreement_is_equal_weight_and_direction_only() -> None:
    stock = np.ones((2, 238), dtype=float)
    market = np.ones((2, 238), dtype=float)
    stock[1, 119:] = -1000.0
    values, eligible, quality = campaign059.compute_sign_agreement_values(
        stock, market, np.array([True, True])
    )
    assert eligible.tolist() == [True, True]
    assert values.tolist() == [1.0, 0.5]
    assert quality["agreement_positions"] == 238 + 119


def test_zero_returns_are_excluded_not_counted_as_agreement() -> None:
    stock = np.zeros((2, 238), dtype=float)
    market = np.ones((2, 238), dtype=float)
    stock[0, :60] = 2.0
    stock[1, :59] = 2.0
    values, eligible, quality = campaign059.compute_sign_agreement_values(
        stock, market, np.array([True, True])
    )
    assert eligible.tolist() == [True, False]
    assert values[0] == 1.0
    assert np.isnan(values[1])
    assert quality["insufficient_informative_position_rows"] == 1


def test_peer_gate_and_nonfinite_vector_fail_closed() -> None:
    stock = np.ones((3, 238), dtype=float)
    market = np.ones((3, 238), dtype=float)
    stock[2, 0] = np.nan
    values, eligible, quality = campaign059.compute_sign_agreement_values(
        stock, market, np.array([True, False, True])
    )
    assert eligible.tolist() == [True, False, False]
    assert np.isnan(values[1:]).all()
    assert quality["insufficient_peer_rows"] == 1
    assert quality["nonfinite_stock_or_market_vector_rows"] == 1


def test_invalid_array_shapes_raise() -> None:
    with pytest.raises(campaign059.Campaign059FeatureError):
        campaign059.compute_sign_agreement_values(
            np.ones((1, 237)), np.ones((1, 237)), np.ones(1, dtype=bool)
        )


def test_raw_extractor_uses_only_two_within_half_return_grids() -> None:
    codes = campaign059.SOURCE_MINUTE_CODES
    datetimes = []
    closes = []
    for day in ("2020-01-02", "2020-01-03"):
        for position, code in enumerate(codes):
            hour, minute = divmod(code, 60)
            datetimes.append(pd.Timestamp(day) + pd.Timedelta(hours=hour, minutes=minute))
            closes.append(float(np.exp(position / 10000.0)))
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "000001.SZ",
            "provider": "tushare",
            "close": closes,
        }
    ).loc[:, campaign059.RAW_COLUMNS]
    profiles, quality = campaign059.extract_signed_return_profiles(
        raw, symbol="000001.SZ"
    )
    assert len(profiles) == 2
    first = profiles[pd.Timestamp("2020-01-02")]
    assert first.shape == (238,)
    assert np.allclose(first, 0.0001)
    assert quality["source_rows"] == 482


def test_empty_output_schema_is_exact() -> None:
    frame = campaign059.empty_output_frame()
    assert tuple(frame.columns) == campaign059.OUTPUT_COLUMNS
    assert frame.empty


def test_manifest_validator_requires_market_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(campaign059, "EXPECTED_PARTITIONS", 0)
    monkeypatch.setattr(campaign059, "EXPECTED_ROWS", 0)
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign059_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": campaign059.OUTPUT_RUN_ID,
        "source_fields_read": list(campaign059.RAW_COLUMNS),
        "source_open_high_low_close_volume_read": True,
        "source_close_read": True,
        "source_amount_read": False,
        "cross_session_lookback": 0,
        "market_benchmark_manifest_sha256": campaign059.MARKET_BENCHMARK_MANIFEST_SHA256,
        "market_benchmark_byte_sha256": campaign059.MARKET_BENCHMARK_BYTE_SHA256,
        "market_benchmark_frame_sha256": campaign059.MARKET_BENCHMARK_FRAME_SHA256,
        "market_benchmark_fields_read": list(campaign059.campaign004.market.BENCHMARK_COLUMNS),
        "minimum_leave_one_out_peers_per_position": 50,
        "minimum_informative_positions": 60,
        "factor_names": [campaign059.FACTOR_NAME],
        "factor_directions": campaign059.FACTOR_DIRECTIONS,
        "factor_formulas": campaign059.FACTOR_FORMULAS,
        "protocol_sha256": campaign059.PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": campaign059.MECHANISM_AUDIT_SHA256,
        "partitions": 0,
        "rows": 0,
        "quality": {"base_rows": 0, f"{campaign059.FACTOR_NAME}__eligible_rows": 0},
        "factor_eligible_rows": {campaign059.FACTOR_NAME: 0},
        "files": [],
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
    campaign059._validate_manifest(manifest)
    manifest["market_benchmark_frame_sha256"] = "bad"
    with pytest.raises(campaign059.Campaign059FeatureError):
        campaign059._validate_manifest(manifest)
