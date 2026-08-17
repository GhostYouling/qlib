import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign007_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _paths(
    *,
    multiplier: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    morning = np.linspace(-0.02, 0.02, 119)
    afternoon = np.linspace(0.018, -0.022, 119)
    changes = np.concatenate([morning, afternoon])
    volume_log = np.concatenate(
        [
            np.array([8.0]),
            8.0 + np.cumsum(morning),
            np.array([8.2]),
            8.2 + np.cumsum(afternoon),
        ]
    )
    price_log = np.concatenate(
        [
            np.array([4.0]),
            4.0 + multiplier * np.cumsum(morning),
            np.array([4.1]),
            4.1 + multiplier * np.cumsum(afternoon),
        ]
    )
    volume = np.exp(volume_log)
    transaction_price = np.exp(price_log)
    amount = volume * transaction_price
    assert len(volume) == 240
    return volume, amount


def test_positive_and_negative_coupling_formula() -> None:
    positive_volume, positive_amount = _paths(multiplier=0.5)
    negative_volume, negative_amount = _paths(multiplier=-0.5)
    values, eligible, quality = FEATURES.compute_factor_values(
        volumes=np.vstack([positive_volume, negative_volume]),
        amounts=np.vstack([positive_amount, negative_amount]),
    )
    observed = values[FEATURES.FACTOR_NAME]
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert observed[0] == pytest.approx(1.0)
    assert observed[1] == pytest.approx(-1.0)
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_joint_zero_bars_are_inactive_but_one_sided_zero_is_fatal() -> None:
    volume, amount = _paths(multiplier=0.5)
    inactive_volume = volume.copy()
    inactive_amount = amount.copy()
    inactive_volume[10] = 0.0
    inactive_amount[10] = 0.0
    invalid_volume = volume.copy()
    invalid_amount = amount.copy()
    invalid_volume[20] = 0.0
    values, eligible, quality = FEATURES.compute_factor_values(
        volumes=np.vstack([inactive_volume, invalid_volume]),
        amounts=np.vstack([inactive_amount, invalid_amount]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isfinite(values[FEATURES.FACTOR_NAME][0])
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__one_sided_zero_activity_rows"
        ]
        == 1
    )


def test_minimum_pair_count_and_constant_vectors_are_fail_closed() -> None:
    volume, amount = _paths(multiplier=0.5)
    sparse_volume = volume.copy()
    sparse_amount = amount.copy()
    sparse_volume[61:180] = 0.0
    sparse_amount[61:180] = 0.0
    constant_volume = np.full(240, 100.0)
    transaction_price = np.exp(np.linspace(4.0, 4.2, 240))
    constant_amount = constant_volume * transaction_price
    values, eligible, quality = FEATURES.compute_factor_values(
        volumes=np.vstack([sparse_volume, constant_volume]),
        amounts=np.vstack([sparse_amount, constant_amount]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__fewer_than_120_pairs_rows"]
        == 1
    )
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__constant_volume_change_rows"
        ]
        == 1
    )


def test_invalid_shapes_and_values_are_rejected_or_ineligible() -> None:
    with pytest.raises(FEATURES.Campaign007FeatureError):
        FEATURES.compute_factor_values(
            volumes=np.ones((1, 239)),
            amounts=np.ones((1, 239)),
        )
    volume, amount = _paths(multiplier=0.5)
    volume[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        volumes=volume.reshape(1, -1),
        amounts=amount.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_volume_rows"] == 1


def test_partition_reads_no_close_and_excludes_0930() -> None:
    volume, amount = _paths(multiplier=0.5)
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
            "volume": np.concatenate([[0.0], volume]),
            "amount": np.concatenate([[0.0], amount]),
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
    assert "close" not in FEATURES.RAW_COLUMNS


def test_empty_joint_base_returns_an_empty_partition() -> None:
    raw = pd.DataFrame(
        {
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            "volume": pd.Series(dtype="float64"),
            "amount": pd.Series(dtype="float64"),
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
            / "docs/a_share_three_day_walkforward_campaign_007_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_007_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["comparison_catalog"]["comparison_count"] == 30
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "high",
        "low",
        "close",
    ]


def test_protocol_is_hash_bound_before_external_values() -> None:
    assert (
        FEATURES.PROTOCOL_SHA256
        == "308d5898c4a6d04b127c21876039ef7886d28b317951240fc29ba9ab2568a8ef"
    )
    spec = FEATURES.load_protocol()
    assert spec["candidates"][0]["name"] == FEATURES.FACTOR_NAME
    assert (
        spec["research_boundary"]["minute_close_field_read_before_admissibility"]
        is False
    )
