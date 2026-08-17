from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign098_features as feature


def _high_low_from_range_mass(rows: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    mass = np.vstack(rows).astype(np.float64)
    low = np.ones_like(mass)
    high = np.exp(mass)
    return high, low


def test_frozen_definition_and_comparator_orders_match_v43() -> None:
    complete = feature.reconstruct_complete_definitions()
    comparisons = feature.reconstruct_comparisons()
    assert len(complete) == feature.FULL_DEFINITION_COUNT == 129
    assert len(comparisons) == feature.COMPARISON_COUNT == 126
    assert feature._order_digest(complete) == feature.FULL_DEFINITION_ORDER_SHA256
    assert feature._order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    assert complete[-1] == {
        "name": "intraday_market_range_profile_synchronization_240m",
        "score_direction": "higher",
    }
    assert comparisons[-1] == complete[-1]


def test_protocol_is_bound_before_values() -> None:
    spec = feature.load_protocol()
    assert spec["candidate"]["name"] == feature.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert (
        spec["ordered_no_return_gates"]["support_predicate_before_source_rows"][
            "candidate_identical_to_or_provably_narrower_than_known_failure"
        ]
        is False
    )
    assert (
        spec["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )


def test_range_clock_variance_exact_endpoints_and_translation() -> None:
    point = np.zeros(240)
    point[100] = 2.0
    endpoints = np.zeros(240)
    endpoints[0] = 1.0
    endpoints[-1] = 1.0
    separated = np.zeros(240)
    separated[20] = 1.0
    separated[60] = 3.0
    translated = np.zeros(240)
    translated[90] = 1.0
    translated[130] = 3.0
    high, low = _high_low_from_range_mass([point, endpoints, separated, translated])
    values, eligible, totals, ranges, centers = feature.compute_range_clock_variance(
        high, low
    )
    assert eligible.tolist() == [True, True, True, True]
    assert values[0] == 0.0
    assert values[1] == 1.0
    assert values[2] == pytest.approx(values[3], abs=1e-14)
    assert totals.tolist() == pytest.approx([2.0, 2.0, 4.0, 4.0])
    assert np.allclose(ranges, np.vstack([point, endpoints, separated, translated]))
    assert centers[3] - centers[2] == pytest.approx(70.0 / 239.0)


def test_range_clock_variance_is_scale_invariant_and_clock_sensitive() -> None:
    base = np.zeros(240)
    base[[10, 30, 70]] = [1.0, 2.0, 1.0]
    scaled = base * 7.0
    permuted = np.zeros(240)
    permuted[[10, 30, 200]] = [1.0, 2.0, 1.0]
    high, low = _high_low_from_range_mass([base, scaled, permuted])
    values, eligible, *_ = feature.compute_range_clock_variance(high, low)
    assert eligible.all()
    assert values[0] == pytest.approx(values[1], abs=1e-14)
    assert values[2] > values[0]


def test_invalid_or_zero_total_support_stays_missing() -> None:
    high = np.ones((4, 240), dtype=np.float64)
    low = np.ones((4, 240), dtype=np.float64)
    high[1, 4] = np.nan
    high[2, 8] = 0.5
    low[2, 8] = 1.0
    high[3, 12] = 2.0
    values, eligible, *_ = feature.compute_range_clock_variance(high, low)
    assert eligible.tolist() == [False, False, False, True]
    assert np.isnan(values[:3]).all()
    assert values[3] == 0.0


def _source_frame() -> pd.DataFrame:
    date = pd.Timestamp("2025-01-02")
    codes = sorted(feature.c90.c86.SOURCE_MINUTE_CODE_SET)
    datetimes = [
        date + pd.Timedelta(hours=code // 60, minutes=code % 60) for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": 1.0,
            "low": 1.0,
        }
    ).loc[:, feature.RAW_COLUMNS]
    continuous = list(feature.c90.c86.CONTINUOUS_MINUTE_CODES)
    raw.loc[
        raw["datetime"].dt.hour * 60 + raw["datetime"].dt.minute == continuous[0],
        "high",
    ] = np.e
    raw.loc[
        raw["datetime"].dt.hour * 60 + raw["datetime"].dt.minute == continuous[-1],
        "high",
    ] = np.e
    raw.loc[raw["datetime"].dt.hour * 60 + raw["datetime"].dt.minute == 570, "high"] = (
        1e9
    )
    return raw


def test_exact_grid_excludes_standalone_0930() -> None:
    frame, quality = feature.extract_range_clock_variance(
        _source_frame(), symbol="SH600000"
    )
    assert len(frame) == 1
    assert frame.iloc[0][feature.FACTOR_NAME] == pytest.approx(1.0)
    assert quality["source_rows"] == 241
    assert quality["valid_range_clock_center_sessions"] == 1
    assert quality["zero_range_bars"] == 238


def test_grid_or_projection_change_fails_closed() -> None:
    raw = _source_frame().iloc[:-1].copy()
    with pytest.raises(feature.Campaign098FeatureError, match="grid changed"):
        feature.extract_range_clock_variance(raw, symbol="SH600000")
    wrong = _source_frame().rename(columns={"high": "open"})
    with pytest.raises(feature.Campaign098FeatureError, match="unexpected raw columns"):
        feature.extract_range_clock_variance(wrong, symbol="SH600000")


def test_status_is_explicitly_no_value() -> None:
    result = feature.status()
    assert result["source_rows_read_by_status"] is False
    assert result["candidate_values_computed_by_status"] is False
    assert result["comparator_values_read_by_status"] is False
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["provider_request_issued_by_status"] is False


def test_verifier_uses_the_active_generated_cache_namespace() -> None:
    assert not hasattr(feature.c90, "cache_v1")
    assert feature._ENGINE["cache_v1"].canonical_column_sha256 is not None


def test_snapshot_retains_original_publication_provenance() -> None:
    manifest = json.loads(
        (
            feature.output_root(feature.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["feature_runner"]["sha256"] == feature.PUBLICATION_RUNNER_SHA256
    assert (
        manifest["implementation_freeze"]["sha256"]
        == feature.PUBLICATION_IMPLEMENTATION_FREEZE_SHA256
    )
