from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign067_features as feature


ROOT = Path(__file__).resolve().parents[2]


def test_campaign067_protocol_and_complete_comparator_order_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons(spec)

    assert len(comparisons) == 97
    assert feature._comparison_order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "quarterly_quality_rank_balance_3f",
        "score_direction": "higher",
    }
    unique = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert unique["complete_definition_count"] == 98
    assert unique["complete_definition_order_sha256"] == feature.FULL_DEFINITION_ORDER_SHA256
    assert unique["all_97_numeric_comparators_must_pass"] is True


def test_campaign067_rank_gap_formula_and_missing_semantics() -> None:
    values, eligible = feature.compute_gap_values(
        np.array(
            [
                [1.0, 0.25],
                [0.20, 0.80],
                [0.50, 0.50],
                [np.nan, 0.40],
            ]
        )
    )

    assert eligible.tolist() == [True, True, True, False]
    np.testing.assert_allclose(values[:3], [0.75, -0.60, 0.0])
    assert np.isnan(values[3])


def test_campaign067_year_rank_uses_average_ties_for_both_fields() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * 4),
            "symbol": ["SH600000", "SZ000001", "SZ000002", "SZ000003"],
            "provider": ["tushare"] * 4,
            "roe": [10.0, 10.0, 20.0, np.nan],
            "net_profit": [100.0, 200.0, 200.0, 300.0],
        }
    )

    result = feature.rank_and_balance_year_frame(frame)

    expected_roe = np.array([0.5, 0.5, 1.0, np.nan])
    expected_profit = np.array([0.25, 0.625, 0.625, 1.0])
    np.testing.assert_allclose(
        result[feature.FACTOR_NAME].to_numpy()[:3],
        expected_roe[:3] - expected_profit[:3],
    )
    assert result[f"{feature.FACTOR_NAME}_eligible"].tolist() == [True, True, True, False]


def test_campaign067_freeze_binds_runner_and_reads_no_return() -> None:
    freeze = json.loads(
        (ROOT / "docs/a_share_three_day_walkforward_campaign_067_feature_implementation_freeze_v2_20260805.json").read_text()
    )
    assert freeze["feature_runner"]["sha256"] == feature._sha256(Path(feature.__file__))
    assert freeze["pre_value_checks"]["historical_daily_price_fields_read"] == []
    assert freeze["pre_value_checks"]["historical_forward_return_fields_read"] is False
    assert freeze["pre_value_checks"]["provider_request_issued"] is False


def test_campaign067_status_is_read_only_before_build() -> None:
    payload = feature.status()
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
