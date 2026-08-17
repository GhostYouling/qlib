import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign016_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign016 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_components() -> tuple[np.ndarray, np.ndarray]:
    gaps = np.resize(
        np.array([-0.0020, -0.0010, 0.0, 0.0010, 0.0020], dtype=float),
        FEATURES.WITHIN_HALF_PAIR_COUNT,
    )
    return gaps, gaps.copy()


def _path(
    *,
    gaps: np.ndarray | None = None,
    bodies: np.ndarray | None = None,
    afternoon_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if gaps is None or bodies is None:
        default_gaps, default_bodies = _default_components()
        gaps = default_gaps if gaps is None else gaps
        bodies = default_bodies if bodies is None else bodies
    gaps = np.asarray(gaps, dtype=float)
    bodies = np.asarray(bodies, dtype=float)
    assert gaps.shape == (FEATURES.WITHIN_HALF_PAIR_COUNT,)
    assert bodies.shape == (FEATURES.WITHIN_HALF_PAIR_COUNT,)

    opens = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    closes = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    highs = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    lows = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    pair_offset = 0
    for start, scale in ((0, 1.0), (120, afternoon_scale)):
        opens[start] = 100.0 * scale
        closes[start] = opens[start]
        highs[start] = opens[start] * 1.001
        lows[start] = opens[start] * 0.999
        for position in range(start + 1, start + 120):
            gap = gaps[pair_offset]
            body = bodies[pair_offset]
            opens[position] = closes[position - 1] * np.exp(gap)
            closes[position] = opens[position] * np.exp(body)
            highs[position] = max(opens[position], closes[position]) * 1.001
            lows[position] = min(opens[position], closes[position]) * 0.999
            pair_offset += 1
    assert pair_offset == FEATURES.WITHIN_HALF_PAIR_COUNT
    return opens, highs, lows, closes


def _compute(
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        opens=arrays[0].reshape(1, -1),
        highs=arrays[1].reshape(1, -1),
        lows=arrays[2].reshape(1, -1),
        closes=arrays[3].reshape(1, -1),
    )


def test_same_signed_and_opposite_signed_components_hit_closed_endpoints() -> None:
    gaps, bodies = _default_components()
    confirming = _path(gaps=gaps, bodies=bodies)
    reversing = _path(gaps=gaps, bodies=-bodies)
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=np.vstack([confirming[0], reversing[0]]),
        highs=np.vstack([confirming[1], reversing[1]]),
        lows=np.vstack([confirming[2], reversing[2]]),
        closes=np.vstack([confirming[3], reversing[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_exact_zero_pairs_remain_in_fixed_support() -> None:
    gaps, bodies = _default_components()
    assert int((gaps == 0.0).sum()) > 0
    values, eligible, _ = _compute(_path(gaps=gaps, bodies=bodies))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_zero_gap_or_body_variance_is_missing() -> None:
    gaps, bodies = _default_components()
    values, eligible, quality = _compute(
        _path(gaps=np.zeros_like(gaps), bodies=bodies)
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_gap_variance_rows"] == 1

    values, eligible, quality = _compute(
        _path(gaps=gaps, bodies=np.zeros_like(bodies))
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_body_variance_rows"] == 1


def test_lunch_boundary_is_not_a_pair() -> None:
    base = _path(afternoon_scale=1.0)
    large_lunch_gap = _path(afternoon_scale=7.0)
    values, eligible, _ = FEATURES.compute_factor_values(
        opens=np.vstack([base[0], large_lunch_gap[0]]),
        highs=np.vstack([base[1], large_lunch_gap[1]]),
        lows=np.vstack([base[2], large_lunch_gap[2]]),
        closes=np.vstack([base[3], large_lunch_gap[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_high_low_are_validation_only() -> None:
    arrays = _path()
    wider_highs = np.maximum(arrays[0], arrays[3]) * 1.2
    wider_lows = np.minimum(arrays[0], arrays[3]) * 0.8
    values, eligible, _ = FEATURES.compute_factor_values(
        opens=np.vstack([arrays[0], arrays[0]]),
        highs=np.vstack([arrays[1], wider_highs]),
        lows=np.vstack([arrays[2], wider_lows]),
        closes=np.vstack([arrays[3], arrays[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_invalid_shapes_ordering_containment_and_nonfinite_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign016FeatureError):
        FEATURES.compute_factor_values(
            opens=np.ones((1, 239)),
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )

    arrays = [array.copy() for array in _path()]
    arrays[2][3] = arrays[1][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"] == 1

    arrays = [array.copy() for array in _path()]
    arrays[0][4] = arrays[1][4] + 1.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__own_bar_open_containment_violation_rows"]
        == 1
    )

    arrays = [array.copy() for array in _path()]
    arrays[3][5] = arrays[1][5] + 1.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__own_bar_close_containment_violation_rows"]
        == 1
    )

    arrays = [array.copy() for array in _path()]
    arrays[0][0] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_ohlc_rows"] == 1


def test_partition_reads_only_ohlc_and_excludes_0930() -> None:
    arrays = _path()
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "open": np.concatenate([[-1.0], arrays[0]]),
            "high": np.concatenate([[-1.0], arrays[1]]),
            "low": np.concatenate([[-1.0], arrays[2]]),
            "close": np.concatenate([[-1.0], arrays[3]]),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "open",
        "high",
        "low",
        "close",
    )


def test_concept_audit_parent_and_protocol_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_016_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_016_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN015_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN015_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["within_half_pair_count"] == 238
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 39
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 37
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 37
    assert comparisons[-1]["name"] == "intraday_prior_range_breakout_pressure_238p"
    assert protocol["finite_post_admissibility_search"][
        "expected_trial_count_if_admitted"
    ] == 1


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "b9eefe47df24afdc92cf433d80cf7d18f014fc0414c25baa33fcf74b6f02b4f9"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf016_single__intraday_interbar_gap_body_confirmation_238p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_016_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign016.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_016"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_016"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    assert record["status"] == (
        "completed_zero_development_survivors_stress_interval_not_opened"
    )
    assert record["development_result"]["frozen_trial_count"] == 1
    assert (
        record["development_result"]["trial"][
            "development_survivor_gate_passed"
        ]
        is False
    )
    assert (
        record["development_result"]["trial"][
            "positive_validation_mean_rank_ic_fold_count"
        ]
        == 0
    )
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"]["recorded_historical_development_trial_count"] == 239
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign017_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
