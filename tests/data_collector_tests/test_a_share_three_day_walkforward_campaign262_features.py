from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign262_features as features


def _raw(amount: np.ndarray | None = None) -> pd.DataFrame:
    minutes = [pd.Timestamp("2024-01-02 09:30")]
    minutes.extend(pd.date_range("2024-01-02 09:31", "2024-01-02 11:30", freq="min"))
    minutes.extend(pd.date_range("2024-01-02 13:01", "2024-01-02 15:00", freq="min"))
    values = np.arange(1.0, 242.0) if amount is None else amount
    return pd.DataFrame(
        {
            "datetime": minutes,
            "symbol": "SH600000",
            "provider": "tushare",
            "amount": values,
        }
    )


def _identity() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
        }
    )


def test_definition_and_comparator_orders_are_exact() -> None:
    assert len(features.reconstruct_prior_complete_definitions()) == 160
    assert len(features.reconstruct_complete_definitions()) == 161
    assert features.reconstruct_complete_definitions()[-1] == {
        "name": features.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(features.reconstruct_comparisons()) == 142


def test_protocol_binds_source_without_values() -> None:
    spec = features.load_protocol()
    assert spec["source_snapshot_contract"]["provider_request_allowed"] is False
    assert (
        spec["research_boundary"][
            "campaign262_candidate_values_computed_or_read_before_freeze"
        ]
        is False
    )


def test_extract_matches_pure_formula_and_excludes_0930() -> None:
    raw = _raw()
    values, quality = features.extract_amount_schedule_uniformity(
        raw, symbol="SH600000"
    )
    expected, _, _ = features.formula.compute_amount_schedule_uniformity(
        np.arange(2.0, 242.0)[None, :]
    )
    assert values.loc[0, features.FACTOR_SHORT_NAME] == pytest.approx(expected[0])
    changed = raw.copy()
    changed.loc[0, "amount"] = 1e15
    second, _ = features.extract_amount_schedule_uniformity(changed, symbol="SH600000")
    assert second.loc[0, features.FACTOR_SHORT_NAME] == pytest.approx(expected[0])
    assert quality["source_rows"] == 241
    assert quality["valid_schedule_sessions"] == 1
    assert quality["positive_amount_bars"] == 240
    assert quality["zero_amount_bars"] == 0


def test_temporal_relocation_changes_extracted_score() -> None:
    clustered = np.ones(241)
    clustered[1:25] = 100.0
    spread = np.ones(241)
    spread[1 + np.arange(0, 240, 10)] = 100.0
    first, _ = features.extract_amount_schedule_uniformity(
        _raw(clustered), symbol="SH600000"
    )
    second, _ = features.extract_amount_schedule_uniformity(
        _raw(spread), symbol="SH600000"
    )
    assert (
        second.loc[0, features.FACTOR_SHORT_NAME]
        > first.loc[0, features.FACTOR_SHORT_NAME]
    )


def test_invalid_or_nonpositive_amount_session_is_missing() -> None:
    for bad in (np.nan, -1.0):
        amount = np.arange(1.0, 242.0)
        amount[7] = bad
        values, quality = features.extract_amount_schedule_uniformity(
            _raw(amount), symbol="SH600000"
        )
        assert np.isnan(values.loc[0, features.FACTOR_SHORT_NAME])
        assert quality["valid_schedule_sessions"] == 0
    values, quality = features.extract_amount_schedule_uniformity(
        _raw(np.zeros(241)), symbol="SH600000"
    )
    assert np.isnan(values.loc[0, features.FACTOR_SHORT_NAME])
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_empty_partition_has_complete_zero_quality_diagnostics() -> None:
    values, quality = features.extract_amount_schedule_uniformity(
        _raw().iloc[0:0].copy(), symbol="SH600000"
    )
    assert values.empty
    assert quality["positive_amount_bars"] == 0
    assert quality["zero_amount_bars"] == 0


def test_attach_finalize_and_validate_semantics() -> None:
    values, _ = features.extract_amount_schedule_uniformity(_raw(), symbol="SH600000")
    attached = features.attach_schedule_values(_identity(), values, symbol="SH600000")
    finalized = features.finalize_feature_frame(attached)
    output = finalized.loc[:, features.OUTPUT_COLUMNS]
    assert features.validate_value_semantics(output) == (1, 1)


def test_wrong_projection_or_grid_fails_closed() -> None:
    with pytest.raises(features.Campaign262FeatureError):
        features.extract_amount_schedule_uniformity(
            _raw().drop(columns=["amount"]), symbol="SH600000"
        )
    with pytest.raises(features.Campaign262FeatureError):
        features.extract_amount_schedule_uniformity(
            _raw().iloc[:-1].copy(), symbol="SH600000"
        )
