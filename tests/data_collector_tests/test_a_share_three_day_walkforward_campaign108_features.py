from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign108_features as campaign108


def _raw(
    closes: np.ndarray,
    *,
    opening_close: float = 1.0,
) -> pd.DataFrame:
    values = {
        code: float(value)
        for code, value in zip(campaign108.CONTINUOUS_MINUTE_CODES, closes, strict=True)
    }
    values[9 * 60 + 30] = opening_close
    rows = []
    for code in sorted(campaign108.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "close": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign108.RAW_COLUMNS]


def _score(closes: np.ndarray, **kwargs: float) -> tuple[float, dict[str, int]]:
    frame, quality = campaign108.extract_continuous_session_net_return_reversal(
        _raw(closes, **kwargs), symbol="000001.SZ"
    )
    return float(frame.loc[0, "continuous_session_net_return_reversal"]), quality


def test_protocol_and_v67_orders_are_prevalue_safe() -> None:
    spec = campaign108.load_protocol()
    comparisons = campaign108.reconstruct_comparisons()
    definitions = campaign108.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == campaign108.FACTOR_NAME
    assert len(comparisons) == 132
    assert (
        campaign108._order_digest(comparisons)
        == campaign108.NUMERIC_COMPARATOR_ORDER_SHA256
    )
    assert len(definitions) == 137
    assert (
        campaign108._order_digest(definitions)
        == campaign108.COMPLETE_DEFINITION_ORDER_SHA256
    )
    assert definitions[-1] == {
        "name": "intraday_exact_close_level_diversity_240m",
        "score_direction": "higher",
    }
    status = campaign108.status()
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_zero_positive_and_negative_endpoint_returns_have_frozen_direction() -> None:
    closes = np.full(240, 10.0, dtype=np.float64)
    zero, quality = _score(closes)
    assert zero == 0.0
    assert quality["zero_endpoint_returns"] == 1

    higher = closes.copy()
    higher[-1] = 11.0
    score, _ = _score(higher)
    assert score == pytest.approx(-np.tanh(np.log(1.1)), abs=1e-15)
    assert score < 0.0

    lower = closes.copy()
    lower[-1] = 9.0
    score, quality = _score(lower)
    assert score == pytest.approx(-np.tanh(np.log(0.9)), abs=1e-15)
    assert score > 0.0
    assert quality["positive_reversal_scores"] == 1


def test_intermediate_path_and_0930_are_unused_after_grid_validation() -> None:
    baseline = np.full(240, 10.0, dtype=np.float64)
    baseline[-1] = 9.5
    expected, _ = _score(baseline)
    changed = np.linspace(1.0, 1000.0, 240, dtype=np.float64)
    changed[0] = 10.0
    changed[-1] = 9.5
    observed, _ = _score(changed, opening_close=0.0)
    assert observed == pytest.approx(expected, abs=1e-15)
    changed[100] = np.nan
    observed, quality = _score(changed)
    assert observed == pytest.approx(expected, abs=1e-15)
    assert quality["valid_endpoint_sessions"] == 1


def test_invalid_endpoint_values_fail_closed() -> None:
    closes = np.full(240, 10.0, dtype=np.float64)
    for value in (0.0, np.nan, np.inf):
        invalid = closes.copy()
        invalid[-1] = value
        frame, quality = campaign108.extract_continuous_session_net_return_reversal(
            _raw(invalid), symbol="000001.SZ"
        )
        assert frame["continuous_session_net_return_reversal"].isna().all()
        assert quality["invalid_numeric_sessions"] == 1


def test_grid_and_output_semantics_fail_closed() -> None:
    raw = _raw(np.full(240, 10.0, dtype=np.float64)).iloc[:-1]
    with pytest.raises(campaign108.Campaign108FeatureError):
        campaign108.extract_continuous_session_net_return_reversal(
            raw, symbol="000001.SZ"
        )
    assert campaign108.validate_value_semantics(campaign108.empty_output_frame()) == (
        0,
        0,
    )
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign108.FACTOR_NAME: [1.1],
            f"{campaign108.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign108.OUTPUT_COLUMNS]
    with pytest.raises(campaign108.Campaign108FeatureError):
        campaign108.validate_value_semantics(bad)


def test_build_requires_explicit_confirmation_before_source_access() -> None:
    with pytest.raises(campaign108.Campaign108FeatureError, match="confirm-build"):
        campaign108.build_snapshot(
            data_root=campaign108.DEFAULT_DATA_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_extractor_uses_only_frozen_close_projection() -> None:
    source = inspect.getsource(
        campaign108.extract_continuous_session_net_return_reversal
    )
    for forbidden in ("open", "high", "low", "volume", "amount", "forward_return"):
        assert f'["{forbidden}"]' not in source


def test_implementation_freeze_is_live() -> None:
    freeze = campaign108._validate_implementation_freeze()
    assert freeze["numeric_comparator_count"] == 132
    assert freeze["complete_definition_count"] == 137
    assert (
        freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    )
