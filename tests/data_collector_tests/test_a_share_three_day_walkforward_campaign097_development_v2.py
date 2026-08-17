from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign097_v2 as repair


def test_v1_freeze_failure_and_compact_snapshot_are_immutable() -> None:
    assert repair._sha256(Path(repair.v1.__file__).resolve()) == repair.V1_RUNNER_SHA256
    assert (
        repair._sha256(repair.V1_DEVELOPMENT_FREEZE)
        == repair.V1_DEVELOPMENT_FREEZE_SHA256
    )
    assert repair._sha256(repair.FAILURE_RECORD) == repair.FAILURE_RECORD_SHA256
    assert (
        repair._sha256(repair.TEST_FAILURE_RECORD) == repair.TEST_FAILURE_RECORD_SHA256
    )
    assert repair._sha256(repair.COMPACT_MANIFEST) == repair.COMPACT_MANIFEST_SHA256


def test_repaired_loader_reads_frozen_2019_compact_panel() -> None:
    campaign, _ = repair.v1.load_campaign(repair.v1.DEFAULT_PREREGISTRATION)
    panel = repair._load_compact_factor_panel(
        campaign,
        [2019],
        pd.DatetimeIndex(["2019-01-02", "2019-01-03"]),
    )
    assert list(panel.columns) == [
        "trade_date",
        "instrument",
        repair.v1.ADMITTED_FACTOR,
    ]
    assert set(panel["trade_date"].dt.strftime("%Y-%m-%d")).issubset(
        {"2019-01-02", "2019-01-03"}
    )


def test_repaired_loader_patch_is_scoped_and_restored() -> None:
    namespace = repair.v1._generated
    original = namespace["_load_compact_factor_panel"]
    with repair._temporary_repaired_compact_loader():
        assert (
            namespace["_load_compact_factor_panel"] is repair._load_compact_factor_panel
        )
    assert namespace["_load_compact_factor_panel"] is original


def test_append_only_failure_entry_is_preserved() -> None:
    ledger = repair.v1.base.load_json(
        repair.REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_097/walkforward/trial_ledger.json"
    )
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0]["phase"] == "infrastructure_failure"
    assert ledger["entries"][0]["trial_id"] == (
        "wf097_infrastructure__development_load_001"
    )
