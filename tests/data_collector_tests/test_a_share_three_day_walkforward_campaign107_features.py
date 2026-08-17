from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign107_features as campaign107


def _raw(closes: np.ndarray, *, opening_close: float = 1.0) -> pd.DataFrame:
    values = {
        code: float(value)
        for code, value in zip(campaign107.CONTINUOUS_MINUTE_CODES, closes, strict=True)
    }
    values[9 * 60 + 30] = opening_close
    rows = []
    for code in sorted(campaign107.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "close": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign107.RAW_COLUMNS]


def _score(closes: np.ndarray, **kwargs: float) -> tuple[float, dict[str, int]]:
    frame, quality = campaign107.extract_exact_close_level_diversity(
        _raw(closes, **kwargs), symbol="000001.SZ"
    )
    return float(frame.loc[0, "exact_close_level_diversity"]), quality


def test_effective_overlay_and_v66_orders_are_prevalue_safe() -> None:
    effective = campaign107.load_protocol()
    comparisons = campaign107.reconstruct_comparisons()
    definitions = campaign107.reconstruct_complete_definitions()
    assert effective["base"]["candidate"]["name"] == campaign107.FACTOR_NAME
    assert (
        effective["overlay"]["exact_binding_correction"]["only_base_literal_corrected"]
        is True
    )
    assert len(comparisons) == 132
    assert (
        campaign107._order_digest(comparisons)
        == campaign107.NUMERIC_COMPARATOR_ORDER_SHA256
    )
    assert len(definitions) == 136
    assert (
        campaign107._order_digest(definitions)
        == campaign107.COMPLETE_DEFINITION_ORDER_SHA256
    )
    assert definitions[-1] == {
        "name": "intraday_nonzero_range_bar_share_240m",
        "score_direction": "higher",
    }
    status = campaign107.status()
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_constant_and_all_distinct_paths_are_exact_endpoints() -> None:
    constant, quality = _score(np.full(240, 10.0, dtype=np.float64))
    assert constant == 0.0
    assert quality["exact_close_repeated_unordered_pairs"] == 28_680
    distinct, quality = _score(10.0 + np.arange(240, dtype=np.float64) / 1000.0)
    assert distinct == 1.0
    assert quality["exact_close_distinct_levels"] == 240
    assert quality["exact_close_repeated_unordered_pairs"] == 0


def test_exact_collision_count_and_clock_order_invariance() -> None:
    closes = np.concatenate(
        [
            np.full(100, 10.0),
            np.full(80, 10.1),
            np.full(60, 10.2),
        ]
    )
    repeated = 100 * 99 // 2 + 80 * 79 // 2 + 60 * 59 // 2
    expected = 1.0 - repeated / 28_680
    score, quality = _score(closes)
    assert score == pytest.approx(expected, abs=1e-15)
    assert quality["exact_close_repeated_unordered_pairs"] == repeated
    score_reversed, _ = _score(closes[::-1])
    assert score_reversed == pytest.approx(expected, abs=1e-15)


def test_numeric_equality_is_exact_without_rounding_or_tolerance() -> None:
    closes = np.full(240, 10.0, dtype=np.float64)
    closes[120:] = np.nextafter(10.0, np.inf)
    repeated = 2 * (120 * 119 // 2)
    score, quality = _score(closes)
    assert score == pytest.approx(1.0 - repeated / 28_680, abs=1e-15)
    assert quality["exact_close_distinct_levels"] == 2


def test_invalid_selected_close_fails_closed_but_0930_is_unused() -> None:
    closes = 10.0 + np.arange(240, dtype=np.float64) / 1000.0
    nonpositive = closes.copy()
    nonpositive[4] = 0.0
    frame, quality = campaign107.extract_exact_close_level_diversity(
        _raw(nonpositive), symbol="000001.SZ"
    )
    assert frame["exact_close_level_diversity"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1

    nonfinite = closes.copy()
    nonfinite[4] = np.nan
    frame, quality = campaign107.extract_exact_close_level_diversity(
        _raw(nonfinite), symbol="000001.SZ"
    )
    assert frame["exact_close_level_diversity"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1
    score, _ = _score(closes, opening_close=0.0)
    assert score == 1.0


def test_grid_and_discrete_output_semantics_fail_closed() -> None:
    raw = _raw(10.0 + np.arange(240, dtype=np.float64) / 1000.0).iloc[:-1]
    with pytest.raises(campaign107.Campaign107FeatureError):
        campaign107.extract_exact_close_level_diversity(raw, symbol="000001.SZ")
    assert campaign107.validate_value_semantics(campaign107.empty_output_frame()) == (
        0,
        0,
    )
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign107.FACTOR_NAME: [0.101],
            f"{campaign107.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign107.OUTPUT_COLUMNS]
    with pytest.raises(campaign107.Campaign107FeatureError):
        campaign107.validate_value_semantics(bad)


def test_build_requires_explicit_confirmation_before_source_access() -> None:
    with pytest.raises(campaign107.Campaign107FeatureError, match="confirm-build"):
        campaign107.build_snapshot(
            data_root=campaign107.DEFAULT_DATA_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_extractor_uses_only_frozen_close_projection() -> None:
    source = inspect.getsource(campaign107.extract_exact_close_level_diversity)
    for forbidden in ("open", "high", "low", "volume", "amount", "forward_return"):
        assert f'["{forbidden}"]' not in source


def test_implementation_freeze_is_live() -> None:
    freeze = campaign107._validate_implementation_freeze()
    assert freeze["numeric_comparator_count"] == 132
    assert freeze["complete_definition_count"] == 136
    assert (
        freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    )
