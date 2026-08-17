from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign099 as campaign


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_099_preregistration.json"
)


def test_frozen_runner_identity_and_compact_manifest() -> None:
    assert campaign.ADMITTED_FACTOR == (
        "intraday_market_close_location_profile_synchronization_240m"
    )
    assert campaign.FROZEN_TRIAL_ID == (
        "wf099_intraday_market_close_location_profile_synchronization_240m_single_higher"
    )
    assert campaign.CANDIDATE_MANIFEST == campaign.COMPACT_MANIFEST
    assert campaign.CANDIDATE_MANIFEST_SHA256 == campaign.COMPACT_MANIFEST_SHA256
    assert campaign.CANDIDATE_DATASET_SHA256 == campaign.COMPACT_DATASET_SHA256
    assert campaign.EXPECTED_ROWS == 1_331_759
    assert campaign.EXPECTED_ELIGIBLE_ROWS == 1_328_449


def test_stock_day_key_decoder_round_trip() -> None:
    days = np.array([17897, 17898, 17899], dtype=np.int64)
    securities = np.array([1_600000, 2_000001, 3_430047], dtype=np.int64)
    dates, instruments = campaign._decode_stock_day_keys(days * 4_000_000 + securities)
    assert dates.equals(pd.DatetimeIndex(pd.to_datetime(days, unit="D", origin="unix")))
    assert instruments.tolist() == ["SH600000", "SZ000001", "BJ430047"]


def test_preregistration_and_single_trial_catalog() -> None:
    effective, digest = campaign.load_campaign(PREREGISTRATION)
    assert len(digest) == 64
    trials = campaign.build_trial_catalog(effective)
    assert len(trials) == 1
    assert trials[0]["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert trials[0]["feature_set"] == [campaign.ADMITTED_FACTOR]
    assert trials[0]["weights"] == [1.0]


def test_compact_factor_loader_is_scoped_and_restored() -> None:
    original = campaign.base.load_factor_panel
    with campaign._temporary_compact_factor_loader():
        assert campaign.base.load_factor_panel is campaign._load_compact_factor_panel
    assert campaign.base.load_factor_panel is original
