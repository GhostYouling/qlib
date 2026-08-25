from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign293 as campaign


ROOT = Path(__file__).resolve().parents[2]


def _matrix(*, complete_families: int) -> tuple[np.ndarray, np.ndarray]:
    feature_names = json.loads(
        campaign.ALPHA158_MANIFEST_PATH.read_text(encoding="utf-8")
    )["feature_names"]
    groups = campaign.family_indices(feature_names)
    matrix = np.full((4, campaign.FEATURE_COUNT), np.nan, dtype=np.float32)
    matrix[:, :13] = np.arange(4, dtype=np.float32)[:, None]
    for group in groups[:complete_families]:
        matrix[:, group] = np.arange(4, dtype=np.float32)[:, None]
    if complete_families < campaign.MINIMUM_COMPLETE_FAMILIES:
        needed = campaign.MINIMUM_ALPHA158_FINITE_FEATURES - int(
            np.isfinite(matrix[0]).sum()
        )
        if needed > 0:
            matrix[:, groups[complete_families, :needed]] = np.arange(
                4, dtype=np.float32
            )[:, None]
    return matrix, groups


def _score(matrix: np.ndarray, groups: np.ndarray):
    observed = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
    support = observed >= campaign.MINIMUM_ALPHA158_FINITE_FEATURES
    return campaign.session_peer_rank_smoothness(
        keys=np.arange(1, len(matrix) + 1, dtype=np.int64),
        matrix=matrix,
        finite_count=observed,
        feature_support=support,
        quality_listing=np.ones(len(matrix), dtype=bool),
        model_support=support.copy(),
        groups=groups,
    )


def test_family_inventory_is_exact_and_disjoint() -> None:
    manifest = json.loads(
        campaign.ALPHA158_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    indices = campaign.family_indices(manifest["feature_names"])
    assert indices.shape == (29, 5)
    assert len(np.unique(indices)) == 145
    assert min(indices.ravel()) == 13
    assert max(indices.ravel()) == 157


def test_identical_peer_rank_term_structures_score_one() -> None:
    matrix, groups = _matrix(complete_families=22)
    frame = _score(matrix, groups)
    eligible = frame[f"{campaign.FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
    assert eligible.all()
    assert np.allclose(frame[campaign.FACTOR_NAME], 1.0)
    assert frame["complete_horizon_family_count"].tolist() == [22] * 4


def test_fewer_than_22_complete_families_is_ineligible() -> None:
    matrix, groups = _matrix(complete_families=21)
    assert np.isfinite(matrix[0]).sum() >= 119
    frame = _score(matrix, groups)
    assert frame["complete_horizon_family_count"].tolist() == [21] * 4
    assert not frame[f"{campaign.FACTOR_NAME}_eligible"].any()
    assert frame[campaign.FACTOR_NAME].isna().all()


def test_smoothness_responds_to_adjacent_horizon_rank_disagreement() -> None:
    matrix, groups = _matrix(complete_families=22)
    target = groups[0]
    matrix[:, target[1]] = matrix[::-1, target[1]]
    frame = _score(matrix, groups)
    values = frame[campaign.FACTOR_NAME].to_numpy(dtype=float)
    assert np.isfinite(values).all()
    assert (values < 1.0).all()
    assert (values >= 0.0).all()


def test_support_semantics_fail_closed() -> None:
    matrix, groups = _matrix(complete_families=22)
    observed = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
    with pytest.raises(campaign.Campaign293Error):
        campaign.session_peer_rank_smoothness(
            keys=np.arange(1, 5, dtype=np.int64),
            matrix=matrix,
            finite_count=observed,
            feature_support=np.zeros(4, dtype=bool),
            quality_listing=np.ones(4, dtype=bool),
            model_support=np.ones(4, dtype=bool),
            groups=groups,
        )


def test_protocol_and_candidate49_bindings_are_frozen() -> None:
    protocol, alpha, numeric = campaign.validate_protocol()
    assert protocol["ordered_numeric_uniqueness"]["comparator_count"] == 146
    assert len(alpha["feature_names"]) == 158
    assert len(numeric["feature_names"]) == 140
    assert campaign.file_sha256(campaign.SIGNAL_LEDGER_PATH) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign.file_sha256(campaign.EXECUTION_LEDGER_PATH) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_plan_is_metadata_only_after_implementation_freeze() -> None:
    result = campaign.plan()
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
    assert result["credential_loaded"] is False
    assert result["candidate49_ledgers_changed"] is False
