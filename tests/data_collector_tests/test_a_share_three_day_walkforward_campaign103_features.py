from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign103_features as features


def test_breadth_votes_improvement_tie_and_deterioration_equally() -> None:
    prior = np.full((1, 130), 0.5, dtype=np.float32)
    current = prior.copy()
    current[0, :40] = 0.6
    current[0, 40:70] = 0.4
    values, paired, eligible = features.improvement_breadth(
        current,
        prior,
        np.array([True]),
        np.array([True]),
    )
    assert paired.tolist() == [130]
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx((40 + 60 * 0.5) / 130)


def test_paired_floor_is_exact_inclusion_exclusion_boundary() -> None:
    current = np.full((2, 130), np.nan, dtype=np.float32)
    prior = np.full((2, 130), np.nan, dtype=np.float32)
    current[:, :98] = 0.6
    prior[:, 32:] = 0.4  # exact overlap is 66
    values, paired, eligible = features.improvement_breadth(
        current,
        prior,
        np.array([True, True]),
        np.array([True, False]),
    )
    assert paired.tolist() == [66, 66]
    assert eligible.tolist() == [True, False]
    assert values[0] == 1.0
    assert np.isnan(values[1])


def test_missing_pair_is_omitted_and_not_a_zero_vote() -> None:
    current = np.full((1, 130), 0.5, dtype=np.float32)
    prior = np.full((1, 130), 0.5, dtype=np.float32)
    current[0, 0] = np.nan
    current[0, 1] = 0.75
    values, paired, eligible = features.improvement_breadth(
        current,
        prior,
        np.array([True]),
        np.array([True]),
    )
    assert paired.tolist() == [129]
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx((1.0 + 128 * 0.5) / 129)


def test_invalid_directional_component_fails_closed() -> None:
    current = np.full((1, 130), 0.5, dtype=np.float32)
    prior = current.copy()
    current[0, 9] = 0.0
    with pytest.raises(features.Campaign103FeatureError, match="escaped"):
        features.improvement_breadth(
            current,
            prior,
            np.array([True]),
            np.array([True]),
        )


def test_protocol_freezes_one_trial_and_all_130_comparisons() -> None:
    protocol = json.loads(features.DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["candidate"]["name"] == features.FACTOR_NAME
    assert protocol["candidate"]["minimum_paired_components"] == 66
    assert protocol["finite_development_catalog_if_admitted"]["trial_count"] == 1
    assert protocol["ordered_no_return_gates"][2]["name"] == "all_130_numeric_uniqueness"
    assert protocol["research_boundary"]["historical_forward_return_fields_read_before_freeze"] is False


def test_source_catalog_matches_bound_campaign102_receipts() -> None:
    _, catalog, manifest = features.load_frozen_inputs()
    observed = catalog["partition_receipts"]
    expected = [
        {"year": int(item["year"]), "rows": int(item["rows"]), "sha256": item["sha256"]}
        for item in manifest["files"]
    ]
    assert observed == expected


def test_comparison_loader_fails_before_coverage_pass(tmp_path) -> None:
    with pytest.raises(features.Campaign103FeatureError, match="before coverage"):
        features.uniqueness_after_coverage(
            candidate_manifest_path=tmp_path / "absent.json",
            coverage={"gate_passed_before_comparison_values": False},
        )


def test_status_reads_no_candidate_comparison_price_or_return_values(tmp_path) -> None:
    payload = features.status(data_root=tmp_path)
    assert payload["campaign103_candidate_or_paired_support_values_read_by_status"] is False
    assert payload["campaign103_comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
