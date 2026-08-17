from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign101_features as campaign101


def test_directional_percentile_uses_full_session_and_average_ties() -> None:
    values = np.array([1.0, 2.0, 2.0, np.nan, 10.0, 20.0], dtype=float)
    sessions = np.array([1, 1, 1, 1, 2, 2], dtype=np.int64)

    higher = campaign101._directional_percentile(values, sessions, "higher")
    lower = campaign101._directional_percentile(values, sessions, "lower")

    np.testing.assert_allclose(higher[:3], [1 / 3, 5 / 6, 5 / 6])
    np.testing.assert_allclose(lower[:3], [1.0, 0.5, 0.5])
    assert np.isnan(higher[3]) and np.isnan(lower[3])
    np.testing.assert_allclose(higher[4:], [0.5, 1.0])
    np.testing.assert_allclose(lower[4:], [1.0, 0.5])


def test_lower_quartile_consensus_is_exact_33rd_value_after_zero_imputation() -> None:
    row = np.linspace(0.01, 1.0, campaign101.NUMERIC_COUNT)
    row[: campaign101.MAXIMUM_MISSING_COMPONENTS] = np.nan
    expected = np.sort(np.where(np.isfinite(row), row, 0.0))[
        campaign101.ORDER_STATISTIC_INDEX
    ]

    values, eligible, count = campaign101._lower_quartile_consensus(row[None, :])

    assert eligible.tolist() == [True]
    assert count.tolist() == [campaign101.MINIMUM_FINITE_COMPONENTS]
    assert values.tolist() == [expected]
    assert expected > 0.0


def test_lower_quartile_consensus_fails_row_with_33_missing_components() -> None:
    row = np.linspace(0.01, 1.0, campaign101.NUMERIC_COUNT)
    row[: campaign101.MAXIMUM_MISSING_COMPONENTS + 1] = np.nan

    values, eligible, count = campaign101._lower_quartile_consensus(row[None, :])

    assert eligible.tolist() == [False]
    assert count.tolist() == [campaign101.MINIMUM_FINITE_COMPONENTS - 1]
    assert np.isnan(values[0])


def test_lower_quartile_consensus_rejects_alternative_shapes_and_ranges() -> None:
    with pytest.raises(campaign101.Campaign101FeatureError):
        campaign101._lower_quartile_consensus(np.ones((2, 128)))
    bad = np.ones((1, campaign101.NUMERIC_COUNT))
    bad[0, 0] = 0.0
    with pytest.raises(campaign101.Campaign101FeatureError):
        campaign101._lower_quartile_consensus(bad)


def test_frozen_numeric_source_order_is_complete_and_excludes_candidate49() -> None:
    sources = campaign101.reconstruct_numeric_sources()

    assert len(sources) == campaign101.NUMERIC_COUNT
    assert campaign101._order_digest(sources) == campaign101.NUMERIC_ORDER_SHA256
    assert len({item["name"] for item in sources}) == campaign101.NUMERIC_COUNT
    assert "candidate49" not in " ".join(item["name"] for item in sources).lower()


def test_load_post_source_year_aligns_compact_source_to_base_keys(tmp_path) -> None:
    factor = "synthetic_factor"
    frame = pd.DataFrame(
        {
            "stock_day_key": np.array([20, 10], dtype=np.int64),
            factor: [2.0, 1.0],
        }
    )
    path = tmp_path / "2020.parquet"
    frame.to_parquet(path, index=False)
    manifest = {
        "files": [
            {"year": year, "path": str(path), "rows": 2} for year in range(2019, 2026)
        ]
    }

    values = campaign101._load_post_source_year(
        source={"name": factor},
        manifest=manifest,
        manifest_path=tmp_path / "snapshot_manifest.json",
        year=2020,
        base_keys=np.array([10, 20], dtype=np.int64),
    )

    np.testing.assert_array_equal(values, [1.0, 2.0])


def test_load_post_source_year_preserves_absent_component_as_nan(tmp_path) -> None:
    factor = "synthetic_factor"
    path = tmp_path / "2020.parquet"
    pd.DataFrame(
        {
            "stock_day_key": np.array([10, 30], dtype=np.int64),
            factor: [1.0, 3.0],
        }
    ).to_parquet(path, index=False)
    manifest = {
        "files": [
            {"year": year, "path": str(path), "rows": 2} for year in range(2019, 2026)
        ]
    }

    values = campaign101._load_post_source_year(
        source={"name": factor},
        manifest=manifest,
        manifest_path=tmp_path / "snapshot_manifest.json",
        year=2020,
        base_keys=np.array([10, 20, 30], dtype=np.int64),
    )

    np.testing.assert_allclose(values[[0, 2]], [1.0, 3.0])
    assert np.isnan(values[1])


def test_load_post_source_year_filters_and_aligns_legacy_source(tmp_path) -> None:
    factor = "synthetic_factor"
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-03", "2020-01-02", "2020-01-02"]),
            "symbol": ["SH600001", "SH600000", "SH600002"],
            factor: [3.0, 2.0, 99.0],
        }
    )
    path = tmp_path / "legacy.parquet"
    frame.to_parquet(path, index=False)
    selected = frame.iloc[:2]
    base_keys = np.sort(
        campaign101._compact_stock_day_keys(selected["trade_date"], selected["symbol"])
    )

    values = campaign101._load_post_source_year(
        source={"name": factor},
        manifest={"files": [{"year": 2020, "path": str(path), "rows": 3}]},
        manifest_path=tmp_path / "snapshot_manifest.json",
        year=2020,
        base_keys=base_keys,
    )

    np.testing.assert_array_equal(values, [2.0, 3.0])
