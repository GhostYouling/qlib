"""Tests for Campaign094's metadata-only v3 activation repair."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import a_share_three_day_walkforward_campaign094_features as v1
from scripts import a_share_three_day_walkforward_campaign094_features_v2 as v2
from scripts import a_share_three_day_walkforward_campaign094_features_v3 as v3


def test_frozen_v2_and_v3_repair_inputs_are_immutable() -> None:
    assert v3._sha256(Path(v2.__file__).resolve()) == v3.V2_RUNNER_SHA256
    assert v3._sha256(v3.V2_FREEZE) == v3.V2_FREEZE_SHA256
    assert v3._sha256(v3.V2_FAILURE) == v3.V2_FAILURE_SHA256
    assert v3._sha256(v3.REPAIR_PROTOCOL) == v3.REPAIR_PROTOCOL_SHA256
    assert v3._sha256(v3.PREACTIVATION_MANIFEST) == v3.PREACTIVATION_MANIFEST_SHA256


def test_quality_normalization_is_one_exact_rename() -> None:
    before = {
        "source_rows": 10,
        "valid_range_local_peak_clock_dispersion_sessions": 8,
        "zero_destination_range_pairs": 7,
    }
    after = v3._normalized_quality(before)
    assert before["zero_destination_range_pairs"] == 7
    assert after == {
        "source_rows": 10,
        "valid_range_local_peak_clock_dispersion_sessions": 8,
        "zero_range_bars": 7,
    }


def test_activation_requires_explicit_confirmation() -> None:
    with pytest.raises(v3.Campaign094FeatureV3Error, match="confirm-activate"):
        v3.activate_manifest()


def test_v3_status_is_read_only_and_preactivation_manifest_is_exact() -> None:
    report = v3.status()
    assert report["status"] == "verified_v1_snapshot_awaiting_v3_activation"
    assert report["partition_or_factor_values_mutated_by_status"] is False
    assert report["comparison_values_read_by_status"] is False
    assert (
        report["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert report["provider_request_issued_by_status"] is False


def test_factor_and_partition_contract_remains_v1() -> None:
    assert v1.FACTOR_NAME == "intraday_range_local_peak_clock_dispersion_236p"
    assert v1.MAXIMUM_SCORE == 0.25
    assert v2.EXPECTED_ROWS == 1_331_759
    assert v2.EXPECTED_PARTITIONS == 7
    assert v2.EXPECTED_SESSIONS == 1_632
