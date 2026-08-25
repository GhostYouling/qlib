from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign286_design as base
from scripts import (
    a_share_three_day_walkforward_campaign286_design_recovery as recovery,
)


def _key(day: str, security: int) -> int:
    value = pd.Timestamp(day).to_datetime64().astype("datetime64[D]").astype(int)
    return int(value) * 4_000_000 + security


def test_recovery_partition_sets_are_disjoint_and_complete() -> None:
    reused = set(recovery.SOURCE_PARTITIONS)
    recomputed = set(recovery.RECOVERY_YEARS)

    assert reused == {2019, 2020}
    assert recomputed == {2021, 2022, 2023}
    assert reused.isdisjoint(recomputed)
    assert reused | recomputed == set(base.DEVELOPMENT_YEARS)


def test_external_configuration_changes_only_data_paths() -> None:
    protocol = base.PROTOCOL_PATH
    loader = base.LOADER_PATH
    recovery.configure_external_data()

    assert base.PROVIDER_URI == recovery.SOURCE_REPO / "data/qlib/cn_a_share"
    assert base.QUALITY_PATH == (
        recovery.SOURCE_REPO / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
    )
    assert base.PROTOCOL_PATH == protocol
    assert base.LOADER_PATH == loader


def test_daily_counts_decodes_compact_keys(tmp_path: Path) -> None:
    path = tmp_path / "partition.parquet"
    frame = pd.DataFrame(
        {
            "stock_day_key": [
                _key("2020-01-02", 1_000_001),
                _key("2020-01-02", 1_000_002),
                _key("2020-01-03", 1_000_001),
            ],
            "quality_listing_eligible": [True, True, False],
            "model_support_eligible": [True, False, False],
        }
    )
    frame.to_parquet(path, index=False)

    daily = recovery.daily_counts(path)

    assert daily["session"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-01-02",
        "2020-01-03",
    ]
    assert daily["quality_listing_names"].tolist() == [2, 0]
    assert daily["eligible_names"].tolist() == [1, 0]


def test_frozen_source_partition_receipts_exist() -> None:
    for year, expected in recovery.SOURCE_PARTITIONS.items():
        path = recovery.source_partition(year)

        assert path.stat().st_size == expected["bytes"]
        assert base.file_sha256(path) == expected["sha256"]
