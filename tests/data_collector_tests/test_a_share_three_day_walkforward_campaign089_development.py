from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign089 as campaign

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_089/walkforward"
)
PREREGISTRATION_SHA256 = (
    "e33f3e65429e67e365e67ef1adb7cf124aa111ce94be5fd4ca0e837f2895854d"
)


def test_preregistration_bindings_and_single_trial_catalog() -> None:
    report = bindings.validate_record(campaign.DEFAULT_PREREGISTRATION)
    assert report["all_bindings_passed"] is True
    assert report["record_sha256"] == PREREGISTRATION_SHA256
    effective, digest = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert digest == report["record_sha256"]
    assert campaign.build_trial_catalog(effective) == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.ADMITTED_FACTOR],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_compact_identity_decoder_uses_unix_day_and_exchange_code() -> None:
    day = int(np.datetime64("2019-01-02", "D").astype(np.int64))
    keys = np.array(
        [
            day * 4_000_000 + 1_600_000,
            day * 4_000_000 + 2_000_001,
            day * 4_000_000 + 3_430_001,
        ],
        dtype=np.int64,
    )
    dates, instruments = campaign._decode_stock_day_keys(keys)
    assert [value.strftime("%Y-%m-%d") for value in dates] == [
        "2019-01-02",
        "2019-01-02",
        "2019-01-02",
    ]
    assert instruments.tolist() == ["SH600000", "SZ000001", "BJ430001"]


def test_compact_factor_loader_binding_is_scoped_and_restored() -> None:
    original = campaign.base.load_factor_panel
    with campaign._temporary_compact_factor_loader():
        assert campaign.base.load_factor_panel is campaign._load_compact_factor_panel
    assert campaign.base.load_factor_panel is original


def test_prevalue_status_and_boundaries_remain_closed() -> None:
    result = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(OUTPUT_ROOT),
        )
    )
    assert result["campaign_id"] == "a_share_three_day_walkforward_campaign_089"
    assert result["expected_trial_count"] == 1
    assert result["ledger_entry_count"] == 0
    assert result["stress_intent_exists"] is False
    assert result["stress_record_exists"] is False
    assert result["candidate49_historical_return_read"] is False
    assert result["current_scoring_selection_sizing_or_orders_allowed"] is False

    spec = json.loads(campaign.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
    audit_path = ROOT / spec["no_return_bindings"]["audit"]["path"]
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == (
        "completed_with_one_admissible_factor_pending_walkforward_preregistration"
    )
    assert audit["historical_forward_return_fields_read"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["orders_allowed"] is False
