from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign099_features as feature


def _manifest_envelope(kind: str) -> dict[str, object]:
    quality = {
        name: 0
        for name in (
            "invalid_required_hlc_rows",
            "nonfinite_or_out_of_range_profile_rows",
            "zero_range_state_count",
            "endpoint_canonicalized_state_count",
            "insufficient_leave_one_out_peer_rows",
            "constant_own_profile_rows",
            "constant_market_profile_rows",
            "nonfinite_correlation_rows",
            "endpoint_canonicalized_rows",
            "range_violation_rows",
        )
    }
    return {
        "kind": kind,
        "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
        "protocol_sha256": feature.PROTOCOL_SHA256,
        "raw_manifest_sha256": feature.c97.base.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": feature.c97.base.JOINT_MANIFEST_SHA256,
        "output_run_id": feature.OUTPUT_RUN_ID,
        "factor_name": feature.FACTOR_NAME,
        "factor_direction": "higher",
        "factor_formula": feature.FACTOR_FORMULA,
        "partitions": 33_015,
        "rows": 7_724_498,
        "quality": quality,
        "market_benchmark": {
            "rows": 240,
            "trade_dates": 1,
            "profile_positions_per_date": 240,
            "processed_symbol_count": 5_396,
            "valid_stock_count_minimum": 51,
        },
        "source_fields_read": list(feature.RAW_COLUMNS),
        "standalone_09_30_row_excluded_from_formula": True,
        "minimum_leave_one_out_peers": feature.MINIMUM_LEAVE_ONE_OUT_PEERS,
        "comparison_factor_values_read": False,
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "source_close_read": True,
    }


def test_campaign099_protocol_and_definition_orders_are_bound() -> None:
    spec = feature.load_protocol()
    assert spec["candidate"]["name"] == feature.FACTOR_NAME
    assert len(feature.reconstruct_complete_definitions()) == 130
    assert len(feature.reconstruct_comparisons()) == 127
    assert feature._order_digest(feature.reconstruct_complete_definitions()) == (
        feature.FULL_DEFINITION_ORDER_SHA256
    )
    assert feature._order_digest(feature.reconstruct_comparisons()) == (
        feature.COMPARISON_ORDER_SHA256
    )


def test_close_location_profiles_use_signed_log_geometry_and_neutral_zero_range() -> (
    None
):
    low = np.ones((2, 240), dtype=float)
    high = np.full((2, 240), 4.0, dtype=float)
    close = np.full((2, 240), 2.0, dtype=float)
    high[0, 0] = low[0, 0] = close[0, 0] = 3.0
    close[0, 1] = 4.0
    close[0, 2] = 1.0
    profiles, valid, quality = feature.compute_close_location_profiles(high, low, close)
    assert valid.tolist() == [True, True]
    assert profiles[0, 0] == 0.0
    assert profiles[0, 1] == 1.0
    assert profiles[0, 2] == -1.0
    assert np.allclose(profiles[1], 0.0)
    assert quality["zero_range_state_count"] == 1


def test_close_location_profiles_reject_unordered_or_nonpositive_hlc() -> None:
    low = np.ones((3, 240), dtype=float)
    high = np.full((3, 240), 2.0, dtype=float)
    close = np.full((3, 240), 1.5, dtype=float)
    close[0, 10] = 2.1
    low[1, 20] = 0.0
    high[2, 30] = np.nan
    profiles, valid, quality = feature.compute_close_location_profiles(high, low, close)
    assert valid.tolist() == [False, False, False]
    assert np.isnan(profiles).all()
    assert quality["invalid_required_hlc_rows"] == 3


def test_profile_correlations_require_peer_support_and_nonconstant_vectors() -> None:
    x = np.linspace(-1.0, 1.0, 240)
    profiles = np.vstack([x, -x, np.zeros(240)])
    valid = np.array([True, True, True])
    sums = np.vstack([x * 51.0, x * 51.0, x * 51.0])
    counts = np.full((3, 240), 51, dtype=np.int64)
    values, eligible, quality = feature.c97.compute_profile_correlations(
        profiles, valid, sums, counts
    )
    assert eligible.tolist() == [True, True, False]
    assert values[0] == pytest.approx(1.0)
    assert values[1] == pytest.approx(-1.0)
    assert np.isnan(values[2])
    assert quality["constant_own_profile_rows"] == 1


def test_extract_partition_profiles_enforces_exact_source_grid() -> None:
    symbol = "SZ000001"
    date = pd.Timestamp("2021-01-04")
    codes = sorted(feature.c97.base.SOURCE_MINUTE_CODE_SET)
    raw = pd.DataFrame(
        {
            "datetime": [
                date + pd.Timedelta(hours=code // 60, minutes=code % 60)
                for code in codes
            ],
            "symbol": symbol,
            "provider": "tushare",
            "high": 2.0,
            "low": 1.0,
            "close": np.linspace(1.01, 1.99, len(codes)),
        }
    ).loc[:, feature.RAW_COLUMNS]
    base = pd.DataFrame(
        {"trade_date": [date], "symbol": [symbol], "provider": ["tushare"]}
    )
    base_work, profiles, valid, quality = feature.extract_partition_profiles(
        raw, base, symbol=symbol
    )
    assert len(base_work) == 1
    assert profiles.shape == (1, 240)
    assert valid.tolist() == [True]
    assert quality["invalid_required_hlc_rows"] == 0
    with pytest.raises(feature.Campaign099FeatureError):
        feature.extract_partition_profiles(raw.iloc[:-1], base, symbol=symbol)


def test_status_is_no_value_no_return_read_only() -> None:
    payload = feature.status(feature.DEFAULT_DATA_ROOT)
    assert payload["comparison_values_read_by_feature_build"] is False
    assert payload["daily_price_or_forward_return_read_by_feature_build"] is False


def test_transient_generic_engine_manifest_envelope_is_strictly_accepted() -> None:
    manifest = _manifest_envelope(
        "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    )
    manifest.update(
        {
            "source_volume_or_amount_read": False,
            "source_open_high_low_read": False,
            "leave_one_out_equal_weight_market": True,
        }
    )
    feature._validate_snapshot_manifest(manifest, require_fingerprint_constants=False)


def test_finalized_campaign099_manifest_envelope_is_strictly_accepted() -> None:
    manifest = _manifest_envelope(
        "a_share_three_day_walkforward_campaign099_feature_snapshot"
    )
    manifest.update(
        {
            "zero_range_state": 0.0,
            "source_high_low_read": True,
            "source_open_read": False,
            "source_volume_read": False,
            "source_amount_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }
    )
    feature._validate_snapshot_manifest(manifest, require_fingerprint_constants=False)


def test_mixed_manifest_envelope_is_rejected() -> None:
    manifest = _manifest_envelope(
        "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    )
    manifest.update(
        {
            "source_volume_or_amount_read": False,
            "source_open_high_low_read": False,
            "leave_one_out_equal_weight_market": True,
            "zero_range_state": 0.0,
        }
    )
    with pytest.raises(feature.Campaign099FeatureError):
        feature._validate_snapshot_manifest(
            manifest, require_fingerprint_constants=False
        )
