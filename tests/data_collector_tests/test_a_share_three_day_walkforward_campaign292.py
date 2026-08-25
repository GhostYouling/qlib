from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign292 as campaign


def _session_inputs(rows: int = 5) -> dict[str, np.ndarray]:
    levels = np.arange(rows, dtype=np.float32)[:, None]
    matrix = np.broadcast_to(
        levels, (rows, campaign.FEATURE_COUNT)
    ).copy()
    return {
        "keys": np.arange(1_100_001, 1_100_001 + rows, dtype=np.int64),
        "matrix": matrix,
        "finite_count": np.full(
            rows, campaign.FEATURE_COUNT, dtype=np.uint8
        ),
        "feature_support": np.ones(rows, dtype=bool),
        "quality_listing": np.ones(rows, dtype=bool),
        "model_support": np.ones(rows, dtype=bool),
    }


def test_session_peer_rank_extremity_is_centered_and_symmetric() -> None:
    output = campaign.session_peer_rank_extremity(**_session_inputs())
    assert output[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert output[campaign.FACTOR_NAME].iloc[0] == pytest.approx(0.8)
    assert output[campaign.FACTOR_NAME].iloc[1] == pytest.approx(0.4)
    assert output[campaign.FACTOR_NAME].iloc[2] == pytest.approx(0.0)
    assert output[campaign.FACTOR_NAME].iloc[3] == pytest.approx(0.4)
    assert output[campaign.FACTOR_NAME].iloc[-1] == pytest.approx(0.8)
    assert (output["finite_feature_count"] == campaign.FEATURE_COUNT).all()


def test_session_peer_rank_extremity_uses_average_ties() -> None:
    inputs = _session_inputs(rows=4)
    inputs["matrix"][:2] = 0.0
    inputs["matrix"][2:] = 1.0
    output = campaign.session_peer_rank_extremity(**inputs)
    assert output[f"{campaign.FACTOR_NAME}_eligible"].all()
    assert np.allclose(output[campaign.FACTOR_NAME], 0.5)


def test_session_peer_rank_extremity_requires_same_session_model_support() -> None:
    inputs = _session_inputs()
    inputs["matrix"][0, :40] = np.nan
    inputs["finite_count"][0] = 118
    inputs["feature_support"][0] = False
    inputs["model_support"][0] = False
    output = campaign.session_peer_rank_extremity(**inputs)
    assert not output[f"{campaign.FACTOR_NAME}_eligible"].iloc[0]
    assert np.isnan(output[campaign.FACTOR_NAME].iloc[0])
    assert output["finite_feature_count"].iloc[0] == 118


def test_session_peer_rank_extremity_rejects_changed_support_semantics() -> None:
    inputs = _session_inputs()
    inputs["finite_count"][0] = 157
    with pytest.raises(campaign.Campaign292Error):
        campaign.session_peer_rank_extremity(**inputs)


def test_daily_rank_rows_uses_average_ties() -> None:
    day = int(np.datetime64("2021-01-04", "D").astype(np.int64))
    keys = day * campaign.base.KEY_SCALE + np.arange(60)
    candidate = np.repeat([0.0, 1.0, 2.0], 20)
    rows = campaign.base.daily_rank_rows(keys, candidate, candidate.copy())
    assert len(rows) == 1
    assert rows[0][1] == 60
    assert rows[0][2] == pytest.approx(1.0)


def test_comparison_gate_is_strict() -> None:
    rows = [[index, 50, 0.8] for index in range(100)]
    result = campaign.base.comparison_result("x", rows, "synthetic")
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
    keys = campaign.base.compact_stock_day_keys(
        pd.Series(["2021-01-04", "2021-01-04"]),
        pd.Series(["SH600000", "SZ000001"]),
    )
    dates, instruments = campaign.base.decode_keys(keys)
    assert [value.date().isoformat() for value in dates] == [
        "2021-01-04",
        "2021-01-04",
    ]
    assert instruments.tolist() == ["SH600000", "SZ000001"]


def test_survivor_decision_rejects_incomplete_validation() -> None:
    decision = campaign.base.survivor_decision([])
    assert decision["passed"] is False
    assert "incomplete_validation_fold_count" in decision["rejection_reasons"]


def test_plan_reads_only_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(campaign, "OUTPUT_ROOT", campaign.REPO_ROOT / "not-created")
    result = campaign.plan()
    assert result["ready"] is True
    assert result["candidate_values_read"] is False
    assert result["comparator_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
    assert result["credential_loaded"] is False
