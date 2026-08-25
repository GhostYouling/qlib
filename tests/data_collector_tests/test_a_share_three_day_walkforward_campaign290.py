from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign290 as campaign


def _session_inputs() -> dict[str, np.ndarray]:
    matrix = np.tile(np.arange(campaign.FEATURE_COUNT, dtype=np.float32), (4, 1))
    matrix[0] -= 1.0
    matrix[1] += 0.0
    matrix[2] += 1.0
    matrix[3] += 2.0
    return {
        "keys": np.array([1_100_001, 1_100_002, 1_100_003, 1_100_004]),
        "matrix": matrix,
        "finite_count": np.full(4, campaign.FEATURE_COUNT, dtype=np.uint8),
        "feature_support": np.ones(4, dtype=bool),
        "quality_listing": np.ones(4, dtype=bool),
        "model_support": np.ones(4, dtype=bool),
    }


def test_session_state_persistence_exact_previous_and_equal_states() -> None:
    inputs = _session_inputs()
    first, states = campaign.session_state_persistence(
        **inputs, previous_states=None, exact_previous_session=False
    )
    assert first[f"{campaign.FACTOR_NAME}_eligible"].sum() == 0
    second, _ = campaign.session_state_persistence(
        **inputs, previous_states=states, exact_previous_session=True
    )
    assert second[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert np.allclose(second[campaign.FACTOR_NAME], 1.0)
    assert (second["paired_feature_count"] == campaign.FEATURE_COUNT).all()


def test_session_state_persistence_does_not_bridge_gap() -> None:
    inputs = _session_inputs()
    _, states = campaign.session_state_persistence(
        **inputs, previous_states=None, exact_previous_session=False
    )
    output, _ = campaign.session_state_persistence(
        **inputs, previous_states=states, exact_previous_session=False
    )
    assert output[f"{campaign.FACTOR_NAME}_eligible"].sum() == 0
    assert output[campaign.FACTOR_NAME].isna().all()


def test_session_state_persistence_requires_119_paired_coordinates() -> None:
    inputs = _session_inputs()
    _, states = campaign.session_state_persistence(
        **inputs, previous_states=None, exact_previous_session=False
    )
    for state in states.values():
        state[:40] = campaign.STATE_MISSING
    output, _ = campaign.session_state_persistence(
        **inputs, previous_states=states, exact_previous_session=True
    )
    assert output[f"{campaign.FACTOR_NAME}_eligible"].sum() == 0
    assert (output["paired_feature_count"] == 118).all()


def test_daily_rank_rows_uses_average_ties() -> None:
    day = int(np.datetime64("2021-01-04", "D").astype(np.int64))
    keys = day * campaign.KEY_SCALE + np.arange(60)
    candidate = np.repeat([0.0, 1.0, 2.0], 20)
    comparison = candidate.copy()
    rows = campaign.daily_rank_rows(keys, candidate, comparison)
    assert len(rows) == 1
    assert rows[0][1] == 60
    assert rows[0][2] == pytest.approx(1.0)


def test_comparison_gate_is_strict() -> None:
    rows = [[index, 50, 0.8] for index in range(100)]
    result = campaign.comparison_result("x", rows, "synthetic")
    assert result["absolute_median_daily_rank_correlation"] == pytest.approx(0.8)
    assert result["gate_passed"] is False


def test_chain_entries_is_append_only_and_deterministic() -> None:
    entries = campaign.chain_entries([{"attempt_id": "a"}, {"attempt_id": "b"}])
    assert entries[0]["previous_entry_sha256"] == campaign.CHAIN_GENESIS
    assert entries[1]["previous_entry_sha256"] == entries[0]["entry_sha256"]
    body = dict(entries[1])
    observed = body.pop("entry_sha256")
    assert campaign.canonical_sha256(body) == observed


def test_compact_stock_day_keys_round_trip() -> None:
    keys = campaign.compact_stock_day_keys(
        pd.Series(["2021-01-04", "2021-01-04"]),
        pd.Series(["SH600000", "SZ000001"]),
    )
    dates, instruments = campaign.decode_keys(keys)
    assert [value.date().isoformat() for value in dates] == [
        "2021-01-04",
        "2021-01-04",
    ]
    assert instruments.tolist() == ["SH600000", "SZ000001"]


def test_survivor_decision_rejects_incomplete_validation() -> None:
    decision = campaign.survivor_decision([])
    assert decision["passed"] is False
    assert "incomplete_validation_fold_count" in decision["rejection_reasons"]


def test_plan_reads_only_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(campaign, "OUTPUT_ROOT", campaign.REPO_ROOT / "not-created")
    result = campaign.plan()
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
