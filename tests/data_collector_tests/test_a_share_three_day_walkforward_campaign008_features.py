import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign008_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _paths(
    *,
    response_multiplier: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    morning_shocks = np.linspace(0.001, 0.02, 118)
    afternoon_shocks = np.linspace(0.019, 0.002, 118)

    def half(
        shocks: np.ndarray,
        close_base: float,
        volume_base: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        close_returns = np.concatenate([shocks, np.array([0.003])])
        log_closes = np.concatenate(
            [
                np.array([close_base]),
                close_base + np.cumsum(close_returns),
            ]
        )
        response = response_multiplier * shocks
        log_volumes = np.concatenate(
            [
                np.array([volume_base, volume_base]),
                volume_base + np.cumsum(response),
            ]
        )
        assert len(log_closes) == 120
        assert len(log_volumes) == 120
        return np.exp(log_closes), np.exp(log_volumes)

    morning_close, morning_volume = half(morning_shocks, 4.0, 8.0)
    afternoon_close, afternoon_volume = half(afternoon_shocks, 4.2, 8.2)
    return (
        np.concatenate([morning_close, afternoon_close]),
        np.concatenate([morning_volume, afternoon_volume]),
    )


def test_positive_and_negative_post_shock_response_formula() -> None:
    positive_close, positive_volume = _paths(response_multiplier=0.5)
    negative_close, negative_volume = _paths(response_multiplier=-0.5)
    values, eligible, quality = FEATURES.compute_factor_values(
        closes=np.vstack([positive_close, negative_close]),
        volumes=np.vstack([positive_volume, negative_volume]),
    )
    observed = values[FEATURES.FACTOR_NAME]
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert observed[0] == pytest.approx(1.0)
    assert observed[1] == pytest.approx(-1.0)
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_response_is_strictly_after_the_price_shock() -> None:
    closes, volumes = _paths(response_multiplier=0.5)
    values, eligible, _ = FEATURES.compute_factor_values(
        closes=closes.reshape(1, -1),
        volumes=volumes.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(1.0)
    shifted = np.concatenate([volumes[:1], volumes[:-1]])
    shifted_values, shifted_eligible, _ = FEATURES.compute_factor_values(
        closes=closes.reshape(1, -1),
        volumes=shifted.reshape(1, -1),
    )
    assert shifted_eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert shifted_values[FEATURES.FACTOR_NAME][0] < 0.999


def test_zero_response_semantics_fail_closed() -> None:
    closes, volumes = _paths(response_multiplier=0.5)
    one_sided = volumes.copy()
    one_sided[20] = 0.0
    sparse = volumes.copy()
    sparse[1:120] = 0.0
    values, eligible, quality = FEATURES.compute_factor_values(
        closes=np.vstack([closes, closes]),
        volumes=np.vstack([one_sided, sparse]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__one_sided_zero_response_rows"]
        == 1
    )
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__fewer_than_120_pairs_rows"]
        == 1
    )


def test_constant_shock_or_response_is_ineligible() -> None:
    closes, volumes = _paths(response_multiplier=0.5)
    constant_close = np.full(240, 100.0)
    constant_growth = np.exp(8.0 + 0.001 * np.arange(240))
    values, eligible, quality = FEATURES.compute_factor_values(
        closes=np.vstack([constant_close, closes]),
        volumes=np.vstack([volumes, constant_growth]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__constant_absolute_shock_rows"]
        == 1
    )
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__constant_volume_growth_rows"]
        == 1
    )


def test_invalid_shapes_and_values_are_rejected_or_ineligible() -> None:
    with pytest.raises(FEATURES.Campaign008FeatureError):
        FEATURES.compute_factor_values(
            closes=np.ones((1, 239)),
            volumes=np.ones((1, 239)),
        )
    closes, volumes = _paths(response_multiplier=0.5)
    closes[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        closes=closes.reshape(1, -1),
        volumes=volumes.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_close_rows"] == 1


def test_partition_reads_no_amount_and_excludes_0930() -> None:
    closes, volumes = _paths(response_multiplier=0.5)
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamp = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamp,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.concatenate([[-1.0], closes]),
            "volume": np.concatenate([[-1.0], volumes]),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["base_rows"] == 1
    assert "amount" not in FEATURES.RAW_COLUMNS


def test_empty_joint_base_returns_an_empty_partition() -> None:
    raw = pd.DataFrame(
        {
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            "close": pd.Series(dtype="float64"),
            "volume": pd.Series(dtype="float64"),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600145",
    )
    assert frame.empty
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert quality == {"base_rows": 0}


def test_source_contract_records_no_values_or_returns() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_008_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_008_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["maximum_possible_pairs"] == 236
    assert audit["comparison_catalog"]["comparison_count"] == 31
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "high",
        "low",
        "amount",
    ]


def test_protocol_is_hash_bound_before_external_values() -> None:
    assert (
        FEATURES.PROTOCOL_SHA256
        == "1c209a1611d822531efe178793c80e5a8f68f5752ae5a0dfa890585e62dfcf56"
    )
    spec = FEATURES.load_protocol()
    assert spec["candidates"][0]["name"] == FEATURES.FACTOR_NAME
    assert spec["research_boundary"]["minute_close_field_read_before_admissibility"]
    assert (
        spec["research_boundary"]["minute_amount_field_read_before_admissibility"]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
